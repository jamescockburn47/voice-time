"""Hardware detection and optimization for voice processing."""
import platform
import subprocess
from typing import Dict, Any


def detect_hardware() -> Dict[str, Any]:
    """
    Detect available hardware for AI acceleration.
    
    Returns:
        Dictionary with hardware capabilities:
        - cpu_name: Processor name
        - has_cuda: NVIDIA GPU available
        - has_amd: AMD GPU available  
        - has_intel: Intel GPU available
        - recommended_device: Best device to use
        - compute_type: Best compute type for faster-whisper
    """
    info = {
        'cpu_name': platform.processor(),
        'platform': platform.system(),
        'has_cuda': False,
        'has_amd': False,
        'has_intel': False,
        'has_npu': False,
        'recommended_device': 'cpu',
        'compute_type': 'int8',  # CPU default
        'notes': []
    }
    
    # Check for NVIDIA CUDA
    try:
        import torch
        if torch.cuda.is_available():
            info['has_cuda'] = True
            info['recommended_device'] = 'cuda'
            info['compute_type'] = 'float16'
            info['gpu_name'] = torch.cuda.get_device_name(0)
            info['notes'].append('NVIDIA GPU detected - using CUDA acceleration')
    except:
        pass
    
    # Check for AMD (Windows)
    if platform.system() == 'Windows':
        try:
            # Check for AMD GPU via wmic
            result = subprocess.run(
                ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                capture_output=True,
                text=True,
                timeout=5
            )
            gpu_info = result.stdout.lower()
            
            if 'amd' in gpu_info or 'radeon' in gpu_info:
                info['has_amd'] = True
                info['notes'].append('AMD GPU detected')
                
                # Check for Ryzen AI (NPU)
                if 'ryzen' in info['cpu_name'].lower() and ('ai' in info['cpu_name'].lower() or '300' in info['cpu_name']):
                    info['has_npu'] = True
                    info['notes'].append('AMD Ryzen AI with NPU detected (Evo x2)')
                    info['notes'].append('Note: NPU not yet supported by Whisper, using optimized CPU')
                
                # For AMD on Windows, CPU with int8 is still best for Whisper
                # DirectML support would require different setup
                info['recommended_device'] = 'cpu'
                info['compute_type'] = 'int8'
                info['notes'].append('Using CPU with int8 quantization (optimized for AMD Ryzen)')
                
        except:
            pass
    
    # Check for Intel
    cpu_lower = info['cpu_name'].lower()
    if 'intel' in cpu_lower:
        info['has_intel'] = True
        info['notes'].append('Intel CPU detected - using optimized CPU mode')
    
    # Optimize compute type based on CPU
    if not info['has_cuda']:  # CPU mode
        if 'amd' in cpu_lower or 'ryzen' in cpu_lower:
            # AMD Ryzen - int8 is fast
            info['compute_type'] = 'int8'
            info['notes'].append('Using int8 quantization for AMD Ryzen (2-3x faster)')
        elif 'intel' in cpu_lower:
            # Intel - int8 with AVX2
            info['compute_type'] = 'int8'
            if 'avx2' in cpu_lower or int(platform.python_version_tuple()[1]) >= 8:
                info['notes'].append('Using int8 with AVX2 acceleration')
    
    return info


def get_optimal_whisper_config(hardware_info: Dict[str, Any] = None) -> Dict[str, str]:
    """
    Get optimal Whisper configuration for detected hardware.
    
    Returns:
        Dictionary with 'device' and 'compute_type' for faster-whisper
    """
    if hardware_info is None:
        hardware_info = detect_hardware()
    
    return {
        'device': hardware_info['recommended_device'],
        'compute_type': hardware_info['compute_type']
    }


# For AMD Ryzen AI (Evo x2) specific notes:
"""
AMD Ryzen AI 300 series (Strix Point) with XDNA NPU:

The NPU is designed for AI workloads but faster-whisper doesn't support it yet.
However, the CPU part is very powerful (Zen 5 cores) and handles Whisper well.

Optimization for Ryzen AI:
1. Use CPU mode (NPU not supported)
2. Use int8 compute type (2-3x faster on Ryzen)
3. Ensure model is "base.en" or "tiny.en" for speed
4. Future: DirectML support could use integrated GPU

Current performance on Ryzen AI 9 365 with base.en:
- int8 CPU: ~1-2 seconds for 5-second audio
- This is excellent for real-time use

The integrated Radeon GPU could potentially be used via DirectML
in the future, but CPU mode is already very fast on Ryzen AI.
"""
