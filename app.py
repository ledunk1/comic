import os
import logging
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import utility modules
from utils.config import UPLOAD_FOLDER, GENERATED_FOLDER, ensure_directories
from routes import register_routes
from utils.tunnel_manager import get_tunnel_manager

# ==============================================================================
# APPLICATION SETUP
# ==============================================================================
app = Flask(__name__)

# Ensure directories exist
ensure_directories()

# Configure Flask app
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GENERATED_FOLDER'] = GENERATED_FOLDER

# Setup logging
logging.basicConfig(level=logging.INFO)

# Register all routes
register_routes(app)

# ==============================================================================
# APPLICATION STARTUP
# ==============================================================================
if __name__ == '__main__':
    # Check if tunnel should be enabled
    enable_tunnel = os.getenv('ENABLE_TUNNEL', 'false').lower() == 'true'
    
    if enable_tunnel:
        tunnel_manager = get_tunnel_manager()
        success, result = tunnel_manager.start_tunnel(port=5000)
        
        if success:
            logging.info(f"🌐 Tunnel started successfully! Public URL: {result}")
            print(f"\n{'='*60}")
            print(f"🌐 PUBLIC ACCESS AVAILABLE")
            print(f"Local URL:  http://localhost:5000")
            print(f"Public URL: {result}")
            print(f"{'='*60}\n")
        else:
            logging.warning(f"Failed to start tunnel: {result}")
            print(f"\n{'='*60}")
            print(f"⚠️  Tunnel failed to start")
            print(f"Reason: {result}")
            print(f"Local URL:  http://localhost:5000")
            print(f"💡 Tip: You can still use the local URL or manually start ngrok")
            print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"🚀 APPLICATION STARTING")
        print(f"Local URL:  http://localhost:5000")
        print(f"💡 Set ENABLE_TUNNEL=true to auto-start ngrok")
        print(f"{'='*60}\n")
    
    # Start Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)