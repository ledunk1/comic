import os
import logging
import random
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, vfx, CompositeVideoClip,
    CompositeAudioClip, AudioClip
)
from moviepy.video.fx.all import crop
from PIL import Image, ImageFilter
import numpy as np
from .gpu_detector import get_best_encoder, get_encoder_params, validate_encoder_before_use

def get_random_effect(weights):
    """Memilih efek acak berdasarkan bobot yang diberikan."""
    if not weights or sum(weights.values()) == 0:
        return 'pan_right'  # Efek default
    
    effects = list(weights.keys())
    chances = list(weights.values())
    
    return random.choices(effects, weights=chances, k=1)[0]

def apply_ken_burns_effect(clip, effect_type='pan_right', intensity=0.08):
    """Menerapkan efek Ken Burns pada klip video dengan implementasi yang diperbaiki berdasarkan script referensi."""
    w, h = clip.size
    duration = clip.duration
    
    logging.info(f"Applying {effect_type} effect with intensity {intensity} on clip size {w}x{h}")
    
    # Faktor zoom untuk efek pan (berdasarkan script referensi)
    zoom_factor = 1 + intensity * 3  # Konversi intensity ke zoom factor yang lebih besar
    
    # Hitung rentang gerak berdasarkan script referensi
    travel_factor = intensity * 4  # Konversi intensity ke travel factor
    
    if effect_type in ['pan_right', 'pan_left', 'pan_up', 'pan_down']:
        # Untuk efek pan, perbesar gambar terlebih dahulu
        enlarged_clip = clip.resize(zoom_factor)
        enlarged_w, enlarged_h = enlarged_clip.size
        
        # Hitung rentang gerak maksimal
        max_range_x = max(0, (enlarged_w - w) / 2)
        max_range_y = max(0, (enlarged_h - h) / 2)
        
        # Terapkan travel factor
        range_x = max_range_x * travel_factor
        range_y = max_range_y * travel_factor
        
        # Posisi tengah
        center_x = (w - enlarged_w) / 2
        center_y = (h - enlarged_h) / 2
        
        def position_func(t):
            progress = t / duration
            if effect_type == 'pan_right':
                return (center_x - range_x * progress, center_y)
            elif effect_type == 'pan_left':
                return (center_x + range_x * progress, center_y)
            elif effect_type == 'pan_up':
                return (center_x, center_y + range_y * progress)
            elif effect_type == 'pan_down':
                return (center_x, center_y - range_y * progress)
            return ('center', 'center')
        
        # Buat composite clip dengan posisi yang berubah
        result_clip = CompositeVideoClip(
            [enlarged_clip.set_position(position_func)], 
            size=(w, h)
        ).set_duration(duration)
        
        return result_clip
    
    elif effect_type in ['zoom_in', 'zoom_out']:
        # Untuk efek zoom, gunakan resize dengan fungsi waktu
        def resize_func(t):
            progress = t / duration
            if effect_type == 'zoom_in':
                return 1 + intensity * 3 * progress  # Zoom dari 1x ke zoom_factor
            elif effect_type == 'zoom_out':
                return zoom_factor - intensity * 3 * progress  # Zoom dari zoom_factor ke 1x
            return 1
        
        # Terapkan resize dengan fungsi waktu dan posisi tengah
        result_clip = CompositeVideoClip(
            [clip.resize(resize_func).set_position('center')],
            size=(w, h)
        ).set_duration(duration)
        
        return result_clip
    
    # Fallback: return original clip
    return clip

