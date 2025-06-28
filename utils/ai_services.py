import os
import base64
import requests
import logging
import time
import asyncio
from threading import Lock

# ==============================================================================
# RATE LIMITING CONFIGURATION
# ==============================================================================

# Rate limiting for different API endpoints
RATE_LIMITS = {
    'vision': {
        'max_concurrent': 1,
        'interval': 3.0,  # 3 seconds between requests
        'last_request_time': 0,
        'lock': Lock()
    },
    'tts': {
        'interval': 15.0,  # 15 seconds between requests
        'last_request_time': 0,
        'lock': Lock()
    }
}

def wait_for_rate_limit(api_type):
    """Wait for rate limit before making API request."""
    if api_type not in RATE_LIMITS:
        return
    
    rate_limit = RATE_LIMITS[api_type]
    
    with rate_limit['lock']:
        current_time = time.time()
        time_since_last = current_time - rate_limit['last_request_time']
        
        if time_since_last < rate_limit['interval']:
            wait_time = rate_limit['interval'] - time_since_last
            logging.info(f"Rate limiting {api_type}: waiting {wait_time:.1f} seconds")
            time.sleep(wait_time)
        
        rate_limit['last_request_time'] = time.time()

# ==============================================================================
# AI SERVICE FUNCTIONS (POLLINATIONS API)
# ==============================================================================

def generate_narration(image_path, vision_model, system_prompt, language="Indonesian"):
    """Analyze image and generate narration in specified language with rate limiting."""
    logging.info(f"Generating narration for {os.path.basename(image_path)} in {language} using model {vision_model}")
    
    # Apply rate limiting for vision API
    wait_for_rate_limit('vision')
    
    try:
        # Check if image file exists
        if not os.path.exists(image_path):
            logging.error(f"Image file not found: {image_path}")
            return f"Error: Image file not found"
        
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        headers = {"Content-Type": "application/json"}
        
        # Improved prompt for better narration quality
        user_text_prompt = f"""Describe this image for a short comic explainer video. 
        Requirements:
        - Keep it concise but complete (1-2 sentences maximum)
        - Focus on the main action or story element
        - Use clear, engaging language suitable for narration
        - Avoid overly complex words that might be hard to pronounce
        - Write in {language} language
        - Make it sound natural when spoken aloud"""

        payload = {
            "model": vision_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        }
        
        # POST endpoint for vision capabilities
        response = requests.post("https://text.pollinations.ai/openai", headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        
        data = response.json()
        if 'choices' in data and len(data['choices']) > 0:
            narration = data['choices'][0]['message']['content'].strip()
            
            # Clean up narration text for better TTS
            narration = clean_narration_text(narration)
            
            logging.info(f"Narration received: {narration}")
            return narration
        else:
            logging.error(f"Unexpected API response format: {data}")
            return f"Error: Unexpected API response format"
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error generating narration: {e}")
        return f"Error: Network error - {str(e)}"
    except Exception as e:
        logging.error(f"Error generating narration: {e}")
        return f"Error: Could not generate narration for {os.path.basename(image_path)}."

def clean_narration_text(text):
    """Clean narration text for better TTS quality."""
    # Remove quotes and unnecessary punctuation that might affect TTS
    text = text.replace('"', '').replace("'", "")
    
    # Replace problematic characters
    text = text.replace('&', 'dan')
    text = text.replace('@', 'at')
    text = text.replace('#', 'hashtag')
    text = text.replace('%', 'persen')
    
    # Ensure proper sentence ending
    if not text.endswith(('.', '!', '?')):
        text += '.'
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text

def generate_tts_audio(narration, voice_model, output_path):
    """Generate audio from narration text with improved handling for longer text."""
    logging.info(f"Generating audio for narration: '{narration[:50]}...' with voice {voice_model}")
    
    # Apply rate limiting for TTS API
    wait_for_rate_limit('tts')
    
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Clean and prepare narration for TTS
        cleaned_narration = clean_narration_text(narration)
        
        # Check text length and split if necessary
        max_length = 500  # Conservative limit for URL length
        if len(cleaned_narration) > max_length:
            logging.warning(f"Narration too long ({len(cleaned_narration)} chars), splitting...")
            return generate_long_tts_audio(cleaned_narration, voice_model, output_path)
        
        # Use POST method for better reliability with longer text
        success = generate_tts_post_method(cleaned_narration, voice_model, output_path)
        
        if not success:
            # Fallback to GET method with shorter text
            logging.info("POST method failed, trying GET method with truncated text...")
            truncated_text = cleaned_narration[:300] + "..." if len(cleaned_narration) > 300 else cleaned_narration
            success = generate_tts_get_method(truncated_text, voice_model, output_path)
        
        return success
        
    except Exception as e:
        logging.error(f"Error generating TTS audio: {e}")
        return False

def generate_tts_post_method(narration, voice_model, output_path):
    """Generate TTS using POST method for better handling of longer text."""
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": "openai-audio",
            "voice": voice_model,
            "input": f"baca teks ini dengan jelas dan lengkap: {narration}",
            "response_format": "mp3"
        }
        
        response = requests.post("https://text.pollinations.ai/openai/audio/speech", 
                               headers=headers, json=payload, timeout=90)
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'audio' in content_type or len(response.content) > 1000:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logging.info(f"Audio saved successfully via POST method: {output_path}")
                    return True
        
        logging.warning("POST method did not return valid audio")
        return False
        
    except Exception as e:
        logging.warning(f"POST method failed: {e}")
        return False

