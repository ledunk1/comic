import subprocess
import logging
import platform
import os

def detect_available_encoders():
    """Detect available hardware encoders on the system."""
    available_encoders = {
        'cpu': {'codec': 'libx264', 'name': 'CPU (libx264)', 'available': True},
        'intel_qsv': {'codec': 'h264_qsv', 'name': 'Intel QSV', 'available': False},
        'nvidia_nvenc': {'codec': 'h264_nvenc', 'name': 'NVIDIA NVENC', 'available': False},
        'amd_amf': {'codec': 'h264_amf', 'name': 'AMD AMF', 'available': False}
    }
    
    try:
        # Get ffmpeg encoders list
        result = subprocess.run(['ffmpeg', '-encoders'], 
                              capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            encoders_output = result.stdout.lower()
            
            # Check for hardware encoders
            if 'h264_qsv' in encoders_output:
                available_encoders['intel_qsv']['available'] = True
                logging.info("Intel QSV encoder detected")
            
            if 'h264_nvenc' in encoders_output:
                available_encoders['nvidia_nvenc']['available'] = True
                logging.info("NVIDIA NVENC encoder detected")
            
            if 'h264_amf' in encoders_output:
                available_encoders['amd_amf']['available'] = True
                logging.info("AMD AMF encoder detected")
        
        # Additional check for AMD AMF using hardware detection
        if not available_encoders['amd_amf']['available']:
            if detect_amd_hardware():
                available_encoders['amd_amf']['available'] = True
                logging.info("AMD hardware detected, enabling AMF encoder")
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.warning(f"Could not detect hardware encoders: {e}")
    
    return available_encoders

def detect_amd_hardware():
    """Detect AMD graphics hardware."""
    try:
        if platform.system() == "Windows":
            # Check Windows registry or WMI for AMD graphics
            try:
                result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and 'amd' in result.stdout.lower():
                    return True
            except:
                pass
            
            # Check using dxdiag
            try:
                result = subprocess.run(['dxdiag', '/t', 'temp_dxdiag.txt'], 
                                      capture_output=True, timeout=15)
                if os.path.exists('temp_dxdiag.txt'):
                    with open('temp_dxdiag.txt', 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        if 'amd' in content or 'radeon' in content:
                            os.remove('temp_dxdiag.txt')
                            return True
                    os.remove('temp_dxdiag.txt')
            except:
                pass
        
        elif platform.system() == "Linux":
            # Check lspci for AMD graphics
            try:
                result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    output = result.stdout.lower()
                    if 'amd' in output or 'radeon' in output or 'advanced micro devices' in output:
                        return True
            except:
                pass
            
            # Check /proc/cpuinfo for AMD
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    content = f.read().lower()
                    if 'amd' in content:
                        return True
            except:
                pass
    
    except Exception as e:
        logging.debug(f"Error detecting AMD hardware: {e}")
    
    return False

def get_best_encoder(enable_gpu=True):
    """Get the best available encoder based on system capabilities."""
    if not enable_gpu:
        return 'libx264', 'CPU (libx264)'
    
    encoders = detect_available_encoders()
    
    # Priority order: NVIDIA > Intel > AMD > CPU
    priority_order = ['nvidia_nvenc', 'intel_qsv', 'amd_amf', 'cpu']
    
    for encoder_type in priority_order:
        if encoders[encoder_type]['available']:
            codec = encoders[encoder_type]['codec']
            name = encoders[encoder_type]['name']
            
            # For AMD AMF, use more lenient testing
            if encoder_type == 'amd_amf':
                if test_amd_encoder_lenient():
                    logging.info(f"Selected encoder: {name} ({codec})")
                    return codec, name
                else:
                    logging.warning("AMD AMF encoder failed lenient test, skipping")
                    continue
            else:
                # Use standard testing for other encoders
                if encoder_type == 'cpu' or test_encoder(codec):
                    logging.info(f"Selected encoder: {name} ({codec})")
                    return codec, name
                else:
                    logging.warning(f"{name} encoder failed test, trying next option")
                    continue
    
    # Fallback to CPU
    return 'libx264', 'CPU (libx264)'

def get_encoder_params(codec):
    """Get encoding parameters for specific codec."""
    params = {
        'libx264': {
            'codec': 'libx264',
            'audio_codec': 'aac',
            'preset': 'medium',
            'crf': 23
        },
        'h264_qsv': {
            'codec': 'h264_qsv',
            'audio_codec': 'aac',
            'preset': 'medium',
            'global_quality': 23
        },
        'h264_nvenc': {
            'codec': 'h264_nvenc',
            'audio_codec': 'aac',
            'preset': 'medium',
            'cq': 23
        },
        'h264_amf': {
            'codec': 'h264_amf',
            'audio_codec': 'aac',
            'quality': 'balanced',
            'rc': 'cqp',
            'qp_i': 22,
            'qp_p': 24,
            'qp_b': 26
        }
    }
    
    return params.get(codec, params['libx264'])

def test_encoder(codec):
    """Test if a specific encoder is working properly."""
    if codec == 'libx264':
        return True  # CPU encoder always works
    
    try:
        # Create a simple test command with shorter duration and smaller resolution
        test_cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=0.5:size=160x120:rate=1',
            '-c:v', codec, '-t', '0.5', '-f', 'null', '-', '-y'
        ]
        
        result = subprocess.run(test_cmd, capture_output=True, timeout=20)
        success = result.returncode == 0
        
        if not success:
            logging.debug(f"Encoder {codec} test failed with stderr: {result.stderr.decode()}")
        
        return success
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.debug(f"Encoder {codec} test failed with exception: {e}")
        return False

def test_amd_encoder_lenient():
    """More lenient test specifically for AMD AMF encoder."""
    try:
        # First, check if AMF encoder is listed in available encoders
        result = subprocess.run(['ffmpeg', '-encoders'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0 or 'h264_amf' not in result.stdout.lower():
            logging.debug("AMD AMF encoder not found in ffmpeg encoders list")
            return False
        
        # Try a very simple encoding test with minimal parameters
        test_cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 'color=red:size=160x120:duration=0.1',
            '-c:v', 'h264_amf', '-t', '0.1', '-f', 'null', '-', '-y'
        ]
        
        result = subprocess.run(test_cmd, capture_output=True, timeout=15)
        
        # AMD AMF might return non-zero but still work, check stderr for specific errors
        if result.returncode == 0:
            logging.info("AMD AMF encoder test passed")
            return True
        
        # Check if the error is just a warning or non-critical
        stderr_text = result.stderr.decode().lower()
        critical_errors = [
            'no device available',
            'failed to initialize',
            'not supported',
            'no such device',
            'cannot load'
        ]
        
        has_critical_error = any(error in stderr_text for error in critical_errors)
        
        if not has_critical_error:
            logging.info("AMD AMF encoder test passed with warnings (acceptable)")
            return True
        else:
            logging.debug(f"AMD AMF encoder has critical errors: {stderr_text}")
            return False
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.debug(f"AMD AMF lenient test failed: {e}")
        return False

def validate_encoder_before_use(codec):
    """Validate encoder right before use with actual encoding parameters."""
    if codec == 'libx264':
        return True
    
    try:
        # Test with actual encoding parameters that will be used
        if codec == 'h264_amf':
            test_cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'color=blue:size=320x240:duration=0.2',
                '-c:v', 'h264_amf', '-rc', 'cqp', '-qp_i', '22', '-qp_p', '24',
                '-t', '0.2', '-f', 'null', '-', '-y'
            ]
        elif codec == 'h264_nvenc':
            test_cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'color=green:size=320x240:duration=0.2',
                '-c:v', 'h264_nvenc', '-preset', 'medium', '-cq', '23',
                '-t', '0.2', '-f', 'null', '-', '-y'
            ]
        elif codec == 'h264_qsv':
            test_cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'color=yellow:size=320x240:duration=0.2',
                '-c:v', 'h264_qsv', '-preset', 'medium', '-global_quality', '23',
                '-t', '0.2', '-f', 'null', '-', '-y'
            ]
        else:
            return test_encoder(codec)
        
        result = subprocess.run(test_cmd, capture_output=True, timeout=15)
        
        # For AMD, be more lenient with return codes
        if codec == 'h264_amf':
            stderr_text = result.stderr.decode().lower()
            critical_errors = [
                'no device available',
                'failed to initialize amf',
                'amf not supported',
                'cannot initialize amf'
            ]
            
            has_critical_error = any(error in stderr_text for error in critical_errors)
            success = result.returncode == 0 or not has_critical_error
        else:
            success = result.returncode == 0
        
        if success:
            logging.info(f"Encoder {codec} validation passed")
        else:
            logging.warning(f"Encoder {codec} validation failed: {result.stderr.decode()}")
        
        return success
        
    except Exception as e:
        logging.warning(f"Encoder {codec} validation failed with exception: {e}")
        return False