def create_blur_background_with_centered_image(image_path, target_w, target_h, blur_radius=30):
    """Membuat background blur dengan gambar asli di tengah (mempertahankan aspect ratio)."""
    try:
        from PIL import Image, ImageFilter
        
        # Buka gambar asli
        original_image = Image.open(image_path)
        img_w, img_h = original_image.size
        
        logging.info(f"Creating blur background: original {img_w}x{img_h} -> target {target_w}x{target_h}")
        
        # 1. Buat background blur dengan resize ke ukuran target (akan terdistorsi)
        background_image = original_image.resize((target_w, target_h), Image.Resampling.LANCZOS)
        background_image = background_image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # 2. Hitung ukuran gambar asli yang akan diletakkan di tengah (mempertahankan aspect ratio)
        img_aspect = img_w / img_h
        target_aspect = target_w / target_h
        
        # Tentukan ukuran gambar foreground agar fit di dalam target tanpa crop
        if img_aspect > target_aspect:
            # Gambar lebih lebar, fit berdasarkan lebar target
            foreground_width = target_w
            foreground_height = int(target_w / img_aspect)
        else:
            # Gambar lebih tinggi, fit berdasarkan tinggi target
            foreground_height = target_h
            foreground_width = int(target_h * img_aspect)
        
        # Pastikan gambar tidak melebihi batas target
        if foreground_width > target_w:
            foreground_width = target_w
            foreground_height = int(target_w / img_aspect)
        if foreground_height > target_h:
            foreground_height = target_h
            foreground_width = int(target_h * img_aspect)
        
        logging.info(f"Foreground size: {foreground_width}x{foreground_height}")
        
        # 3. Resize gambar asli untuk foreground (mempertahankan aspect ratio)
        foreground_image = original_image.resize((foreground_width, foreground_height), Image.Resampling.LANCZOS)
        
        # 4. Hitung posisi tengah untuk menempelkan foreground
        pos_x = (target_w - foreground_width) // 2
        pos_y = (target_h - foreground_height) // 2
        
        logging.info(f"Positioning foreground at: ({pos_x}, {pos_y})")
        
        # 5. Tempelkan gambar foreground ke atas background
        final_image = background_image.copy()
        final_image.paste(foreground_image, (pos_x, pos_y))
        
        # 6. Simpan sebagai file sementara
        temp_path = image_path.replace('.', '_center_blur.')
        final_image.save(temp_path, quality=95)
        
        logging.info(f"Center blur image created: {temp_path}")
        return temp_path
        
    except Exception as e:
        logging.error(f"Error creating center blur background: {e}")
        return image_path  # Return original if blur fails

def create_blur_background(image_path, target_w, target_h, blur_radius=30):
    """Membuat background blur berdasarkan script referensi blur.py (fit to screen)."""
    try:
        from PIL import Image, ImageFilter
        
        # Buka gambar asli
        original_image = Image.open(image_path)
        
        # Buat background blur dengan resize ke ukuran target
        background_image = original_image.resize((target_w, target_h), Image.Resampling.LANCZOS)
        background_image = background_image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Hitung ukuran foreground (gambar asli) agar pas di tengah
        img_w, img_h = original_image.size
        img_aspect = img_w / img_h
        target_aspect = target_w / target_h
        
        if img_aspect > target_aspect:
            # Gambar lebih lebar, sesuaikan dengan tinggi target
            foreground_height = target_h
            foreground_width = int(foreground_height * img_aspect)
        else:
            # Gambar lebih tinggi, sesuaikan dengan lebar target
            foreground_width = target_w
            foreground_height = int(foreground_width / img_aspect)
        
        # Resize gambar asli untuk foreground
        foreground_image = original_image.resize((foreground_width, foreground_height), Image.Resampling.LANCZOS)
        
        # Hitung posisi tengah untuk menempelkan foreground
        pos_x = (target_w - foreground_width) // 2
        pos_y = (target_h - foreground_height) // 2
        
        # Tempelkan gambar foreground ke atas background
        final_image = background_image.copy()
        final_image.paste(foreground_image, (pos_x, pos_y))
        
        # Simpan sebagai file sementara
        temp_path = image_path.replace('.', '_blurred.')
        final_image.save(temp_path)
        
        return temp_path
        
    except Exception as e:
        logging.error(f"Error creating blur background: {e}")
        return image_path  # Return original if blur fails