def generate_tts_get_method(narration, voice_model, output_path):
    """Generate TTS using GET method (fallback)."""
    try:
        # Prepare TTS prompt
        tts_prompt = f"baca teks ini dengan jelas: {narration}"
        encoded_narration = requests.utils.quote(tts_prompt)
        
        # Ensure URL is not too long
        if len(encoded_narration) > 800:
            # Further truncate if still too long
            short_narration = narration[:200] + "..."
            tts_prompt = f"baca teks ini: {short_narration}"
            encoded_narration = requests.utils.quote(tts_prompt)
        
        url = f"https://text.pollinations.ai/{encoded_narration}."
        params = {"model": "openai-audio", "voice": voice_model}
        
        response = requests.get(url, params=params, timeout=90)
        response.raise_for_status()
        
        # Check if response contains audio
        content_type = response.headers.get('Content-Type', '')
        if 'audio' in content_type or len(response.content) > 1000:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logging.info(f"Audio saved successfully via GET method: {output_path}")
                return True
        
        logging.error(f"GET method did not return valid audio. Content-Type: {content_type}")
        return False
        
    except Exception as e:
        logging.error(f"GET method failed: {e}")
        return False

def generate_long_tts_audio(narration, voice_model, output_path):
    """Handle long narration by splitting into chunks and combining."""
    try:
        from moviepy.editor import AudioFileClip, concatenate_audioclips
        
        # Split narration into sentences
        sentences = split_into_sentences(narration)
        audio_chunks = []
        temp_files = []
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
                
            temp_path = output_path.replace('.mp3', f'_chunk_{i}.mp3')
            temp_files.append(temp_path)
            
            # Generate audio for this chunk
            success = generate_tts_post_method(sentence, voice_model, temp_path)
            if not success:
                success = generate_tts_get_method(sentence, voice_model, temp_path)
            
            if success and os.path.exists(temp_path):
                audio_chunks.append(temp_path)
            else:
                logging.warning(f"Failed to generate audio for chunk {i}: {sentence[:50]}...")
        
        if not audio_chunks:
            logging.error("No audio chunks were generated successfully")
            return False
        
        # Combine audio chunks
        if len(audio_chunks) == 1:
            # Only one chunk, just rename it
            os.rename(audio_chunks[0], output_path)
        else:
            # Multiple chunks, combine them
            clips = [AudioFileClip(chunk) for chunk in audio_chunks]
            final_audio = concatenate_audioclips(clips)
            final_audio.write_audiofile(output_path, logger=None)
            
            # Clean up clips
            for clip in clips:
                clip.close()
            final_audio.close()
        
        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file) and temp_file != output_path:
                try:
                    os.remove(temp_file)
                except:
                    pass
        
        logging.info(f"Long audio generated successfully: {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error generating long TTS audio: {e}")
        return False

def split_into_sentences(text):
    """Split text into sentences for better TTS processing."""
    import re
    
    # Split by sentence endings
    sentences = re.split(r'[.!?]+', text)
    
    # Clean and filter sentences
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and len(sentence) > 3:  # Ignore very short fragments
            # Ensure sentence ends properly
            if not sentence.endswith(('.', '!', '?')):
                sentence += '.'
            cleaned_sentences.append(sentence)
    
    # If no proper sentences found, split by length
    if not cleaned_sentences:
        max_chunk = 200
        cleaned_sentences = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
    
    return cleaned_sentences