import os
import logging
import json
from datetime import datetime, timedelta
from .config import GENERATED_FOLDER, UPLOAD_FOLDER

# ==============================================================================
# MEDIA MANAGEMENT FUNCTIONS
# ==============================================================================

MEDIA_REGISTRY_FILE = os.path.join(GENERATED_FOLDER, 'media_registry.json')

def load_media_registry():
    """Load media registry from JSON file."""
    if not os.path.exists(MEDIA_REGISTRY_FILE):
        return {}
    
    try:
        with open(MEDIA_REGISTRY_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(f"Error loading media registry: {e}")
        return {}

def save_media_registry(registry):
    """Save media registry to JSON file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(MEDIA_REGISTRY_FILE), exist_ok=True)
        
        with open(MEDIA_REGISTRY_FILE, 'w') as f:
            json.dump(registry, f, indent=4)
        logging.info(f"Media registry saved successfully with {len(registry)} entries")
        return True
    except Exception as e:
        logging.error(f"Error saving media registry: {e}")
        return False

def register_generated_media(video_path, scenes_data):
    """Register generated media in the registry."""
    registry = load_media_registry()
    
    media_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Ensure unique media_id
    counter = 1
    original_id = media_id
    while media_id in registry:
        media_id = f"{original_id}_{counter}"
        counter += 1
    
    registry[media_id] = {
        'video_path': video_path,
        'created_at': datetime.now().isoformat(),
        'scenes_count': len(scenes_data),
        'file_size': os.path.getsize(video_path) if os.path.exists(video_path) else 0,
        'scenes_data': scenes_data
    }
    
    if save_media_registry(registry):
        logging.info(f"Registered media with ID: {media_id}")
        return media_id
    else:
        logging.error(f"Failed to register media with ID: {media_id}")
        return None

def get_all_generated_media():
    """Get all generated media with their details."""
    registry = load_media_registry()
    media_list = []
    
    for media_id, data in registry.items():
        # Check if file still exists
        video_path = data.get('video_path', '')
        file_exists = os.path.exists(video_path) if video_path else False
        
        # Create relative path for web access
        relative_path = ''
        if file_exists and video_path:
            try:
                # Convert absolute path to relative path from static folder
                if video_path.startswith('static'):
                    relative_path = video_path.replace('static/', '').replace('static\\', '')
                else:
                    relative_path = os.path.relpath(video_path, 'static')
                # Normalize path separators for web
                relative_path = relative_path.replace('\\', '/')
            except Exception as e:
                logging.warning(f"Error creating relative path for {video_path}: {e}")
                relative_path = ''
        
        media_info = {
            'id': media_id,
            'video_path': video_path,
            'created_at': data.get('created_at', ''),
            'scenes_count': data.get('scenes_count', 0),
            'file_size': data.get('file_size', 0),
            'file_exists': file_exists,
            'relative_path': relative_path
        }
        media_list.append(media_info)
    
    # Sort by creation date (newest first)
    media_list.sort(key=lambda x: x['created_at'], reverse=True)
    logging.info(f"Retrieved {len(media_list)} media entries")
    return media_list

def delete_generated_media(media_id):
    """Delete ONLY the specified media and remove from registry."""
    logging.info(f"Attempting to delete media with ID: {media_id}")
    
    registry = load_media_registry()
    
    if media_id not in registry:
        logging.warning(f"Media ID {media_id} not found in registry")
        return False, "Media not found in registry"
    
    # Get the specific media data for this ID only
    media_data = registry[media_id]
    video_path = media_data.get('video_path')
    scenes_data = media_data.get('scenes_data', [])
    
    deleted_files = []
    errors = []
    
    # Delete video file if exists - ONLY for this specific media
    if video_path and os.path.exists(video_path):
        try:
            os.remove(video_path)
            deleted_files.append(f"video: {os.path.basename(video_path)}")
            logging.info(f"Deleted video file: {video_path}")
        except Exception as e:
            error_msg = f"Error deleting video file {video_path}: {e}"
            logging.error(error_msg)
            errors.append(error_msg)
    
    # Delete associated uploaded image files - ONLY for this specific media
    for scene in scenes_data:
        image_path = scene.get('image_path')
        if image_path and os.path.exists(image_path):
            # CRITICAL: Check if this image is used by other media before deleting
            image_used_elsewhere = False
            for other_id, other_data in registry.items():
                if other_id != media_id:  # Skip the current media being deleted
                    other_scenes = other_data.get('scenes_data', [])
                    for other_scene in other_scenes:
                        if other_scene.get('image_path') == image_path:
                            image_used_elsewhere = True
                            logging.info(f"Image {image_path} is used by media {other_id}, not deleting")
                            break
                    if image_used_elsewhere:
                        break
            
            # Only delete if not used by other media
            if not image_used_elsewhere:
                try:
                    os.remove(image_path)
                    deleted_files.append(f"image: {os.path.basename(image_path)}")
                    logging.info(f"Deleted uploaded image file: {image_path}")
                except Exception as e:
                    error_msg = f"Error deleting image file {image_path}: {e}"
                    logging.error(error_msg)
                    errors.append(error_msg)
            else:
                logging.info(f"Skipped deleting shared image: {os.path.basename(image_path)}")
    
    # Remove ONLY this specific media_id from registry
    try:
        del registry[media_id]
        logging.info(f"Removed media ID {media_id} from registry")
    except KeyError:
        logging.warning(f"Media ID {media_id} was not in registry")
    
    # Save updated registry
    if save_media_registry(registry):
        success_msg = f"Media {media_id} deleted successfully"
        if deleted_files:
            success_msg += f". Deleted files: {', '.join(deleted_files)}"
        if errors:
            success_msg += f". Errors: {'; '.join(errors)}"
        
        logging.info(success_msg)
        return True, success_msg
    else:
        error_msg = "Error updating registry after deletion"
        logging.error(error_msg)
        return False, error_msg

def cleanup_old_media(days_old=7):
    """Clean up media files older than specified days."""
    logging.info(f"Starting cleanup of media older than {days_old} days")
    
    registry = load_media_registry()
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    deleted_count = 0
    media_ids_to_delete = []
    
    # First, identify which media to delete
    for media_id, data in registry.items():
        try:
            created_at_str = data.get('created_at', '')
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str)
                if created_at < cutoff_date:
                    media_ids_to_delete.append(media_id)
                    logging.info(f"Media {media_id} marked for deletion (created: {created_at})")
        except Exception as e:
            logging.error(f"Error processing media {media_id} for cleanup: {e}")
    
    # Then delete each identified media ONE BY ONE
    for media_id in media_ids_to_delete:
        try:
            success, message = delete_generated_media(media_id)
            if success:
                deleted_count += 1
                logging.info(f"Auto-deleted old media: {media_id}")
            else:
                logging.warning(f"Failed to delete old media {media_id}: {message}")
        except Exception as e:
            logging.error(f"Error deleting old media {media_id}: {e}")
    
    logging.info(f"Cleanup completed. Deleted {deleted_count} old media files")
    return deleted_count

def get_media_stats():
    """Get statistics about generated media."""
    registry = load_media_registry()
    
    total_files = len(registry)
    total_size = 0
    existing_files = 0
    
    for data in registry.values():
        video_path = data.get('video_path', '')
        if video_path and os.path.exists(video_path):
            existing_files += 1
            file_size = data.get('file_size', 0)
            if file_size == 0 and os.path.exists(video_path):
                # Recalculate file size if not stored
                try:
                    file_size = os.path.getsize(video_path)
                except:
                    file_size = 0
            total_size += file_size
    
    stats = {
        'total_files': total_files,
        'existing_files': existing_files,
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'orphaned_files': total_files - existing_files
    }
    
    logging.info(f"Media stats: {stats}")
    return stats

def cleanup_orphaned_files():
    """Clean up files that exist but are not in registry."""
    logging.info("Starting cleanup of orphaned files")
    
    deleted_count = 0
    
    # Clean up orphaned video files in generated folder
    if os.path.exists(GENERATED_FOLDER):
        registry = load_media_registry()
        registered_files = set()
        
        # Get all registered file paths
        for data in registry.values():
            video_path = data.get('video_path')
            if video_path:
                registered_files.add(os.path.abspath(video_path))
        
        # Check all files in generated folder
        try:
            for filename in os.listdir(GENERATED_FOLDER):
                if filename.endswith('.mp4'):
                    file_path = os.path.join(GENERATED_FOLDER, filename)
                    abs_path = os.path.abspath(file_path)
                    
                    if abs_path not in registered_files:
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                            logging.info(f"Deleted orphaned video file: {filename}")
                        except Exception as e:
                            logging.error(f"Error deleting orphaned file {filename}: {e}")
        except Exception as e:
            logging.error(f"Error scanning generated folder: {e}")
    
    # Clean up orphaned uploaded image files
    if os.path.exists(UPLOAD_FOLDER):
        registry = load_media_registry()
        registered_images = set()
        
        # Get all registered image paths
        for data in registry.values():
            scenes_data = data.get('scenes_data', [])
            for scene in scenes_data:
                image_path = scene.get('image_path')
                if image_path:
                    registered_images.add(os.path.abspath(image_path))
        
        # Check all files in upload folder
        try:
            for filename in os.listdir(UPLOAD_FOLDER):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    abs_path = os.path.abspath(file_path)
                    
                    if abs_path not in registered_images:
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                            logging.info(f"Deleted orphaned image file: {filename}")
                        except Exception as e:
                            logging.error(f"Error deleting orphaned image file {filename}: {e}")
        except Exception as e:
            logging.error(f"Error scanning upload folder: {e}")
    
    logging.info(f"Orphaned files cleanup completed. Deleted {deleted_count} files")
    return deleted_count