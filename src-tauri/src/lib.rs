use std::sync::Mutex;
use std::process::Command;
use tauri::Manager;
use tauri::Emitter;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

struct ServerState {
    process: Option<std::process::Child>,
}

const DEFAULT_MODEL: &str = "qwen2.5:0.5b-instruct";

/// Run PowerShell silently and get output
fn ps(script: &str) -> Option<String> {
    let mut cmd = Command::new("powershell");
    cmd.args(["-NoProfile", "-NonInteractive", "-Command", script]);
    
    #[cfg(windows)]
    cmd.creation_flags(CREATE_NO_WINDOW);
    
    cmd.output().ok().map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
}

/// Find Ollama executable
fn find_ollama() -> Option<String> {
    if let Ok(profile) = std::env::var("USERPROFILE") {
        let path = format!("{}\\AppData\\Local\\Programs\\Ollama\\ollama.exe", profile);
        if std::path::Path::new(&path).exists() {
            return Some(path);
        }
    }
    
    for pf in ["C:\\Program Files\\Ollama\\ollama.exe", "C:\\Program Files (x86)\\Ollama\\ollama.exe"] {
        if std::path::Path::new(pf).exists() {
            return Some(pf.to_string());
        }
    }
    
    ps("(Get-Command ollama -ErrorAction SilentlyContinue).Source")
        .filter(|s| !s.is_empty() && std::path::Path::new(s).exists())
}

/// Check if Ollama API is ready
fn ollama_ready() -> bool {
    ps("try{(iwr 'http://localhost:11434/api/tags' -TimeoutSec 2).StatusCode -eq 200}catch{$false}")
        .map(|s| s.to_lowercase() == "true")
        .unwrap_or(false)
}

