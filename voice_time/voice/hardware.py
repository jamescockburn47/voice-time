"""Hardware detection for voice processing.

DESIGN PHILOSOPHY (SOTA 2025):
- Ollama auto-detects GPU/CPU and configures itself optimally
- faster-whisper auto-detects CUDA availability and falls back to CPU
- We detect hardware for INFORMATIONAL purposes only (showing users what we found)
- We do NOT try to manually configure devices - let the libraries handle it

This approach is more reliable and works on any hardware including:
- No GPU (integrated graphics only) - like Lenovo IdeaPad
- NVIDIA GPU (CUDA)
- AMD GPU (CPU fallback, as DirectML not widely supported)
- Intel integrated graphics (CPU mode)
"""
import platform
import subprocess
from typing import Dict, Any


def detect_hardware() -> Dict[str, Any]:
    """
    Detect hardware for informational display purposes.
    
    NOTE: We do NOT use this to configure Ollama or faster-whisper.
    Those libraries auto-detect and configure themselves optimally.
    
    Returns:
        Dictionary with detected hardware info for UI display
    """
    info = {
        'cpu': _get_cpu_info(),
        'gpu': _get_gpu_info(),
        'memory_gb': _get_memory_gb(),
        'platform': platform.system(),
        'summary': '',  # Human-readable summary
    }
    
    # Build summary message
    summaries = []
    if info['gpu']['name'] and info['gpu']['name'] != 'Unknown':
        if info['gpu']['has_dedicated']:
            summaries.append(f"GPU: {info['gpu']['name']}")
        else:
            summaries.append(f"Integrated: {info['gpu']['name']}")
    
    summaries.append(f"CPU: {info['cpu']['name']}")
    
    if info['memory_gb']:
        summaries.append(f"{info['memory_gb']}GB RAM")
    
    info['summary'] = ' | '.join(summaries)
    
    return info


def _get_cpu_info() -> Dict[str, Any]:
    """Get CPU information."""
    cpu_name = platform.processor() or 'Unknown CPU'
    
    # Clean up the name
    if not cpu_name or cpu_name == 'Unknown CPU':
        # Try Windows-specific method
        if platform.system() == 'Windows':
            try:
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command',
                     '(Get-CimInstance Win32_Processor).Name'],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if result.returncode == 0 and result.stdout.strip():
                    cpu_name = result.stdout.strip()
            except:
                pass
    
    return {
        'name': cpu_name,
        'is_intel': 'intel' in cpu_name.lower(),
        'is_amd': 'amd' in cpu_name.lower() or 'ryzen' in cpu_name.lower(),
    }


def _get_gpu_info() -> Dict[str, Any]:
    """
    Get GPU information using Windows WMI.
    
    This is for display purposes only - Ollama handles its own GPU detection.
    """
    info = {
        'name': None,
        'has_dedicated': False,
        'has_nvidia': False,
        'has_amd': False,
    }
    
    if platform.system() != 'Windows':
        return info
    
    try:
        # Use PowerShell + WMI for reliable GPU detection
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name'],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if result.returncode == 0 and result.stdout.strip():
            gpus = [g.strip() for g in result.stdout.strip().split('\n') if g.strip()]
            
            # Find the best GPU (prefer dedicated over integrated)
            dedicated = None
            integrated = None
            
            for gpu in gpus:
                gpu_lower = gpu.lower()
                
                # Check for dedicated GPUs
                if 'nvidia' in gpu_lower or 'geforce' in gpu_lower or 'rtx' in gpu_lower or 'gtx' in gpu_lower:
                    dedicated = gpu
                    info['has_nvidia'] = True
                    info['has_dedicated'] = True
                elif 'radeon' in gpu_lower and 'graphics' not in gpu_lower:
                    # Dedicated AMD (not integrated Radeon Graphics)
                    dedicated = gpu
                    info['has_amd'] = True
                    info['has_dedicated'] = True
                else:
                    # Integrated graphics (Intel UHD, AMD Radeon Graphics, etc.)
                    integrated = gpu
            
            # Use dedicated if available, otherwise integrated
            info['name'] = dedicated or integrated
            
    except Exception:
        pass
    
    return info


def _get_memory_gb() -> int:
    """Get system RAM in GB."""
    if platform.system() != 'Windows':
        return 0
    
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             '[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)'],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except:
        pass
    
    return 0


def get_optimal_whisper_config() -> Dict[str, str]:
    """
    Get Whisper configuration.
    
    NOTE: faster-whisper auto-detects CUDA. We just provide sensible defaults.
    The library will use GPU if available, CPU otherwise.
    """
    return {
        'device': 'auto',  # Let faster-whisper decide
        'compute_type': 'auto',  # Let it pick best for the device
    }


def get_hardware_summary() -> str:
    """
    Get a one-line summary of detected hardware for display.
    
    Example outputs:
    - "GPU: NVIDIA GeForce RTX 3080 | CPU: AMD Ryzen 9 | 32GB RAM"
    - "Integrated: Intel UHD Graphics | CPU: Intel Core i5 | 16GB RAM"
    - "CPU: Intel Core i3 | 8GB RAM" (when GPU detection fails)
    """
    try:
        info = detect_hardware()
        return info.get('summary', 'Hardware detection unavailable')
    except Exception as e:
        return f'Hardware detection error: {e}'
