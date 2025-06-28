document.addEventListener('DOMContentLoaded', function() {

    const form = document.getElementById('creation-form');
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    const imageInput = document.getElementById('images');
    const previewArea = document.getElementById('image-preview-area');
    const loader = document.querySelector('.loader');
    const submitButtonText = document.querySelector('.button-text');

    // New elements for video settings
    const resolutionSelect = document.getElementById('resolution');
    const imagePositioningOptions = document.getElementById('image-positioning-options');

    // Prompt Manager Elements
    const promptList = document.getElementById('prompt-list');
    const addPromptBtn = document.getElementById('add-prompt-btn');
    const newPromptNameInput = document.getElementById('new-prompt-name');
    const newPromptTextInput = document.getElementById('new-prompt-text');
    const expertiseSelect = document.getElementById('expertise');
    const expertiseGroup = document.getElementById('expertise-group');

    // --- MAIN FORM LOGIC ---

    // Function to handle resolution change
    function handleResolutionChange() {
        const selectedResolution = resolutionSelect.value;
        if (selectedResolution === '16:9') {
            imagePositioningOptions.style.display = 'block';
        } else {
            imagePositioningOptions.style.display = 'none';
            // Reset to default when not 16:9
            const fitScreenRadio = document.querySelector('input[name="image_positioning"][value="fit_screen"]');
            if (fitScreenRadio) {
                fitScreenRadio.checked = true;
            }
        }
    }

    // Function to handle mode change
    function handleModeChange() {
        const selectedMode = document.querySelector('input[name="mode"]:checked').value;
        document.querySelectorAll('.radio-group label').forEach(label => {
             label.classList.remove('checked');
        });
        document.querySelector(`input[value="${selectedMode}"]`).parentElement.classList.add('checked');

        // Show/hide expertise group based on mode
        if (selectedMode === 'semi-auto') {
            expertiseGroup.style.display = 'none';
        } else {
            expertiseGroup.style.display = 'block';
        }

        updateImagePreviews(); // Update previews to show/hide textareas
    }

    // Function to handle image positioning radio change
    function handleImagePositioningChange() {
        const positioningRadios = document.querySelectorAll('input[name="image_positioning"]');
        positioningRadios.forEach(radio => {
            const label = radio.parentElement;
            if (radio.checked) {
                label.classList.add('checked');
            } else {
                label.classList.remove('checked');
            }
        });
    }

    // Function to update image previews
    function updateImagePreviews() {
        previewArea.innerHTML = ''; // Clear existing previews
        const files = imageInput.files;
        const selectedMode = document.querySelector('input[name="mode"]:checked').value;

        if (files.length > 0) {
            previewArea.style.display = 'grid';
        } else {
            previewArea.style.display = 'none';
        }

        Array.from(files).forEach((file, index) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                const previewCard = document.createElement('div');
                previewCard.className = 'preview-card';
                
                let innerHTML = `<img src="${e.target.result}" alt="Preview of ${file.name}">`;

                if (selectedMode === 'semi-manual') {
                    innerHTML += `
                        <div class="narration-input">
                            <label for="narration_${index}">Narration for ${file.name}</label>
                            <textarea name="narration_${index}" id="narration_${index}" placeholder="Write narration here..." required></textarea>
                        </div>
                    `;
                } else if (selectedMode === 'semi-auto') {
                    innerHTML += `
                        <div class="narration-input">
                            <label for="prompt_${index}">Custom Prompt for ${file.name}</label>
                            <textarea name="prompt_${index}" id="prompt_${index}" placeholder="Enter custom prompt here (e.g., 'This shows character John fighting the villain in the city. John is wearing red cape and has super strength...')" required></textarea>
                            <small class="prompt-hint">💡 Tip: Include character names, actions, settings, and any specific details you want in the narration</small>
                        </div>
                    `;
                }
                
                previewCard.innerHTML = innerHTML;
                previewArea.appendChild(previewCard);
            };
            reader.readAsDataURL(file);
        });
    }

    // Show loader on form submission
    if (form) {
        form.addEventListener('submit', function() {
            if (loader) loader.style.display = 'block';
            if (submitButtonText) submitButtonText.style.display = 'none';
        });
    }

    // Attach event listeners
    if (modeRadios) modeRadios.forEach(radio => radio.addEventListener('change', handleModeChange));
    if (imageInput) imageInput.addEventListener('change', updateImagePreviews);
    if (resolutionSelect) resolutionSelect.addEventListener('change', handleResolutionChange);
    
    // Add event listeners for image positioning radios
    const positioningRadios = document.querySelectorAll('input[name="image_positioning"]');
    positioningRadios.forEach(radio => {
        radio.addEventListener('change', handleImagePositioningChange);
    });
    
    // Initial calls
    handleModeChange();
    handleResolutionChange();
    handleImagePositioningChange();

    // Make updateImagePreviews available globally for drag-drop.js
    window.updateImagePreviews = updateImagePreviews;

    // --- PROMPT MANAGER LOGIC ---

    async function fetchPrompts() {
        try {
            const response = await fetch('/prompts');
            if (!response.ok) throw new Error('Network response was not ok');
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch prompts:', error);
            return {};
        }
    }

    function renderPrompts(prompts) {
        promptList.innerHTML = '';
        expertiseSelect.innerHTML = '';

        if (Object.keys(prompts).length === 0) {
            promptList.innerHTML = '<p>No prompts found. Add one below!</p>';
        }

        for (const [name, text] of Object.entries(prompts)) {
            // Populate prompt manager list
            const item = document.createElement('div');
            item.className = 'prompt-item';
            item.innerHTML = `
                <div class="prompt-item-content" data-name="${name}" data-text="${text}" title="Click to edit">
                    <strong>${name}</strong>
                    <span>${text}</span>
                </div>
                <div class="prompt-item-actions">
                    <button class="button danger-button delete-prompt-btn" data-name="${name}">Delete</button>
                </div>
            `;
            promptList.appendChild(item);

            // Populate main form select
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            expertiseSelect.appendChild(option);
        }
    }

    async function loadAndRenderPrompts() {
        const prompts = await fetchPrompts();
        renderPrompts(prompts);
    }

    async function handleAddOrUpdatePrompt() {
        const name = newPromptNameInput.value.trim();
        const text = newPromptTextInput.value.trim();
        if (!name || !text) {
            alert('Please provide both a name and text for the prompt.');
            return;
        }

        // Check if prompt exists to decide between add/update
        const prompts = await fetchPrompts();
        const isUpdate = Object.keys(prompts).includes(name);
        const url = isUpdate ? '/prompts/update' : '/prompts/add';

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, text })
            });
            const result = await response.json();
            if (result.success) {
                newPromptNameInput.value = '';
                newPromptTextInput.value = '';
                renderPrompts(result.prompts);
            } else {
                alert('Error saving prompt: ' + result.error);
            }
        } catch (error) {
            console.error('Failed to save prompt:', error);
        }
    }
    
    async function handleDeletePrompt(name) {
       if (!confirm(`Are you sure you want to delete the prompt "${name}"?`)) return;

       try {
            const response = await fetch('/prompts/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const result = await response.json();
            if (result.success) {
                 loadAndRenderPrompts();
            } else {
                alert('Error deleting prompt: ' + result.error);
            }
       } catch (error) {
           console.error('Failed to delete prompt:', error);
       }
    }
    
    // Event delegation for prompt list
    promptList.addEventListener('click', (e) => {
        // Handle delete
        if (e.target.classList.contains('delete-prompt-btn')) {
            const name = e.target.dataset.name;
            handleDeletePrompt(name);
        }
        
        // Handle click to edit
        const content = e.target.closest('.prompt-item-content');
        if (content) {
            newPromptNameInput.value = content.dataset.name;
            newPromptTextInput.value = content.dataset.text;
        }
    });

    if (addPromptBtn) addPromptBtn.addEventListener('click', handleAddOrUpdatePrompt);

    // Initial load for prompts
    loadAndRenderPrompts();

});