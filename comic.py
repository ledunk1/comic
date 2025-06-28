import os
import logging
import threading
import webbrowser
import tkinter as tk
from tkinter import font
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Asumsikan file-file ini ada di direktori yang sama atau path-nya benar
# Jika file ini tidak ada, Anda bisa membuat file dummy atau hapus bagian import ini
try:
    from utils.config import UPLOAD_FOLDER, GENERATED_FOLDER, ensure_directories
    from routes import register_routes
except ImportError:
    # Fallback jika modul tidak ditemukan (untuk testing)
    print("Peringatan: Modul 'utils' atau 'routes' tidak ditemukan. Menggunakan konfigurasi default.")
    UPLOAD_FOLDER = 'uploads'
    GENERATED_FOLDER = 'generated'
    def ensure_directories():
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(GENERATED_FOLDER, exist_ok=True)
    def register_routes(app):
        @app.route('/')
        def index():
            return "<h1>Flask App Running!</h1><p>Created by tialota.</p>"

# ==============================================================================
# APPLICATION SETUP
# ==============================================================================
app = Flask(__name__)

# Pastikan direktori yang diperlukan ada
ensure_directories()

# Konfigurasi Flask app
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GENERATED_FOLDER'] = GENERATED_FOLDER

# Setup logging
logging.basicConfig(level=logging.INFO)

# Daftarkan semua routes
register_routes(app)

# ==============================================================================
# FLASK & TKINTER FUNCTIONS
# ==============================================================================

def start_flask_app():
    """Fungsi untuk menjalankan server Flask."""
    # Menjalankan Flask tanpa debug mode di thread untuk stabilitas
    # use_reloader=False penting agar tidak me-restart di dalam thread
    print(f"\n{'='*60}")
    print(f"🚀 APPLICATION STARTING")
    print(f"Local URL:  http://localhost:5000")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def open_browser():
    """Fungsi untuk membuka web browser ke halaman utama."""
    webbrowser.open("http://localhost:5000")

def create_tkinter_ui():
    """Fungsi untuk membuat dan menjalankan GUI Tkinter."""
    root = tk.Tk()
    root.title("App Launcher")
    root.geometry("350x180")
    root.resizable(False, False)
    
    # Atur style font
    title_font = font.Font(family="Helvetica", size=12, weight="bold")
    button_font = font.Font(family="Helvetica", size=10)
    credit_font = font.Font(family="Helvetica", size=9, slant="italic")

    # Frame utama untuk padding
    main_frame = tk.Frame(root, padx=20, pady=20)
    main_frame.pack(expand=True, fill="both")

    # Label status
    status_label = tk.Label(
        main_frame, 
        text="Server Flask sedang berjalan.",
        font=title_font
    )
    status_label.pack(pady=(0, 10))

    # Tombol untuk membuka browser
    open_button = tk.Button(
        main_frame, 
        text="Buka di Browser", 
        command=open_browser,
        font=button_font,
        bg="#4CAF50", # Warna hijau
        fg="white",   # Teks putih
        relief="flat",
        padx=10,
        pady=5
    )
    open_button.pack(pady=10)

    # Label kredit
    credit_label = tk.Label(
        main_frame, 
        text="Created by tialota", 
        font=credit_font, 
        fg="grey"
    )
    credit_label.pack(side="bottom")

    root.mainloop()

# ==============================================================================
# APPLICATION STARTUP
# ==============================================================================
if __name__ == '__main__':
    # Jalankan server Flask di thread terpisah agar tidak memblokir UI
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.daemon = True  # Set daemon agar thread berhenti saat program utama ditutup
    flask_thread.start()

    # Buat dan jalankan UI Tkinter di thread utama
    create_tkinter_ui()
