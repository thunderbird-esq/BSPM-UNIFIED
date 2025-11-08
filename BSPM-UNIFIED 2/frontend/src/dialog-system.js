/**
 * GBStudio Automation Hub - Dialog System
 * Pokemon-style Dialog Manager
 *
 * Features:
 * - Show/Hide dialogs
 * - Confirm dialogs
 * - Alert dialogs
 * - Toast notifications
 * - Custom dialogs with choices
 * - Typewriter text effect
 */

class DialogSystem {
    constructor() {
        this.activeDialogs = new Map();
        this.dialogCount = 0;
        this.defaultOptions = {
            type: 'info', // info, warning, error, success
            showOverlay: true,
            closeOnOverlayClick: true,
            showCloseButton: true,
            typewriterEffect: false,
            typewriterSpeed: 50, // ms per character
            position: 'center' // center, bottom, top
        };
    }

    /**
     * Show a basic dialog
     * @param {string} message - The message to display
     * @param {Object} options - Dialog options
     * @returns {Promise} - Resolves when dialog is closed
     */
    show(message, options = {}) {
        return new Promise((resolve) => {
            const opts = { ...this.defaultOptions, ...options };
            const dialogId = `dialog-${++this.dialogCount}`;

            // Create overlay
            const overlay = this._createOverlay(opts, dialogId);

            // Create dialog
            const dialog = this._createDialog(message, opts, dialogId);

            // Add close button if needed
            if (opts.showCloseButton) {
                const closeBtn = this._createButton('Close', 'primary', () => {
                    this.hide(dialogId);
                    resolve('closed');
                });
                const buttonContainer = document.createElement('div');
                buttonContainer.className = 'gb-dialog-buttons';
                buttonContainer.appendChild(closeBtn);
                dialog.appendChild(buttonContainer);
            }

            // Append to DOM
            if (opts.showOverlay) {
                overlay.appendChild(dialog);
                document.body.appendChild(overlay);
            } else {
                document.body.appendChild(dialog);
            }

            // Store reference
            this.activeDialogs.set(dialogId, { overlay, dialog, resolve });

            // Apply typewriter effect if enabled
            if (opts.typewriterEffect) {
                this._applyTypewriterEffect(dialog.querySelector('.gb-dialog-text'), opts.typewriterSpeed);
            }
        });
    }

