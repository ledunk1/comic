import os
import logging
from threading import Thread
import time

# ==============================================================================
# TUNNEL MANAGEMENT WITH PYNGROK
# ==============================================================================

class TunnelManager:
    def __init__(self):
        self.tunnel = None
        self.public_url = None
        self.is_running = False
        
    def start_tunnel(self, port=5000, auth_token=None):
        """Start ngrok tunnel."""
        try:
            from pyngrok import ngrok, conf
            
            # Check if there are already active tunnels
            try:
                active_tunnels = ngrok.get_tunnels()
                if active_tunnels:
                    # Use existing tunnel if available
                    for tunnel in active_tunnels:
                        if tunnel.config['addr'] == str(port):
                            self.tunnel = tunnel
                            self.public_url = tunnel.public_url
                            self.is_running = True
                            logging.info(f"Using existing ngrok tunnel: {self.public_url}")
                            return True, self.public_url
                    
                    # If there's a tunnel but not for our port, we can't create another with free account
                    logging.warning("Another ngrok tunnel is already running. Cannot create additional tunnel with free account.")
                    return False, "Another ngrok tunnel is already running. Free accounts are limited to 1 tunnel."
            except Exception as e:
                logging.debug(f"Error checking existing tunnels: {e}")
            
            # Use auth token from environment variable if not provided
            if not auth_token:
                auth_token = os.getenv('NGROK_AUTH_TOKEN')
            
            # Set auth token if available
            if auth_token:
                ngrok.set_auth_token(auth_token)
                logging.info("Using ngrok auth token from environment")
            else:
                logging.info("No ngrok auth token provided - using free tier")
            
            # Kill any existing tunnels to avoid conflicts
            try:
                ngrok.kill()
                time.sleep(1)  # Give it a moment to clean up
            except Exception as e:
                logging.debug(f"Error killing existing tunnels: {e}")
            
            # Start tunnel
            self.tunnel = ngrok.connect(port, "http")
            self.public_url = self.tunnel.public_url
            self.is_running = True
            
            logging.info(f"Ngrok tunnel started: {self.public_url}")
            return True, self.public_url
            
        except ImportError:
            logging.error("pyngrok not installed. Install with: pip install pyngrok")
            return False, "pyngrok not installed"
        except Exception as e:
            error_msg = str(e)
            if "ERR_NGROK_108" in error_msg or "limited to 1 simultaneous" in error_msg:
                logging.warning("Ngrok free account limit reached. Another tunnel is already running.")
                return False, "Ngrok free account limit: Another tunnel is already running"
            else:
                logging.error(f"Error starting ngrok tunnel: {e}")
                return False, str(e)
    
    def stop_tunnel(self):
        """Stop ngrok tunnel."""
        try:
            if self.tunnel:
                from pyngrok import ngrok
                ngrok.disconnect(self.tunnel.public_url)
                self.tunnel = None
                self.public_url = None
                self.is_running = False
                logging.info("Ngrok tunnel stopped")
                return True
        except Exception as e:
            logging.error(f"Error stopping ngrok tunnel: {e}")
            return False
    
    def get_status(self):
        """Get tunnel status."""
        # Check if tunnel is still active
        if self.tunnel:
            try:
                from pyngrok import ngrok
                active_tunnels = ngrok.get_tunnels()
                tunnel_still_active = any(t.public_url == self.public_url for t in active_tunnels)
                if not tunnel_still_active:
                    self.is_running = False
                    self.tunnel = None
                    self.public_url = None
            except Exception as e:
                logging.debug(f"Error checking tunnel status: {e}")
        
        return {
            'is_running': self.is_running,
            'public_url': self.public_url,
            'tunnel_info': str(self.tunnel) if self.tunnel else None
        }
    
    def restart_tunnel(self, port=5000, auth_token=None):
        """Restart tunnel."""
        self.stop_tunnel()
        time.sleep(2)  # Longer pause for cleanup
        return self.start_tunnel(port, auth_token)

# Global tunnel manager instance
tunnel_manager = TunnelManager()

def get_tunnel_manager():
    """Get the global tunnel manager instance."""
    return tunnel_manager