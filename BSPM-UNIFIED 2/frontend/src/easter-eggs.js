/**
 * Easter Eggs and Fun Extras
 * Konami Code and Barry Encounter
 */

// Konami Code tracking
let konamiCode = [];
const konamiSequence = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];

// Track click count on Barry head for secret mode
let barryClickCount = 0;
let barryClickTimeout = null;

/**
 * Initialize easter eggs
 */
export function initEasterEggs() {
    // Konami code listener
    document.addEventListener('keydown', handleKonamiInput);

    // Barry head click listener (if it exists)
    const barryHead = document.querySelector('.barry-head');
    if (barryHead) {
        barryHead.addEventListener('click', handleBarryClick);
    }

    // Secret double-click on header for dev mode
    const header = document.querySelector('.gb-header h1');
    if (header) {
        header.addEventListener('dblclick', toggleDevMode);
    }

    console.log('🎮 Easter eggs initialized! Try the Konami code...');
}

/**
 * Handle Konami code input
 */
function handleKonamiInput(e) {
    konamiCode.push(e.key);
    konamiCode = konamiCode.slice(-10);

    if (konamiCode.join(',') === konamiSequence.join(',')) {
        triggerBarryEncounter();
        konamiCode = []; // Reset after trigger
    }
}

/**
 * Trigger a wild Barry encounter
 */
function triggerBarryEncounter() {
    // Create encounter dialog
    const dialog = document.createElement('div');
    dialog.className = 'modal-backdrop';
    dialog.style.cssText = 'display: flex; z-index: 3000;';

    dialog.innerHTML = `
        <div class="modal-content barry-modal" style="animation: battleIntro 0.5s ease-out;">
            <div class="barry-head" style="animation: barryBounce 1s infinite;"></div>
            <h2 style="color: #ff0000;">A wild BARRY appeared!</h2>
            <p>BARRY wants to generate sprites!</p>
            <p style="font-size: 10px; margin-top: 16px;">What will you do?</p>
            <div style="display: flex; gap: 8px; margin-top: 16px;">
                <button class="btn-primary" onclick="this.closest('.modal-backdrop').remove()">GENERATE</button>
                <button class="btn-secondary" onclick="this.closest('.modal-backdrop').remove()">RUN AWAY</button>
            </div>
        </div>
    `;

    document.body.appendChild(dialog);

    // Play sound effect if audio is enabled
    playSound('encounter');

    // Auto-close after 10 seconds
    setTimeout(() => {
        if (dialog.parentElement) {
            dialog.remove();
        }
    }, 10000);
}

/**
 * Handle Barry head clicks for secret mode
 */
function handleBarryClick() {
    barryClickCount++;

    // Reset counter after 2 seconds of no clicks
    clearTimeout(barryClickTimeout);
    barryClickTimeout = setTimeout(() => {
        barryClickCount = 0;
    }, 2000);

    // Trigger secret mode after 7 clicks
    if (barryClickCount >= 7) {
        activateSecretMode();
        barryClickCount = 0;
    }
}

/**
 * Activate secret sprite generation mode
 */
function activateSecretMode() {
    const container = document.querySelector('.gb-container');
    if (!container) return;

    // Apply retro color cycling effect
    container.style.animation = 'colorCycle 5s infinite';

    // Add style for color cycling if not exists
    if (!document.getElementById('secret-mode-styles')) {
        const style = document.createElement('style');
        style.id = 'secret-mode-styles';
        style.textContent = `
            @keyframes colorCycle {
                0% { filter: hue-rotate(0deg); }
                25% { filter: hue-rotate(90deg); }
                50% { filter: hue-rotate(180deg); }
                75% { filter: hue-rotate(270deg); }
                100% { filter: hue-rotate(360deg); }
            }
            @keyframes barryBounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-10px); }
            }
            @keyframes battleIntro {
                0% { transform: scale(0); opacity: 0; }
                60% { transform: scale(1.1); }
                100% { transform: scale(1); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }

    // Show notification
    showNotification('🌈 SECRET MODE ACTIVATED! 🌈', 'success');

    // Reset after 10 seconds
    setTimeout(() => {
        container.style.animation = '';
    }, 10000);
}

/**
 * Toggle developer mode with enhanced logging
 */
function toggleDevMode() {
    const isDevMode = document.body.classList.toggle('dev-mode');

    if (isDevMode) {
        console.log('%c🔧 DEVELOPER MODE ACTIVATED 🔧', 'font-size: 20px; color: #9bbc0f; font-weight: bold;');
        console.log('Enhanced logging enabled');
        console.log('API calls will be logged to console');

        // Add dev mode indicator
        const devIndicator = document.createElement('div');
        devIndicator.id = 'dev-mode-indicator';
        devIndicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: #ff0000;
            color: #fff;
            padding: 4px 8px;
            font-family: 'Press Start 2P', monospace;
            font-size: 8px;
            z-index: 9999;
            border: 2px solid #000;
        `;
        devIndicator.textContent = 'DEV MODE';
        document.body.appendChild(devIndicator);

        showNotification('Developer mode enabled', 'success');
    } else {
        console.log('Developer mode disabled');
        const indicator = document.getElementById('dev-mode-indicator');
        if (indicator) indicator.remove();
        showNotification('Developer mode disabled', 'warning');
    }

    // Store preference
    localStorage.setItem('devMode', isDevMode);
}

/**
 * Show notification toast
 */
function showNotification(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `${type}-message`;
    toast.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 2000; animation: slideInUp 0.3s ease-out;';
    toast.innerHTML = `<p>${message}</p>`;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideInUp 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Play sound effect (placeholder for future audio implementation)
 */
function playSound(soundName) {
    // Placeholder for sound effects
    // Future implementation could use Web Audio API
    if (document.body.classList.contains('dev-mode')) {
        console.log(`🔊 Playing sound: ${soundName}`);
    }
}

/**
 * Check for stored dev mode preference on load
 */
if (localStorage.getItem('devMode') === 'true') {
    document.body.classList.add('dev-mode');
    console.log('%c🔧 Developer mode restored from storage', 'color: #9bbc0f;');
}

// Export for potential external use
export {
    triggerBarryEncounter,
    activateSecretMode,
    toggleDevMode,
    showNotification
};