def get_encoder_settings(gpu_acceleration='auto'):
    """Get encoder settings based on GPU acceleration preference with improved AMD support."""
    encoder_map = {
        'auto': lambda: get_best_encoder(True),
        'cpu': lambda: ('libx264', 'CPU (libx264)'),
        'intel': lambda: ('h264_qsv', 'Intel QSV'),
        'nvidia': lambda: ('h264_nvenc', 'NVIDIA NVENC'),
        'amd': lambda: ('h264_amf', 'AMD AMF')
    }
    
    try:
        codec, name = encoder_map.get(gpu_acceleration, encoder_map['auto'])()
        
        # For AMD AMF, use more thorough validation
        if codec == 'h264_amf':
            if validate_encoder_before_use(codec):
                logging.info(f"AMD AMF encoder validated successfully")
            else:
                logging.warning(f"AMD AMF encoder validation failed, falling back to CPU")
                codec, name = 'libx264', 'CPU (libx264)'
        elif codec != 'libx264':
            # Test other hardware encoders
            if not validate_encoder_before_use(codec):
                logging.warning(f"Selected encoder {codec} failed validation, falling back to CPU")
                codec, name = 'libx264', 'CPU (libx264)'
        
        params = get_encoder_params(codec)
        logging.info(f"Using video encoder: {name} ({codec})")
        
        return params
        
    except Exception as e:
        logging.error(f"Error getting encoder settings: {e}")
        # Fallback to CPU
        return get_encoder_params('libx264')

