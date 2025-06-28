document.addEventListener('DOMContentLoaded', function() {
    const imageInput = document.getElementById('images');
    const previewArea = document.getElementById('image-preview-area');
    
    if (!imageInput || !previewArea) return;

    // Create drag and drop overlay
    const dropZone = document.createElement('div');
    dropZone.className = 'drag-drop-zone';
    dropZone.innerHTML = `
        <div class="drag-drop-content">
            <div class="drag-drop-icon">📁</div>
            <p class="drag-drop-text">Drag & drop images here or <span class="browse-link">browse files</span></p>
            <p class="drag-drop-hint">Supports JPG, PNG, GIF files</p>
        </div>
    `;

    // Insert drop zone before the file input
    imageInput.parentNode.insertBefore(dropZone, imageInput);
    
    // Hide the original file input
    imageInput.style.display = 'none';

    let dragCounter = 0;

    // Drag and drop event handlers
    dropZone.addEventListener('dragenter', function(e) {
        e.preventDefault();
        dragCounter++;
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        dragCounter--;
        if (dragCounter === 0) {
            dropZone.classList.remove('drag-over');
        }
    });

    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dragCounter = 0;
        dropZone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        handleFiles(files);
    });

    // Click to browse
    dropZone.addEventListener('click', function() {
        imageInput.click();
    });

    // Handle file input change
    imageInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        // Validate files
        const validFiles = [];
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
        
        Array.from(files).forEach(file => {
            if (allowedTypes.includes(file.type)) {
                validFiles.push(file);
            } else {
                showNotification(`File "${file.name}" is not a valid image format.`, 'error');
            }
        });

        if (validFiles.length === 0) {
            return;
        }

        // Create a new FileList-like object
        const dt = new DataTransfer();
        validFiles.forEach(file => dt.items.add(file));
        imageInput.files = dt.files;

        // Update drop zone appearance
        updateDropZoneAppearance(validFiles.length);
        
        // Trigger the existing preview update
        if (window.updateImagePreviews) {
            window.updateImagePreviews();
        }

        showNotification(`${validFiles.length} file(s) uploaded successfully!`, 'success');
    }

    function updateDropZoneAppearance(fileCount) {
        if (fileCount > 0) {
            dropZone.classList.add('has-files');
            dropZone.querySelector('.drag-drop-text').innerHTML = 
                `${fileCount} file(s) selected - <span class="browse-link">click to change</span>`;
        } else {
            dropZone.classList.remove('has-files');
            dropZone.querySelector('.drag-drop-text').innerHTML = 
                `Drag & drop images here or <span class="browse-link">browse files</span>`;
        }
    }

    function showNotification(message, type = 'info') {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.upload-notification');
        existingNotifications.forEach(n => n.remove());

        const notification = document.createElement('div');
        notification.className = `upload-notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
});