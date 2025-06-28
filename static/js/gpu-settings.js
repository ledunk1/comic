document.addEventListener('DOMContentLoaded', function() {
    const gpuOptions = document.querySelectorAll('.gpu-option');
    const gpuDetectionInfo = document.getElementById('gpu-detection-info');
    const refreshGpuBtn = document.getElementById('refresh-gpu-btn');
    
    // Initialize GPU option selection
    initializeGpuOptions();
    
    // Load GPU encoder information
    loadGpuEncoders();
    
    // Refresh button event listener
    if (refreshGpuBtn) {
        refreshGpuBtn.addEventListener('click', function() {
            loadGpuEncoders();
        });
    }
    
    function initializeGpuOptions() {
        gpuOptions.forEach(option => {
            const radio = option.querySelector('input[type="radio"]');
            
            // Handle option selection
            option.addEventListener('click', function() {
                // Remove selected class from all options
                gpuOptions.forEach(opt => opt.classList.remove('selected'));
                
                // Add selected class to clicked option
                this.classList.add('selected');
                
                // Check the radio button
                if (radio) {
                    radio.checked = true;
                }
                
                console.log(`GPU acceleration option selected: ${radio.value}`);
            });
            
            // Set initial selection
            if (radio && radio.checked) {
                option.classList.add('selected');
            }
        });
    }
    
    async function loadGpuEncoders() {
        if (!gpuDetectionInfo) return;
        
        // Show loading state
        const detectionList = gpuDetectionInfo.querySelector('.gpu-detection-list');
        if (detectionList) {
            detectionList.innerHTML = '<div class="gpu-detection-loading">Detecting available encoders...</div>';
        }
        
        try {
            const response = await fetch('/api/gpu-encoders');
            if (!response.ok) throw new Error('Failed to fetch GPU encoders');
            
            const data = await response.json();
            if (data.success) {
                renderGpuEncoders(data.encoders);
            } else {
                showGpuError('Error detecting encoders: ' + data.error);
            }
        } catch (error) {
            console.error('Error loading GPU encoders:', error);
            showGpuError('Failed to detect GPU encoders');
        }
    }
    
    function renderGpuEncoders(encoders) {
        const detectionList = gpuDetectionInfo.querySelector('.gpu-detection-list');
        if (!detectionList) return;
        
        let html = '';
        
        // Sort encoders by availability (available first)
        const sortedEncoders = Object.entries(encoders).sort((a, b) => {
            return b[1].available - a[1].available;
        });
        
        sortedEncoders.forEach(([key, encoder]) => {
            const statusClass = encoder.available ? 'available' : 'unavailable';
            const statusText = encoder.available ? 'Available' : 'Not Available';
            
            html += `
                <div class="gpu-encoder-item">
                    <span class="encoder-name">${encoder.name}</span>
                    <span class="encoder-status ${statusClass}">${statusText}</span>
                </div>
            `;
        });
        
        detectionList.innerHTML = html;
        
        // Update GPU option availability
        updateGpuOptionAvailability(encoders);
        
        console.log('GPU encoders loaded:', encoders);
    }
    
    function updateGpuOptionAvailability(encoders) {
        gpuOptions.forEach(option => {
            const radio = option.querySelector('input[type="radio"]');
            const statusElement = option.querySelector('.gpu-status');
            
            if (!radio || !statusElement) return;
            
            const optionValue = radio.value;
            let isAvailable = true;
            
            // Check availability based on option value
            switch (optionValue) {
                case 'intel':
                    isAvailable = encoders.intel_qsv?.available || false;
                    break;
                case 'nvidia':
                    isAvailable = encoders.nvidia_nvenc?.available || false;
                    break;
                case 'amd':
                    isAvailable = encoders.amd_amf?.available || false;
                    break;
                case 'cpu':
                    isAvailable = true; // CPU is always available
                    break;
                case 'auto':
                    isAvailable = true; // Auto is always available
                    break;
            }
            
            // Update status display
            if (optionValue === 'auto') {
                statusElement.textContent = 'Smart';
                statusElement.className = 'gpu-status auto';
            } else if (isAvailable) {
                statusElement.textContent = 'Available';
                statusElement.className = 'gpu-status available';
            } else {
                statusElement.textContent = 'Not Available';
                statusElement.className = 'gpu-status unavailable';
            }
            
            // Disable option if not available (except auto and cpu)
            if (!isAvailable && optionValue !== 'auto' && optionValue !== 'cpu') {
                option.style.opacity = '0.6';
                option.style.pointerEvents = 'none';
                radio.disabled = true;
                
                // If this option was selected, switch to auto
                if (radio.checked) {
                    const autoOption = document.querySelector('input[value="auto"]');
                    if (autoOption) {
                        autoOption.checked = true;
                        autoOption.closest('.gpu-option').classList.add('selected');
                        option.classList.remove('selected');
                    }
                }
            } else {
                option.style.opacity = '1';
                option.style.pointerEvents = 'auto';
                radio.disabled = false;
            }
        });
    }
    
    function showGpuError(message) {
        const detectionList = gpuDetectionInfo.querySelector('.gpu-detection-list');
        if (detectionList) {
            detectionList.innerHTML = `
                <div style="color: var(--danger-color); font-style: italic;">
                    ${message}
                </div>
            `;
        }
    }
    
    // Show notification for GPU selection
    function showGpuNotification(message, type = 'info') {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.gpu-notification');
        existingNotifications.forEach(n => n.remove());

        const notification = document.createElement('div');
        notification.className = `upload-notification gpu-notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    // Monitor form submission to show encoding info
    const form = document.getElementById('creation-form');
    if (form) {
        form.addEventListener('submit', function() {
            const selectedOption = document.querySelector('input[name="gpu_acceleration"]:checked');
            if (selectedOption) {
                const optionLabel = selectedOption.closest('.gpu-option').querySelector('.gpu-option-title').textContent;
                showGpuNotification(`Using ${optionLabel} for video encoding`, 'info');
            }
        });
    }
});