def create_video_from_scenes(scenes, output_folder, resolution='9:16', image_positioning='fit_screen', enable_movement=False, effect_weights=None, pause_duration=0.5, movement_speed=8, gpu_acceleration='auto'):
    """Membuat video dari daftar adegan dengan resolusi HD 720p."""
    if not scenes:
        logging.warning("Tidak ada adegan yang diberikan untuk membuat video.")
        return None
        
    final_clips = []
    
    # UPDATED: Menggunakan resolusi HD 720p untuk semua rasio
    res_map = {
        '9:16': (720, 1280),   # HD Portrait (720p)
        '16:9': (1280, 720),   # HD Landscape (720p) 
        '1:1': (720, 720)      # HD Square (720p)
    }
    target_w, target_h = res_map.get(resolution, (720, 1280))
    
    logging.info(f"Creating video with HD 720p resolution: {target_w}x{target_h} ({resolution})")
    
    # Convert movement speed from percentage to decimal (8% -> 0.08)
    movement_intensity = movement_speed / 100.0
    logging.info(f"Using movement intensity: {movement_intensity} (from speed: {movement_speed}%)")
    logging.info(f"Image positioning mode: {image_positioning}")
    
    # Get encoder settings
    encoder_params = get_encoder_settings(gpu_acceleration)
    logging.info(f"Video encoding settings: {encoder_params}")

    try:
        for i, scene in enumerate(scenes):
            image_path = scene['image_path']
            audio_path = scene['audio_path']
            logging.info(f"Memproses adegan {i}: Gambar='{image_path}', Audio='{audio_path}'")
            
            if not os.path.exists(image_path):
                logging.error(f"File gambar tidak ditemukan: {image_path}")
                continue
                
            if not os.path.exists(audio_path):
                logging.error(f"File audio tidak ditemukan: {audio_path}")
                continue

            try:
                # Load audio clip and get duration
                audio_clip = AudioFileClip(audio_path)
                audio_duration = audio_clip.duration
                
                # Add pause duration to total duration
                total_duration = audio_duration + pause_duration
                
                # Create silent pause audio
                if pause_duration > 0:
                    silent_pause = AudioClip(lambda t: 0, duration=pause_duration, fps=44100)
                    final_audio = CompositeAudioClip([audio_clip, silent_pause.set_start(audio_duration)])
                else:
                    final_audio = audio_clip
                
                # Tentukan path gambar yang akan digunakan
                working_image_path = image_path
                temp_files_to_cleanup = []
                
                # Process image based on positioning mode and resolution
                if resolution == '16:9' and image_positioning == 'center_blur':
                    # Center with blur background mode - FIXED VERSION
                    logging.info(f"Creating center with blur background for scene {i}")
                    working_image_path = create_blur_background_with_centered_image(image_path, target_w, target_h)
                    temp_files_to_cleanup.append(working_image_path)
                    
                    # Load the processed image and set it to exact target size
                    final_clip_canvas = ImageClip(working_image_path).set_duration(total_duration)
                    # Ensure exact target size
                    final_clip_canvas = final_clip_canvas.resize((target_w, target_h))
                    
                elif resolution == '16:9' and image_positioning == 'fit_screen':
                    # Fit to screen mode (original behavior)
                    logging.info(f"Using fit to screen mode for scene {i}")
                    
                    # Load dan proses gambar
                    img_clip = ImageClip(working_image_path).set_duration(total_duration)
                    
                    # Get image dimensions
                    img_w, img_h = img_clip.size
                    if img_w == 0 or img_h == 0:
                        logging.error(f"Invalid image dimensions for {working_image_path}: {img_w}x{img_h}")
                        continue
                    
                    img_aspect = img_w / img_h
                    target_aspect = target_w / target_h
                    
                    # Resize image to fit target resolution (may crop)
                    if img_aspect > target_aspect:
                        # Image is wider, fit by height (crop sides)
                        resized_clip = img_clip.resize(height=target_h)
                    else:
                        # Image is taller, fit by width (crop top/bottom)
                        resized_clip = img_clip.resize(width=target_w)
                    
                    # Create final composition
                    final_clip_canvas = CompositeVideoClip(
                        [resized_clip.set_position("center")], 
                        size=(target_w, target_h), 
                        bg_color=(0, 0, 0)
                    )
                
                else:
                    # Default behavior for 9:16 and other resolutions
                    logging.info(f"Using default positioning for resolution {resolution}")
                    
                    # Load dan proses gambar
                    img_clip = ImageClip(working_image_path).set_duration(total_duration)
                    
                    # Get image dimensions
                    img_w, img_h = img_clip.size
                    if img_w == 0 or img_h == 0:
                        logging.error(f"Invalid image dimensions for {working_image_path}: {img_w}x{img_h}")
                        continue
                    
                    img_aspect = img_w / img_h
                    target_aspect = target_w / target_h
                    
                    # Resize image to fit target resolution
                    if img_aspect > target_aspect:
                        # Image is wider, fit by height
                        resized_clip = img_clip.resize(height=target_h)
                    else:
                        # Image is taller, fit by width
                        resized_clip = img_clip.resize(width=target_w)
                    
                    # Create final composition
                    final_clip_canvas = CompositeVideoClip(
                        [resized_clip.set_position("center")], 
                        size=(target_w, target_h), 
                        bg_color=(0, 0, 0)
                    )

                # Apply movement effects if enabled
                if enable_movement and effect_weights:
                    try:
                        chosen_effect = get_random_effect(effect_weights)
                        logging.info(f"Menerapkan efek '{chosen_effect}' dengan intensitas {movement_intensity} pada adegan {i}")
                        final_clip_canvas = apply_ken_burns_effect(final_clip_canvas, effect_type=chosen_effect, intensity=movement_intensity)
                    except Exception as e:
                        logging.warning(f"Failed to apply movement effect for scene {i}: {e}")

                # Set audio and duration
                final_clip_canvas = final_clip_canvas.set_audio(final_audio).set_duration(total_duration)
                final_clips.append(final_clip_canvas)
                
                logging.info(f"Successfully processed scene {i} with HD 720p resolution")
                
                # Clean up temporary files if created
                for temp_file in temp_files_to_cleanup:
                    if temp_file != image_path and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                            logging.info(f"Cleaned up temporary file: {temp_file}")
                        except Exception as cleanup_error:
                            logging.warning(f"Failed to cleanup temp file {temp_file}: {cleanup_error}")
                
            except Exception as e:
                logging.error(f"Error processing scene {i}: {e}")
                continue
        
        if not final_clips:
            logging.error("Tidak ada klip yang valid yang dibuat. Membatalkan pembuatan video.")
            return None

        logging.info(f"Concatenating {len(final_clips)} clips...")
        final_video = concatenate_videoclips(final_clips, method="compose")
        
        # Ensure output directory exists
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, "output.mp4")
        
        logging.info(f"Writing HD 720p video to {output_path} using {encoder_params['codec']}...")
        
        # Prepare encoding parameters with improved AMD AMF support
        write_params = {
            'codec': encoder_params['codec'],
            'audio_codec': encoder_params['audio_codec'],
            'fps': 24,
            'logger': 'bar',
            'temp_audiofile': 'temp-audio.m4a',
            'remove_temp': True
        }
        
        # Add codec-specific parameters
        if encoder_params['codec'] == 'libx264':
            write_params['preset'] = encoder_params.get('preset', 'medium')
            if 'crf' in encoder_params:
                write_params['ffmpeg_params'] = ['-crf', str(encoder_params['crf'])]
        elif encoder_params['codec'] == 'h264_qsv':
            if 'global_quality' in encoder_params:
                write_params['ffmpeg_params'] = ['-global_quality', str(encoder_params['global_quality'])]
        elif encoder_params['codec'] == 'h264_nvenc':
            write_params['preset'] = encoder_params.get('preset', 'medium')
            if 'cq' in encoder_params:
                write_params['ffmpeg_params'] = ['-cq', str(encoder_params['cq'])]
        elif encoder_params['codec'] == 'h264_amf':
            # Improved AMD AMF parameters
            ffmpeg_params = ['-rc', 'cqp']
            if 'qp_i' in encoder_params:
                ffmpeg_params.extend(['-qp_i', str(encoder_params['qp_i'])])
            if 'qp_p' in encoder_params:
                ffmpeg_params.extend(['-qp_p', str(encoder_params['qp_p'])])
            if 'qp_b' in encoder_params:
                ffmpeg_params.extend(['-qp_b', str(encoder_params['qp_b'])])
            
            # Add AMD-specific optimizations
            ffmpeg_params.extend(['-usage', 'transcoding', '-profile:v', 'main'])
            write_params['ffmpeg_params'] = ffmpeg_params
        
        try:
            final_video.write_videofile(output_path, **write_params)
            logging.info(f"HD 720p video successfully created using {encoder_params['codec']}: {output_path}")
        except Exception as e:
            logging.error(f"Hardware encoding failed: {e}")
            logging.info("Falling back to CPU encoding...")
            
            # Fallback to CPU encoding
            fallback_params = {
                'codec': 'libx264',
                'audio_codec': 'aac',
                'fps': 24,
                'preset': 'medium',
                'logger': 'bar',
                'temp_audiofile': 'temp-audio.m4a',
                'remove_temp': True,
                'ffmpeg_params': ['-crf', '23']
            }
            
            final_video.write_videofile(output_path, **fallback_params)
            logging.info(f"HD 720p video successfully created using CPU fallback: {output_path}")
        
        return output_path

    except Exception as e:
        logging.error(f"Terjadi kesalahan saat pemrosesan video: {e}", exc_info=True)
        return None
    finally:
        # Clean up clips to free memory
        for clip in final_clips:
            try:
                if hasattr(clip, 'close'): 
                    clip.close()
                if hasattr(clip, 'audio') and hasattr(clip.audio, 'close'): 
                    clip.audio.close()
            except Exception as e:
                logging.warning(f"Error closing clip: {e}")

def cleanup_temporary_files(scenes):
    """Menghapus file audio sementara setelah video dibuat."""
    for scene in scenes:
        try:
            if 'audio_path' in scene and os.path.exists(scene['audio_path']):
                os.remove(scene['audio_path'])
                logging.info(f"Cleaned up temporary audio file: {scene['audio_path']}")
        except Exception as e:
            logging.warning(f"Tidak dapat menghapus file sementara {scene['audio_path']}: {e}")
            
def get_effect_weights(form_data):
    """Mengekstrak bobot efek dari data formulir."""
    weights = {}
    for key, value in form_data.items():
        if key.startswith('effect_'):
            effect_name = key.replace('effect_', '')
            try:
                weights[effect_name] = int(value)
            except (ValueError, TypeError):
                weights[effect_name] = 0
    return weights