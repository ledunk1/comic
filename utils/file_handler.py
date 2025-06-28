import os
import uuid
import logging
from werkzeug.utils import secure_filename

def save_uploaded_file(file, upload_folder):
    """
    Menyimpan file yang diunggah ke folder yang ditentukan dengan nama yang unik.
    Sangat penting, fungsi ini mengembalikan path lengkap ke file yang disimpan.
    """
    if not file or not file.filename:
        logging.warning("Upaya penyimpanan file gagal: tidak ada file atau nama file.")
        return None
    
    # Membersihkan nama file untuk keamanan
    filename = secure_filename(file.filename)
    # Membuat nama file yang unik untuk menghindari penimpaan file
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    # Membuat path lengkap tempat file akan disimpan
    full_path = os.path.join(upload_folder, unique_filename)
    
    try:
        file.save(full_path)
        logging.info(f"File berhasil disimpan di: {full_path}")
        return full_path # Mengembalikan path lengkap yang benar
    except Exception as e:
        logging.error(f"Terjadi kesalahan saat menyimpan file {full_path}: {e}")
        return None

def generate_unique_filename(prefix, extension, folder):
    """Menghasilkan nama file yang unik dengan path lengkap di dalam folder yang ditentukan."""
    filename = f"{prefix}_{uuid.uuid4().hex}.{extension}"
    return os.path.join(folder, filename)