/// Install Ollama via winget
fn install_ollama() -> bool {
    let result = ps("winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements --silent; $?");
    if result.map(|s| s.to_lowercase() == "true").unwrap_or(false) {
        std::thread::sleep(std::time::Duration::from_secs(3));
        return find_ollama().is_some();
    }
    
    // Fallback: direct download
    let dl = ps(r#"
        $f = "$env:TEMP\ollama.exe"
        iwr 'https://ollama.com/download/OllamaSetup.exe' -OutFile $f
        Start-Process $f '/S' -Wait
        Start-Sleep 3
        Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    "#);
    dl.map(|s| s.to_lowercase() == "true").unwrap_or(false)
}

/// Start Ollama service
fn start_ollama(path: &str) -> bool {
    if ollama_ready() {
        return true;
    }
    
    ps(&format!("Start-Process '{}' 'serve' -WindowStyle Hidden", path));
    
    for _ in 0..30 {
        std::thread::sleep(std::time::Duration::from_secs(1));
        if ollama_ready() {
            return true;
        }
    }
    false
}

/// Check if model is downloaded
fn model_exists(path: &str, model: &str) -> bool {
    let mut cmd = Command::new(path);
    cmd.args(["list"]);
    #[cfg(windows)]
    cmd.creation_flags(CREATE_NO_WINDOW);
    
    if let Ok(out) = cmd.output() {
        let list = String::from_utf8_lossy(&out.stdout);
        // Check for the model name (without the -instruct suffix sometimes)
        return list.contains("qwen2.5:0.5b") || list.contains(model);
    }
    false
}

/// Pull model (blocking, waits for completion)
fn pull_model(path: &str, model: &str) -> bool {
    let mut cmd = Command::new(path);
    cmd.args(["pull", model]);
    #[cfg(windows)]
    cmd.creation_flags(CREATE_NO_WINDOW);
    
    match cmd.status() {
        Ok(status) => status.success(),
        Err(_) => false
    }
}

/// Check if backend is ready
fn backend_ready() -> bool {
    ps("try{(iwr 'http://localhost:5000' -TimeoutSec 1).StatusCode -eq 200}catch{$false}")
        .map(|s| s.to_lowercase() == "true")
        .unwrap_or(false)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Mutex::new(ServerState { process: None }))
        .setup(|app| {
            let _ = app.handle().plugin(
                tauri_plugin_log::Builder::default()
                    .level(log::LevelFilter::Info)
                    .build(),
            );
            
            if cfg!(debug_assertions) {
                log::info!("Dev mode");
                return Ok(());
            }
            
            // Get handle for emitting events
            let handle = app.handle().clone();
            
            // Get window and load splash immediately
            if let Some(window) = app.get_webview_window("main") {
                // Load splash screen first
                let splash_html = r#"
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style>
                            * { margin: 0; padding: 0; box-sizing: border-box; }
                            body {
                                font-family: 'Segoe UI', sans-serif;
                                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                                color: white;
                                height: 100vh;
                                display: flex;
                                flex-direction: column;
                                align-items: center;
                                justify-content: center;
                            }
                            h1 { font-size: 2.5rem; font-weight: 300; margin-bottom: 10px; }
                            .subtitle { color: #64b5f6; margin-bottom: 40px; }
                            .spinner {
                                width: 40px; height: 40px;
                                border: 3px solid rgba(255,255,255,0.1);
                                border-top-color: #64b5f6;
                                border-radius: 50%;
                                animation: spin 1s linear infinite;
                                margin-bottom: 20px;
                            }
                            @keyframes spin { to { transform: rotate(360deg); } }
                            #status { color: #90caf9; font-size: 0.9rem; }
                        </style>
                    </head>
                    <body>
                        <h1>TimeBrief</h1>
                        <p class="subtitle">Voice-Powered Time Tracking</p>
                        <div class="spinner"></div>
                        <p id="status">Starting...</p>
                        <script>
                            window.__TAURI__.event.listen('setup-status', (event) => {
                                document.getElementById('status').textContent = event.payload;
                            });
                        </script>
                    </body>
                    </html>
                "#;
                
                let _ = window.eval(&format!(
                    "document.open(); document.write(`{}`); document.close();",
                    splash_html.replace('`', "\\`")
                ));
            }
            
            // Clone handle for the setup thread
            let app_handle = app.handle().clone();
            
            // Run setup in background thread
            std::thread::spawn(move || {
                let emit = |msg: &str| {
                    log::info!("{}", msg);
                    let _ = handle.emit("setup-status", msg);
                };
                
                // 1. Find or install Ollama
                emit("Checking for Ollama...");
                let ollama = match find_ollama() {
                    Some(path) => {
                        emit("Ollama found");
                        path
                    }
                    None => {
                        emit("Installing Ollama (this takes a minute)...");
                        if install_ollama() {
                            emit("Ollama installed");
                            find_ollama().unwrap_or_default()
                        } else {
                            emit("Ollama installation failed - please install from ollama.com");
                            String::new()
                        }
                    }
                };
                
                if !ollama.is_empty() {
                    // 2. Start Ollama
                    emit("Starting Ollama service...");
                    if start_ollama(&ollama) {
                        emit("Ollama running");
                        
                        // 3. Check/download model
                        if !model_exists(&ollama, DEFAULT_MODEL) {
                            emit("Downloading AI model (~400MB)...");
                            emit("This only happens once - please wait...");
                            
                            if pull_model(&ollama, DEFAULT_MODEL) {
                                emit("AI model ready");
                            } else {
                                emit("Model download failed - will retry later");
                            }
                        } else {
                            emit("AI model ready");
                        }
                    } else {
                        emit("Ollama failed to start");
                    }
                }
                
                // 4. Start backend server
                emit("Starting TimeBrief server...");
                
                let server_path = app_handle.path().resource_dir()
                    .expect("resource dir")
                    .join("binaries")
                    .join("timebrief-server-x86_64-pc-windows-msvc.exe");
                
                if server_path.exists() {
                    let mut cmd = std::process::Command::new(&server_path);
                    #[cfg(windows)]
                    cmd.creation_flags(CREATE_NO_WINDOW);
                    
                    if let Ok(child) = cmd.spawn() {
                        // Store the process handle
                        if let Some(state) = app_handle.try_state::<Mutex<ServerState>>() {
                            state.lock().unwrap().process = Some(child);
                        }
                        
                        // Wait for backend to be ready
                        emit("Waiting for server...");
                        for i in 0..60 {
                            std::thread::sleep(std::time::Duration::from_millis(500));
                            if backend_ready() {
                                emit("Server ready!");
                                break;
                            }
                            if i % 10 == 0 && i > 0 {
                                emit(&format!("Still starting... ({}s)", i / 2));
                            }
                        }
                    }
                } else {
                    emit("Server binary not found!");
                    log::error!("Missing: {:?}", server_path);
                }
                
                // 5. Navigate to the app
                std::thread::sleep(std::time::Duration::from_millis(500));
                
                if let Some(window) = app_handle.get_webview_window("main") {
                    if backend_ready() {
                        emit("Loading TimeBrief...");
                        let _ = window.eval("window.location.href = 'http://localhost:5000'");
                    } else {
                        emit("Backend not responding - please restart the app");
                    }
                }
            });
            
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<Mutex<ServerState>>();
                let mut guard = state.lock().unwrap();
                if let Some(mut proc) = guard.process.take() {
                    let _ = proc.kill();
                };
            }
        })
        .run(tauri::generate_context!())
        .expect("app error");
}
