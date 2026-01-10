use std::sync::Mutex;
use tauri::Manager;

// Store the server process handle
struct ServerState {
    process: Option<std::process::Child>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Mutex::new(ServerState { process: None }))
        .setup(|app| {
            // In debug mode, assume Flask is already running externally
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
                log::info!("Debug mode: expecting Flask at localhost:5000");
            } else {
                // In release mode, spawn the bundled server
                log::info!("Starting bundled server...");
                
                // Get the sidecar path
                let sidecar_path = app
                    .path()
                    .resource_dir()
                    .expect("failed to get resource dir")
                    .join("binaries")
                    .join("timebrief-server-x86_64-pc-windows-msvc.exe");
                
                if sidecar_path.exists() {
                    match std::process::Command::new(&sidecar_path)
                        .spawn()
                    {
                        Ok(child) => {
                            log::info!("Server started with PID: {}", child.id());
                            let state = app.state::<Mutex<ServerState>>();
                            state.lock().unwrap().process = Some(child);
                        }
                        Err(e) => {
                            log::error!("Failed to start server: {}", e);
                        }
                    }
                    
                    // Wait for server to be ready
                    std::thread::sleep(std::time::Duration::from_secs(2));
                } else {
                    log::warn!("Server binary not found at: {:?}", sidecar_path);
                }
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Kill the server when window closes
                let state = window.state::<Mutex<ServerState>>();
                let mut guard = state.lock().unwrap();
                if let Some(mut process) = guard.process.take() {
                    let _ = process.kill();
                    log::info!("Server process terminated");
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
