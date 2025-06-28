import os
import json
import logging
from .config import PROMPTS_FILE

# ==============================================================================
# PROMPT MANAGEMENT FUNCTIONS
# ==============================================================================

def load_prompts():
    """Load prompts from JSON file."""
    if not os.path.exists(PROMPTS_FILE):
        # Create default file if it doesn't exist
        default_prompts = {
            "Expert Narrator": "You are an expert narrator. Describe the following image in a clear, concise, and engaging way for a short explainer video. Focus on the key elements and their meaning.",
            "Comic Book Style": "You are a classic comic book narrator. Describe this scene with a dramatic and punchy tone. Use onomatopoeia if it fits.",
            "Simple Explainer": "You are a friendly teacher. Explain what is happening in this image in simple terms that anyone can understand."
        }
        with open(PROMPTS_FILE, 'w') as f:
            json.dump(default_prompts, f, indent=4)
        return default_prompts
    
    try:
        with open(PROMPTS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(f"Error loading prompts: {e}")
        return {}

def save_prompts(prompts_data):
    """Save prompts to JSON file."""
    try:
        with open(PROMPTS_FILE, 'w') as f:
            json.dump(prompts_data, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"Error saving prompts: {e}")
        return False

def add_prompt(name, text):
    """Add a new prompt."""
    if not name or not text:
        return False, "Name and text are required"
    
    prompts = load_prompts()
    prompts[name] = text
    
    if save_prompts(prompts):
        return True, prompts
    return False, "Failed to save prompt"

def delete_prompt(name):
    """Delete a prompt by name."""
    if not name:
        return False, "Name is required"
    
    prompts = load_prompts()
    if name not in prompts:
        return False, "Prompt not found"
    
    del prompts[name]
    
    if save_prompts(prompts):
        return True, prompts
    return False, "Failed to save prompts"

def update_prompt(name, new_text):
    """Update an existing prompt."""
    if not name or not new_text:
        return False, "Name and new text are required"
    
    prompts = load_prompts()
    if name not in prompts:
        return False, "Prompt not found"
    
    prompts[name] = new_text
    
    if save_prompts(prompts):
        return True, prompts
    return False, "Failed to save prompts"