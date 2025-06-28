import os

# ==============================================================================
# APPLICATION CONFIGURATION
# ==============================================================================

# Folder paths
UPLOAD_FOLDER = os.path.join('static', 'uploads')
GENERATED_FOLDER = os.path.join('static', 'generated')
PROMPTS_FILE = 'prompts.json'

# Model and language lists
TTS_VOICES = [
    "alloy", "echo", "fable", "onyx", "nova", "shimmer", "ash", "coral", "sage", 
    "verse", "ballad", "amuch", "aster", "brook", "clover", "dan", "elan", 
    "marilyn", "meadow", "jazz", "rio", "megan-wetherall", "jade-hardy"
]

VISION_MODELS = [
    "openai", "openai-fast", "openai-large", "bidara", "sur", "phi", "evil", 
    "mirexa", "unity", "mistral"
]

LANGUAGES = ["Indonesian", "English", "Japanese", "Spanish", "French", "German"]

# GPU Acceleration options
GPU_ACCELERATION_OPTIONS = [
    {"value": "auto", "label": "Auto (Best Available)", "description": "Automatically select the best encoder"},
    {"value": "cpu", "label": "CPU Only (libx264)", "description": "Use CPU encoding (most compatible)"},
    {"value": "intel", "label": "Intel QSV", "description": "Intel hardware acceleration"},
    {"value": "nvidia", "label": "NVIDIA NVENC", "description": "NVIDIA GPU acceleration"},
    {"value": "amd", "label": "AMD AMF", "description": "AMD GPU acceleration"}
]

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(GENERATED_FOLDER, exist_ok=True)