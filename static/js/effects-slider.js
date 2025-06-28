document.addEventListener('DOMContentLoaded', function() {
    // Effect slider configuration
    const effectTypes = [
        { id: 'pan_right', name: 'Pan Right', defaultValue: 20 },
        { id: 'pan_left', name: 'Pan Left', defaultValue: 20 },
        { id: 'pan_up', name: 'Pan Up', defaultValue: 15 },
        { id: 'pan_down', name: 'Pan Down', defaultValue: 15 },
        { id: 'zoom_in', name: 'Zoom In', defaultValue: 15 },
        { id: 'zoom_out', name: 'Zoom Out', defaultValue: 15 }
    ];

    let effectValues = {};

    // Initialize effect values
    effectTypes.forEach(effect => {
        effectValues[effect.id] = effect.defaultValue;
    });

    // Movement speed configuration
    const speedDescriptions = {
        2: { label: 'Very Slow (2%)', hint: 'Extremely subtle movement, barely noticeable' },
        3: { label: 'Very Slow (3%)', hint: 'Very gentle movement, great for calm scenes' },
        4: { label: 'Slow (4%)', hint: 'Gentle movement, suitable for peaceful content' },
        5: { label: 'Slow (5%)', hint: 'Slow movement, good for dramatic effect' },
        6: { label: 'Medium Slow (6%)', hint: 'Moderate slow movement, balanced feel' },
        7: { label: 'Medium (7%)', hint: 'Slightly below normal speed, smooth motion' },
        8: { label: 'Normal (8%)', hint: 'Normal speed provides balanced, smooth movement effects' },
        9: { label: 'Medium Fast (9%)', hint: 'Slightly faster than normal, more dynamic' },
        10: { label: 'Medium Fast (10%)', hint: 'Moderately fast movement, engaging motion' },
        11: { label: 'Fast (11%)', hint: 'Fast movement, good for action scenes' },
        12: { label: 'Fast (12%)', hint: 'Quick movement, creates energy and excitement' },
        13: { label: 'Very Fast (13%)', hint: 'Very dynamic movement, high energy feel' },
        14: { label: 'Very Fast (14%)', hint: 'Rapid movement, intense and dramatic' },
        15: { label: 'Very Fast (15%)', hint: 'Very rapid movement, maximum drama' },
        16: { label: 'Extreme (16%)', hint: 'Extreme movement, very intense effect' },
        17: { label: 'Extreme (17%)', hint: 'Extreme fast movement, highly dramatic' },
        18: { label: 'Extreme (18%)', hint: 'Maximum speed movement, very intense' },
        19: { label: 'Extreme (19%)', hint: 'Ultra-fast movement, extreme drama' },
        20: { label: 'Maximum (20%)', hint: 'Maximum speed, most dramatic movement possible' }
    };

    function createEffectSliders() {
        const container = document.getElementById('effect-sliders-container');
        if (!container) return;

        container.innerHTML = '';

        effectTypes.forEach(effect => {
            const sliderGroup = document.createElement('div');
            sliderGroup.className = 'effect-slider-group';
            
            sliderGroup.innerHTML = `
                <div class="effect-slider-header">
                    <label for="${effect.id}_slider">${effect.name}</label>
                    <span class="effect-value" id="${effect.id}_value">${effectValues[effect.id]}%</span>
                </div>
                <input type="range" 
                       id="${effect.id}_slider" 
                       class="effect-slider" 
                       min="0" 
                       max="100" 
                       value="${effectValues[effect.id]}"
                       data-effect="${effect.id}">
                <input type="hidden" name="effect_${effect.id}" value="${effectValues[effect.id]}">
            `;
            
            container.appendChild(sliderGroup);
        });

        // Add total display with warning
        const totalDisplay = document.createElement('div');
        totalDisplay.className = 'effect-total-display';
        totalDisplay.innerHTML = `
            <div class="total-percentage">
                <strong>Total: <span id="total-percentage">100</span>%</strong>
            </div>
            <div class="total-warning" id="total-warning">
                ⚠️ Total must equal 100% to generate video
            </div>
        `;
        container.appendChild(totalDisplay);

        // Attach events immediately after creating sliders
        attachSliderEvents();
        updateSliderUI();
    }

    function attachSliderEvents() {
        const sliders = document.querySelectorAll('.effect-slider');
        
        sliders.forEach(slider => {
            // Simple event handler that works reliably
            slider.addEventListener('input', function(e) {
                const effectId = this.dataset.effect;
                const newValue = parseInt(this.value);
                
                console.log(`Effect slider changed: ${effectId} = ${newValue}%`);
                
                // Update the value
                effectValues[effectId] = newValue;
                updateSliderUI();
            });

            slider.addEventListener('change', function(e) {
                const effectId = this.dataset.effect;
                const newValue = parseInt(this.value);
                
                // Update the value
                effectValues[effectId] = newValue;
                updateSliderUI();
            });
        });
    }

    function updateSliderUI() {
        effectTypes.forEach(effect => {
            const slider = document.getElementById(`${effect.id}_slider`);
            const valueDisplay = document.getElementById(`${effect.id}_value`);
            const hiddenInput = document.querySelector(`input[name="effect_${effect.id}"]`);
            
            if (slider) slider.value = effectValues[effect.id];
            if (valueDisplay) valueDisplay.textContent = `${effectValues[effect.id]}%`;
            if (hiddenInput) hiddenInput.value = effectValues[effect.id];
        });
        
        // Update total display
        const totalDisplay = document.getElementById('total-percentage');
        const totalWarning = document.getElementById('total-warning');
        const totalContainer = document.querySelector('.effect-total-display');
        const total = Object.values(effectValues).reduce((sum, val) => sum + val, 0);
        
        if (totalDisplay) {
            totalDisplay.textContent = total;
            
            // Update styling based on total
            if (total === 100) {
                totalDisplay.classList.remove('invalid');
                totalDisplay.classList.add('valid');
                if (totalContainer) totalContainer.classList.remove('invalid');
                if (totalWarning) totalWarning.classList.remove('show');
            } else {
                totalDisplay.classList.remove('valid');
                totalDisplay.classList.add('invalid');
                if (totalContainer) totalContainer.classList.add('invalid');
                if (totalWarning) totalWarning.classList.add('show');
            }
        }
        
        // Update form submission button state
        updateSubmitButtonState(total === 100);
    }

    function updateSubmitButtonState(isValid) {
        const submitButton = document.querySelector('button[type="submit"]');
        const movementCheckbox = document.getElementById('enable_movement');
        
        if (submitButton && movementCheckbox && movementCheckbox.checked) {
            if (isValid) {
                submitButton.disabled = false;
                submitButton.style.opacity = '1';
                submitButton.style.cursor = 'pointer';
            } else {
                submitButton.disabled = true;
                submitButton.style.opacity = '0.6';
                submitButton.style.cursor = 'not-allowed';
            }
        }
    }

    function resetToDefaults() {
        effectTypes.forEach(effect => {
            effectValues[effect.id] = effect.defaultValue;
        });
        updateSliderUI();
    }

    function randomizeEffects() {
        // Generate random values that sum to 100
        let remaining = 100;
        const randomValues = {};
        
        effectTypes.forEach((effect, index) => {
            if (index === effectTypes.length - 1) {
                // Last effect gets the remaining value
                randomValues[effect.id] = remaining;
            } else {
                // Random value between 0 and remaining amount
                const maxValue = Math.min(50, remaining); // Cap at 50% for any single effect
                const value = Math.floor(Math.random() * (maxValue + 1));
                randomValues[effect.id] = value;
                remaining -= value;
            }
        });
        
        effectValues = randomValues;
        updateSliderUI();
    }

    function normalizeToHundred() {
        const currentTotal = Object.values(effectValues).reduce((sum, val) => sum + val, 0);
        
        if (currentTotal !== 100) {
            const difference = 100 - currentTotal;
            
            // Find the effect with the highest value to adjust
            const maxEffect = effectTypes.reduce((max, effect) => 
                effectValues[effect.id] > effectValues[max.id] ? effect : max
            );
            
            effectValues[maxEffect.id] = Math.max(0, effectValues[maxEffect.id] + difference);
        }
        
        updateSliderUI();
    }

    // Movement Speed Control
    function initializeMovementSpeedControl() {
        const speedSlider = document.getElementById('movement_speed_slider');
        const speedValue = document.getElementById('movement_speed_value');
        const speedHint = document.getElementById('speed_hint');
        const speedInput = document.getElementById('movement_speed_input');
        
        if (!speedSlider || !speedValue || !speedHint || !speedInput) {
            console.log('Movement speed elements not found');
            return;
        }
        
        function updateSpeedDisplay(value) {
            const speed = parseInt(value);
            const description = speedDescriptions[speed];
            
            if (description) {
                speedValue.textContent = description.label;
                speedHint.textContent = description.hint;
            }
            
            speedInput.value = speed;
            console.log(`Movement speed updated: ${speed}%`);
        }
        
        // Initial display
        updateSpeedDisplay(speedSlider.value);
        
        // Handle slider changes
        speedSlider.addEventListener('input', function() {
            updateSpeedDisplay(this.value);
        });
        
        speedSlider.addEventListener('change', function() {
            updateSpeedDisplay(this.value);
        });
        
        console.log('Movement speed control initialized');
    }

    // Initialize when movement is enabled
    function initializeEffectSliders() {
        const movementCheckbox = document.getElementById('enable_movement');
        const effectSlidersSection = document.getElementById('effect-sliders-section');
        
        if (!movementCheckbox || !effectSlidersSection) return;
        
        function toggleEffectSliders() {
            if (movementCheckbox.checked) {
                effectSlidersSection.style.display = 'block';
                
                // Initialize both effect sliders and movement speed control
                setTimeout(() => {
                    createEffectSliders();
                    initializeMovementSpeedControl();
                    console.log('Effect sliders and movement speed initialized');
                }, 100);
            } else {
                effectSlidersSection.style.display = 'none';
                // Reset submit button state when movement is disabled
                const submitButton = document.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.style.opacity = '1';
                    submitButton.style.cursor = 'pointer';
                }
            }
        }
        
        movementCheckbox.addEventListener('change', toggleEffectSliders);
        toggleEffectSliders(); // Initial call
    }

    // Expose functions globally for button events
    window.resetEffectSliders = resetToDefaults;
    window.randomizeEffects = randomizeEffects;
    window.normalizeEffectSliders = normalizeToHundred;
    
    // Initialize everything
    initializeEffectSliders();
});