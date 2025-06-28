document.addEventListener('DOMContentLoaded', function() {
    const mediaListElement = document.getElementById('media-list');
    const refreshBtn = document.getElementById('refresh-media-btn');
    const cleanupBtn = document.getElementById('cleanup-media-btn');
    const statsContainer = document.getElementById('media-stats');

    // Load media list on page load
    loadMediaList();
    loadMediaStats();

    // Event listeners
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            this.disabled = true;
            this.textContent = 'Refreshing...';
            
            loadMediaList();
            loadMediaStats();
            
            setTimeout(() => {
                this.disabled = false;
                this.textContent = 'Refresh List';
            }, 1000);
        });
    }

    if (cleanupBtn) {
        cleanupBtn.addEventListener('click', function() {
            const confirmMessage = 'Are you sure you want to clean up old media files (older than 7 days)?\n\nThis action cannot be undone and will delete:\n- Old video files\n- Associated uploaded images\n- Registry entries';
            
            if (confirm(confirmMessage)) {
                this.disabled = true;
                this.textContent = 'Cleaning up...';
                cleanupOldMedia();
            }
        });
    }

    async function loadMediaList() {
        try {
            showNotification('Loading media list...', 'info');
            
            const response = await fetch('/media/list');
            if (!response.ok) throw new Error('Failed to fetch media list');
            
            const data = await response.json();
            renderMediaList(data.media_list || []);
            
            showNotification('Media list loaded successfully', 'success');
        } catch (error) {
            console.error('Error loading media list:', error);
            showNotification('Error loading media list', 'error');
        }
    }

    async function loadMediaStats() {
        try {
            const response = await fetch('/media/stats');
            if (!response.ok) throw new Error('Failed to fetch media stats');
            
            const stats = await response.json();
            renderMediaStats(stats);
        } catch (error) {
            console.error('Error loading media stats:', error);
        }
    }

    function renderMediaList(mediaList) {
        if (!mediaListElement) return;
        
        if (!mediaList || mediaList.length === 0) {
            mediaListElement.innerHTML = '<p class="text-muted">No generated videos found.</p>';
            return;
        }

        const listHTML = mediaList.map(media => {
            const createdDate = new Date(media.created_at).toLocaleString();
            const fileSizeMB = (media.file_size / (1024 * 1024)).toFixed(2);
            const statusClass = media.file_exists ? 'success' : 'danger';
            const statusText = media.file_exists ? 'Available' : 'Missing';

            return `
                <div class="media-item" data-id="${media.id}">
                    <div class="media-info">
                        <div class="media-header">
                            <strong>Video ${media.id}</strong>
                            <span class="media-status ${statusClass}">${statusText}</span>
                        </div>
                        <div class="media-details">
                            <span>Created: ${createdDate}</span>
                            <span>Scenes: ${media.scenes_count}</span>
                            <span>Size: ${fileSizeMB} MB</span>
                        </div>
                    </div>
                    <div class="media-actions">
                        ${media.file_exists ? `
                            <button class="button secondary-button download-media-btn" 
                                    data-path="${media.relative_path}" 
                                    data-filename="video_${media.id}.mp4">
                                Download
                            </button>
                        ` : ''}
                        <button class="button danger-button delete-media-btn" 
                                data-id="${media.id}"
                                data-confirm="Are you sure you want to delete Video ${media.id}?\n\nThis will delete:\n- The video file\n- Associated uploaded images (if not used by other videos)\n- Registry entry\n\nThis action cannot be undone.">
                            Delete
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        mediaListElement.innerHTML = listHTML;

        // Attach delete event listeners with improved confirmation
        document.querySelectorAll('.delete-media-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const mediaId = this.dataset.id;
                const confirmMessage = this.dataset.confirm;
                
                if (confirm(confirmMessage)) {
                    // Disable button during deletion
                    this.disabled = true;
                    this.textContent = 'Deleting...';
                    
                    deleteMedia(mediaId).finally(() => {
                        // Re-enable button if deletion fails
                        this.disabled = false;
                        this.textContent = 'Delete';
                    });
                }
            });
        });

        // Attach download event listeners
        document.querySelectorAll('.download-media-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const filePath = this.dataset.path;
                const filename = this.dataset.filename;
                downloadFile(filePath, filename);
            });
        });
    }

    function renderMediaStats(stats) {
        if (!statsContainer) return;

        statsContainer.innerHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">${stats.total_files}</div>
                    <div class="stat-label">Total Videos</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${stats.existing_files}</div>
                    <div class="stat-label">Available</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${stats.total_size_mb} MB</div>
                    <div class="stat-label">Total Size</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${stats.orphaned_files}</div>
                    <div class="stat-label">Missing Files</div>
                </div>
            </div>
        `;
    }

    function downloadFile(filePath, filename) {
        try {
            // Create a temporary anchor element for download
            const link = document.createElement('a');
            link.href = `/static/${filePath}`;
            link.download = filename;
            link.style.display = 'none';
            
            // Add to DOM, click, and remove
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            showNotification('Download started', 'success');
        } catch (error) {
            console.error('Error downloading file:', error);
            showNotification('Error downloading file', 'error');
        }
    }

    async function deleteMedia(mediaId) {
        try {
            showNotification(`Deleting video ${mediaId}...`, 'info');
            
            const response = await fetch('/media/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ media_id: mediaId })
            });

            const result = await response.json();
            if (result.success) {
                showNotification(`Video ${mediaId} deleted successfully`, 'success');
                // Reload both list and stats
                loadMediaList();
                loadMediaStats();
            } else {
                showNotification('Error deleting video: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('Error deleting media:', error);
            showNotification('Error deleting video', 'error');
        }
    }

    async function cleanupOldMedia() {
        try {
            showNotification('Starting cleanup of old media files...', 'info');
            
            const response = await fetch('/media/cleanup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ days_old: 7 })
            });

            const result = await response.json();
            if (result.success) {
                const message = `Cleanup completed! Deleted ${result.deleted_count} old videos and ${result.orphaned_cleaned} orphaned files`;
                showNotification(message, 'success');
                // Reload both list and stats
                loadMediaList();
                loadMediaStats();
            } else {
                showNotification('Error during cleanup: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('Error during cleanup:', error);
            showNotification('Error during cleanup', 'error');
        } finally {
            // Re-enable cleanup button
            if (cleanupBtn) {
                cleanupBtn.disabled = false;
                cleanupBtn.textContent = 'Cleanup Old Videos';
            }
        }
    }

    function showNotification(message, type = 'info') {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.media-notification');
        existingNotifications.forEach(n => n.remove());

        const notification = document.createElement('div');
        notification.className = `media-notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Auto remove after 4 seconds (longer for better readability)
        setTimeout(() => {
            notification.remove();
        }, 4000);
    }
});