    /**
     * Show a confirmation dialog
     * @param {string} message - The message to display
     * @param {Object} options - Dialog options
     * @returns {Promise<boolean>} - Resolves with true/false based on user choice
     */
    confirm(message, options = {}) {
        return new Promise((resolve) => {
            const opts = { ...this.defaultOptions, ...options };
            const dialogId = `confirm-${++this.dialogCount}`;

            // Create overlay
            const overlay = this._createOverlay(opts, dialogId);

            // Create dialog
            const dialog = this._createDialog(message, opts, dialogId);
            dialog.classList.add('gb-confirm-dialog');

            // Create buttons
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'gb-dialog-buttons';

            const confirmBtn = this._createButton(opts.confirmText || 'Yes', 'primary', () => {
                this.hide(dialogId);
                resolve(true);
            });

            const cancelBtn = this._createButton(opts.cancelText || 'No', 'cancel', () => {
                this.hide(dialogId);
                resolve(false);
            });

            buttonContainer.appendChild(cancelBtn);
            buttonContainer.appendChild(confirmBtn);
            dialog.appendChild(buttonContainer);

            // Append to DOM
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);

            // Store reference
            this.activeDialogs.set(dialogId, { overlay, dialog, resolve });
        });
    }

    /**
     * Show an alert dialog
     * @param {string} message - The message to display
     * @param {string} type - Alert type (info, warning, error, success)
     * @returns {Promise} - Resolves when dialog is closed
     */
    alert(message, type = 'info') {
        return this.show(message, {
            type,
            showCloseButton: true,
            closeOnOverlayClick: false
        });
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Toast type (info, warning, error, success)
     * @param {number} duration - Duration in ms (default 3000)
     */
    toast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `gb-toast ${type}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, duration);
    }

    /**
     * Show a dialog with custom choices
     * @param {string} message - The message to display
     * @param {Array} choices - Array of choice objects {text, value}
     * @param {Object} options - Dialog options
     * @returns {Promise} - Resolves with selected choice value
     */
    showChoices(message, choices, options = {}) {
        return new Promise((resolve) => {
            const opts = { ...this.defaultOptions, ...options };
            const dialogId = `choice-${++this.dialogCount}`;

            // Create overlay
            const overlay = this._createOverlay(opts, dialogId);

            // Create dialog
            const dialog = this._createDialog(message, opts, dialogId);

            // Create choices container
            const choicesContainer = document.createElement('div');
            choicesContainer.className = 'gb-dialog-choices';

            choices.forEach((choice, index) => {
                const choiceBtn = document.createElement('div');
                choiceBtn.className = 'gb-dialog-choice';
                choiceBtn.textContent = choice.text;
                if (index === 0) {
                    choiceBtn.classList.add('selected');
                }

                choiceBtn.addEventListener('click', () => {
                    this.hide(dialogId);
                    resolve(choice.value);
                });

                choiceBtn.addEventListener('mouseenter', () => {
                    // Remove selected class from all choices
                    choicesContainer.querySelectorAll('.gb-dialog-choice').forEach(c => {
                        c.classList.remove('selected');
                    });
                    choiceBtn.classList.add('selected');
                });

                choicesContainer.appendChild(choiceBtn);
            });

            dialog.appendChild(choicesContainer);

            // Append to DOM
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);

            // Store reference
            this.activeDialogs.set(dialogId, { overlay, dialog, resolve });

            // Keyboard navigation
            let selectedIndex = 0;
            const handleKeyPress = (e) => {
                const choiceElements = choicesContainer.querySelectorAll('.gb-dialog-choice');

                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    selectedIndex = (selectedIndex + 1) % choices.length;
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    selectedIndex = (selectedIndex - 1 + choices.length) % choices.length;
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    this.hide(dialogId);
                    resolve(choices[selectedIndex].value);
                    document.removeEventListener('keydown', handleKeyPress);
                    return;
                }

                // Update selected class
                choiceElements.forEach((el, idx) => {
                    el.classList.toggle('selected', idx === selectedIndex);
                });
            };

            document.addEventListener('keydown', handleKeyPress);
        });
    }

    /**
     * Show an input dialog
     * @param {string} message - The message to display
     * @param {Object} options - Dialog options
     * @returns {Promise<string|null>} - Resolves with input value or null if cancelled
     */
    prompt(message, options = {}) {
        return new Promise((resolve) => {
            const opts = { ...this.defaultOptions, ...options };
            const dialogId = `prompt-${++this.dialogCount}`;

            // Create overlay
            const overlay = this._createOverlay(opts, dialogId);

            // Create dialog
            const dialog = this._createDialog(message, opts, dialogId);

            // Create input field
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'gb-dialog-input';
            input.placeholder = opts.placeholder || 'Enter text...';
            input.value = opts.defaultValue || '';

            const content = dialog.querySelector('.gb-dialog-content');
            content.appendChild(input);

            // Create buttons
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'gb-dialog-buttons';

            const confirmBtn = this._createButton('OK', 'primary', () => {
                this.hide(dialogId);
                resolve(input.value);
            });

            const cancelBtn = this._createButton('Cancel', 'cancel', () => {
                this.hide(dialogId);
                resolve(null);
            });

            buttonContainer.appendChild(cancelBtn);
            buttonContainer.appendChild(confirmBtn);
            dialog.appendChild(buttonContainer);

            // Append to DOM
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);

            // Focus input
            setTimeout(() => input.focus(), 100);

            // Enter key to confirm
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.hide(dialogId);
                    resolve(input.value);
                }
            });

            // Store reference
            this.activeDialogs.set(dialogId, { overlay, dialog, resolve });
        });
    }

    /**
     * Hide a dialog
     * @param {string} dialogId - The ID of the dialog to hide
     */
    hide(dialogId) {
        const dialogData = this.activeDialogs.get(dialogId);
        if (!dialogData) return;

        const { overlay, dialog } = dialogData;

        // Add fade-out animation
        if (overlay) {
            overlay.style.animation = 'overlayFadeIn 0.2s ease reverse';
        }
        dialog.style.animation = 'dialogSlideIn 0.2s ease reverse';

        setTimeout(() => {
            if (overlay) {
                overlay.remove();
            } else {
                dialog.remove();
            }
            this.activeDialogs.delete(dialogId);
        }, 200);
    }

    /**
     * Hide all active dialogs
     */
    hideAll() {
        this.activeDialogs.forEach((_, dialogId) => {
            this.hide(dialogId);
        });
    }

    /**
     * Create overlay element
     * @private
     */
    _createOverlay(options, dialogId) {
        const overlay = document.createElement('div');
        overlay.className = 'gb-dialog-overlay';
        overlay.dataset.dialogId = dialogId;

        if (options.closeOnOverlayClick) {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    this.hide(dialogId);
                }
            });
        }

        return overlay;
    }

    /**
     * Create dialog element
     * @private
     */
    _createDialog(message, options, dialogId) {
        const dialog = document.createElement('div');
        dialog.className = `gb-dialog ${options.type}`;
        if (options.position === 'bottom') {
            dialog.classList.add('gb-dialog-bottom');
        }
        dialog.dataset.dialogId = dialogId;

        // Add header if title is provided
        if (options.title) {
            const header = document.createElement('div');
            header.className = 'gb-dialog-header';

            if (options.avatar) {
                const avatar = document.createElement('img');
                avatar.src = options.avatar;
                avatar.className = 'gb-dialog-avatar';
                header.appendChild(avatar);
            }

            const title = document.createElement('span');
            title.textContent = options.title;
            header.appendChild(title);

            dialog.appendChild(header);
        }

        // Add content
        const content = document.createElement('div');
        content.className = 'gb-dialog-content';

        const text = document.createElement('div');
        text.className = 'gb-dialog-text';
        text.textContent = message;

        content.appendChild(text);
        dialog.appendChild(content);

        // Add arrow if needed
        if (options.showArrow) {
            const arrow = document.createElement('div');
            arrow.className = 'gb-dialog-arrow';
            dialog.appendChild(arrow);
        }

        return dialog;
    }

    /**
     * Create button element
     * @private
     */
    _createButton(text, className, onClick) {
        const button = document.createElement('button');
        button.className = `gb-dialog-button ${className}`;
        button.textContent = text;
        button.addEventListener('click', onClick);
        return button;
    }

    /**
     * Apply typewriter effect to text
     * @private
     */
    _applyTypewriterEffect(element, speed) {
        const text = element.textContent;
        element.textContent = '';
        let index = 0;

        const interval = setInterval(() => {
            if (index < text.length) {
                element.textContent += text[index];
                index++;
            } else {
                clearInterval(interval);
            }
        }, speed);
    }
}

// Create global instance
const dialogSystem = new DialogSystem();

// Export for ES6 modules
export default dialogSystem;

// Also attach to window for non-module scripts
if (typeof window !== 'undefined') {
    window.DialogSystem = DialogSystem;
    window.dialogSystem = dialogSystem;
}

/**
 * Convenience functions
 */
export const showDialog = (message, options) => dialogSystem.show(message, options);
export const confirmDialog = (message, options) => dialogSystem.confirm(message, options);
export const alertDialog = (message, type) => dialogSystem.alert(message, type);
export const toastNotification = (message, type, duration) => dialogSystem.toast(message, type, duration);
export const promptDialog = (message, options) => dialogSystem.prompt(message, options);
export const hideDialog = (dialogId) => dialogSystem.hide(dialogId);
export const hideAllDialogs = () => dialogSystem.hideAll();
