import os
import logging
from flask import render_template, request, jsonify, redirect, url_for, send_file, abort

# Import utility modules
from utils.config import TTS_VOICES, VISION_MODELS, LANGUAGES, GPU_ACCELERATION_OPTIONS
from utils.prompt_manager import (
    load_prompts, add_prompt, delete_prompt, update_prompt
)
from utils.ai_services import generate_narration, generate_tts_audio
from utils.video_processor import create_video_from_scenes, cleanup_temporary_files, get_effect_weights
from utils.file_handler import save_uploaded_file, generate_unique_filename
from utils.media_manager import (
    register_generated_media, get_all_generated_media, delete_generated_media,
    cleanup_old_media, get_media_stats, cleanup_orphaned_files
)
from utils.gpu_detector import detect_available_encoders

# ==============================================================================
# MAIN ROUTES
# ==============================================================================

def register_routes(app):
    """Register all routes with the Flask app."""
    
    @app.route('/', methods=['GET', 'POST'])
    def index():
        if request.method == 'POST':
            return handle_video_creation(app)
        
        # For GET request, show main page with all options
        return render_template('index.html', 
                               tts_voices=TTS_VOICES, 
                               vision_models=VISION_MODELS, 
                               prompts=load_prompts(),
                               languages=LANGUAGES,
                               gpu_options=GPU_ACCELERATION_OPTIONS)

    # ==============================================================================
    # PROMPT MANAGEMENT API ROUTES
    # ==============================================================================
    
    @app.route('/prompts', methods=['GET'])
    def get_prompts():
        """Get all prompts."""
        return jsonify(load_prompts())

    @app.route('/prompts/add', methods=['POST'])
    def add_prompt_route():
        """Add a new prompt."""
        data = request.json
        name = data.get('name')
        text = data.get('text')
        
        success, result = add_prompt(name, text)
        if success:
            return jsonify({"success": True, "prompts": result})
        else:
            return jsonify({"success": False, "error": result}), 400

    @app.route('/prompts/delete', methods=['POST'])
    def delete_prompt_route():
        """Delete a prompt."""
        data = request.json
        name = data.get('name')
        
        success, result = delete_prompt(name)
        if success:
            return jsonify({"success": True, "prompts": result})
        else:
            return jsonify({"success": False, "error": result}), 404

    @app.route('/prompts/update', methods=['POST'])
    def update_prompt_route():
        """Update an existing prompt."""
        data = request.json
        name = data.get('name')
        new_text = data.get('text')
        
        success, result = update_prompt(name, new_text)
        if success:
            return jsonify({"success": True, "prompts": result})
        else:
            return jsonify({"success": False, "error": result}), 404

    # ==============================================================================
    # MEDIA MANAGEMENT API ROUTES
    # ==============================================================================
    
    @app.route('/media/list', methods=['GET'])
    def get_media_list():
        """Get list of all generated media."""
        try:
            media_list = get_all_generated_media()
            return jsonify({"success": True, "media_list": media_list})
        except Exception as e:
            logging.error(f"Error getting media list: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/media/delete', methods=['POST'])
    def delete_media_route():
        """Delete a generated media file."""
        try:
            data = request.json
            media_id = data.get('media_id')
            
            if not media_id:
                return jsonify({"success": False, "error": "Media ID is required"}), 400
            
            success, message = delete_generated_media(media_id)
            if success:
                return jsonify({"success": True, "message": message})
            else:
                return jsonify({"success": False, "error": message}), 404
        except Exception as e:
            logging.error(f"Error deleting media: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/media/cleanup', methods=['POST'])
    def cleanup_media_route():
        """Clean up old media files."""
        try:
            data = request.json
            days_old = data.get('days_old', 7)
            
            deleted_count = cleanup_old_media(days_old)
            orphaned_count = cleanup_orphaned_files()
            
            return jsonify({
                "success": True, 
                "deleted_count": deleted_count,
                "orphaned_cleaned": orphaned_count,
                "message": f"Cleaned up {deleted_count} old files and {orphaned_count} orphaned files"
            })
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/media/stats', methods=['GET'])
    def get_media_stats_route():
        """Get media statistics."""
        try:
            stats = get_media_stats()
            return jsonify(stats)
        except Exception as e:
            logging.error(f"Error getting media stats: {e}")
            return jsonify({"error": str(e)}), 500

    # ==============================================================================
    # GPU DETECTION API ROUTE
    # ==============================================================================
    
    @app.route('/api/gpu-encoders', methods=['GET'])
    def get_gpu_encoders():
        """Get available GPU encoders."""
        try:
            encoders = detect_available_encoders()
            return jsonify({"success": True, "encoders": encoders})
        except Exception as e:
            logging.error(f"Error detecting GPU encoders: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ==============================================================================
    # FILE DOWNLOAD ROUTE
    # ==============================================================================
    
    @app.route('/download/<path:filename>')
    def download_file(filename):
        """Download generated media files."""
        try:
            file_path = os.path.join('static', filename)
            if not os.path.exists(file_path):
                logging.error(f"File not found for download: {file_path}")
                abort(404)
            
            return send_file(file_path, as_attachment=True)
        except Exception as e:
            logging.error(f"Error downloading file {filename}: {e}")
            abort(500)

# ==============================================================================
# VIDEO CREATION HANDLER
# ==============================================================================

def handle_video_creation(app):
    """Handle the enhanced video creation process."""
    try:
        # Extract form data
        mode = request.form.get('mode')
        voice_model = request.form.get('voice_model')
        vision_model = request.form.get('vision_model')
        language = request.form.get('language', 'Indonesian')
        expertise_key = request.form.get('expertise')
        
        # New features
        resolution = request.form.get('resolution', '9:16')
        image_positioning = request.form.get('image_positioning', 'fit_screen')
        enable_movement = request.form.get('enable_movement') == 'on'
        gpu_acceleration = request.form.get('gpu_acceleration', 'auto')
        
        # Get pause duration
        try:
            pause_duration = float(request.form.get('pause_duration', 0.5))
            if pause_duration < 0:
                pause_duration = 0.5
        except (ValueError, TypeError):
            pause_duration = 0.5
        
        # Get movement speed
        try:
            movement_speed = int(request.form.get('movement_speed', 8))
            if movement_speed < 2 or movement_speed > 20:
                movement_speed = 8
        except (ValueError, TypeError):
            movement_speed = 8
        
        logging.info(f"Movement speed set to: {movement_speed}%")
        logging.info(f"GPU acceleration setting: {gpu_acceleration}")
        logging.info(f"Image positioning for 16:9: {image_positioning}")
        
        # Extract effect weights from form data
        effect_weights = get_effect_weights(request.form) if enable_movement else None
        
        # Validate effect weights if movement is enabled
        if enable_movement and effect_weights:
            total_weight = sum(effect_weights.values())
            if total_weight != 100:
                logging.warning(f"Effect weights total is {total_weight}, not 100. Normalizing...")
                # Normalize weights to sum to 100
                if total_weight > 0:
                    for key in effect_weights:
                        effect_weights[key] = (effect_weights[key] / total_weight) * 100
                else:
                    # Set default weights if all are 0
                    effect_weights = {
                        'pan_right': 20, 'pan_left': 20, 'pan_up': 15,
                        'pan_down': 15, 'zoom_in': 15, 'zoom_out': 15
                    }
        
        # Get system prompt
        prompts = load_prompts()
        system_prompt = prompts.get(expertise_key, "Describe the image.")

        uploaded_files = request.files.getlist('images')
        if not uploaded_files or all(not file.filename for file in uploaded_files):
            logging.error("No files uploaded")
            return redirect(url_for('index'))
        
        scenes = []
        
        # Process each uploaded image
        for i, file in enumerate(uploaded_files):
            if file and file.filename != '':
                logging.info(f"Processing file {i}: {file.filename}")
                
                # Save uploaded file
                image_path = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])
                if not image_path:
                    logging.error(f"Failed to save file: {file.filename}")
                    continue
                
                # Get narration based on mode
                narration = ""
                if mode == 'full-ai':
                    narration = generate_narration(image_path, vision_model, system_prompt, language)
                elif mode == 'semi-auto':
                    custom_prompt = request.form.get(f'prompt_{i}', '')
                    if custom_prompt:
                        custom_system_prompt = f"You are an expert narrator. Use the following context: {custom_prompt}. Describe the image incorporating this context."
                        narration = generate_narration(image_path, vision_model, custom_system_prompt, language)
                    else:
                        logging.warning(f"No custom prompt provided for image {i}")
                        continue
                else:  # semi-manual mode
                    narration = request.form.get(f'narration_{i}', '')

                if not narration or narration.startswith("Error:"):
                    logging.warning(f"Skipping scene for {file.filename} due to narration error: {narration}")
                    continue
                
                # Generate audio (TTS)
                audio_path = generate_unique_filename(f"audio_{i}", "mp3", app.config['GENERATED_FOLDER'])
                logging.info(f"Generating TTS audio for scene {i}")
                
                if generate_tts_audio(narration, voice_model, audio_path):
                    scenes.append({
                        'image_path': image_path, 
                        'narration': narration, 
                        'audio_path': audio_path
                    })
                    logging.info(f"Successfully created scene {i}")
                else:
                    logging.warning(f"Skipping scene for {file.filename} due to audio generation error.")
        
        if not scenes:
            logging.error("No valid scenes created")
            return redirect(url_for('index'))
        
        logging.info(f"Creating video with {len(scenes)} scenes")
        video_path = create_video_from_scenes(
            scenes, 
            app.config['GENERATED_FOLDER'],
            resolution=resolution,
            image_positioning=image_positioning,
            enable_movement=enable_movement,
            effect_weights=effect_weights,
            pause_duration=pause_duration,
            movement_speed=movement_speed,
            gpu_acceleration=gpu_acceleration
        )
        
        if video_path and os.path.exists(video_path):
            # Register the generated media
            media_id = register_generated_media(video_path, scenes)
            logging.info(f"Video generated and registered with ID: {media_id}")
            
            # Clean up temporary files
            cleanup_temporary_files(scenes)
            
            # --- FIX STARTS HERE ---
            # Get the filename from the full path
            video_filename = os.path.basename(video_path)
            # Create a path relative to the 'static' folder for the template
            # This path will be used with url_for('static', filename=...) in the template
            template_video_path = os.path.join('generated', video_filename)
            # --- FIX ENDS HERE ---

            return render_template('index.html', 
                                   video_file=template_video_path, # Use the corrected, dynamic path
                                   tts_voices=TTS_VOICES, 
                                   vision_models=VISION_MODELS, 
                                   prompts=load_prompts(),
                                   languages=LANGUAGES,
                                   gpu_options=GPU_ACCELERATION_OPTIONS)
        else:
            logging.error("Video creation failed")
            return redirect(url_for('index'))

    except Exception as e:
        logging.error(f"Error in video creation: {e}", exc_info=True)
        return redirect(url_for('index'))