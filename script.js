// Main JavaScript file for Learn Python Interactive

// Global variables
let isCodeRunning = false;
let executionHistory = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize syntax highlighting
    if (typeof Prism !== 'undefined') {
        Prism.highlightAll();
    }
    
    // Set up event listeners
    setupEventListeners();
    
    // Load execution history from localStorage
    loadExecutionHistory();
    
    // Initialize any interactive elements
    initializeInteractiveElements();
}

function setupEventListeners() {
    // Code runner button
    const runButtons = document.querySelectorAll('.run-code-btn');
    runButtons.forEach(button => {
        button.addEventListener('click', function() {
            runExerciseCode(this);
        });
    });
    
    // Copy code buttons
    const copyButtons = document.querySelectorAll('.copy-code-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            copyCode(this);
        });
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

function handleKeyboardShortcuts(event) {
    // Ctrl/Cmd + Enter to run code
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        const activeCodeInput = document.activeElement;
        if (activeCodeInput && activeCodeInput.classList.contains('code-input')) {
            const runButton = activeCodeInput.closest('.exercise-block, .mini-editor, .code-runner-container')
                                           ?.querySelector('.run-code-btn');
            if (runButton) {
                event.preventDefault();
                runButton.click();
            }
        }
    }
}

function initializeInteractiveElements() {
    // Auto-resize textareas
    const textareas = document.querySelectorAll('.code-input');
    textareas.forEach(textarea => {
        autoResizeTextarea(textarea);
        textarea.addEventListener('input', function() {
            autoResizeTextarea(this);
        });
    });
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.max(textarea.scrollHeight, 120) + 'px';
}

// Code execution functions
function runCode() {
    const codeInput = document.getElementById('code-input');
    if (!codeInput) return;
    
    const code = codeInput.value.trim();
    if (!code) {
        showNotification('Please enter some Python code to run.', 'warning');
        return;
    }
    
    executeCode(code, document.getElementById('output-content'));
}

function runExerciseCode(button) {
    const container = button.closest('.exercise-block, .mini-editor');
    const codeInput = container.querySelector('.code-input');
    const outputElement = container.querySelector('.output-content');
    
    if (!codeInput || !outputElement) return;
    
    const code = codeInput.value.trim();
    if (!code) {
        showNotification('Please enter some Python code to run.', 'warning');
        return;
    }
    
    executeCode(code, outputElement, button);
}

function runSidebarCode(button) {
    const container = button.closest('.mini-editor');
    const codeInput = container.querySelector('.code-input');
    const outputContainer = container.querySelector('.code-output');
    const outputElement = container.querySelector('.output-content');
    
    if (!codeInput || !outputElement) return;
    
    const code = codeInput.value.trim();
    if (!code) {
        showNotification('Please enter some Python code to run.', 'warning');
        return;
    }
    
    // Show output container
    outputContainer.style.display = 'block';
    
    executeCode(code, outputElement, button);
}

function executeCode(code, outputElement, button = null) {
    if (isCodeRunning) return;
    
    isCodeRunning = true;
    
    // Update button state if provided
    if (button) {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Running...';
        button.disabled = true;
    }
    
    // Show loading in output
    outputElement.textContent = 'Running code...';
    outputElement.parentElement.style.display = 'block';
    
    // Send code to server
    fetch('/run_code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: code })
    })
    .then(response => response.json())
    .then(data => {
        displayCodeOutput(data, outputElement);
        addToExecutionHistory(code, data);
    })
    .catch(error => {
        console.error('Error:', error);
        outputElement.textContent = 'Error: Could not execute code. Please try again.';
        showNotification('Error executing code. Please try again.', 'error');
    })
    .finally(() => {
        isCodeRunning = false;
        
        // Restore button state
        if (button) {
            button.innerHTML = '<i class="fas fa-play me-1"></i>Run Code';
            button.disabled = false;
        }
    });
}

function displayCodeOutput(result, outputElement) {
    outputElement.innerHTML = '';
    
    if (result.success) {
        if (result.output) {
            outputElement.textContent = result.output;
        } else {
            outputElement.innerHTML = '<span class="text-muted">Code executed successfully (no output)</span>';
        }
    } else {
        outputElement.innerHTML = `<span class="text-danger">${escapeHtml(result.error)}</span>`;
    }
    
    // Scroll to output if it's not visible
    outputElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function addToExecutionHistory(code, result) {
    const execution = {
        code: code.substring(0, 100) + (code.length > 100 ? '...' : ''),
        success: result.success,
        timestamp: new Date().toLocaleTimeString(),
        output: result.output || result.error
    };
    
    executionHistory.unshift(execution);
    
    // Keep only last 10 executions
    if (executionHistory.length > 10) {
        executionHistory = executionHistory.slice(0, 10);
    }
    
    // Save to localStorage
    localStorage.setItem('pythonExecutionHistory', JSON.stringify(executionHistory));
    
    // Update history display if element exists
    updateHistoryDisplay();
}

function loadExecutionHistory() {
    try {
        const stored = localStorage.getItem('pythonExecutionHistory');
        if (stored) {
            executionHistory = JSON.parse(stored);
            updateHistoryDisplay();
        }
    } catch (error) {
        console.error('Error loading execution history:', error);
        executionHistory = [];
    }
}

function updateHistoryDisplay() {
    const historyElement = document.getElementById('execution-history');
    if (!historyElement) return;
    
    if (executionHistory.length === 0) {
        historyElement.innerHTML = '<p class="text-muted text-center">No executions yet</p>';
        return;
    }
    
    const historyHTML = executionHistory.map(execution => {
        const statusIcon = execution.success ? 'fa-check-circle text-success' : 'fa-times-circle text-danger';
        const statusText = execution.success ? 'Success' : 'Error';
        
        return `
            <div class="history-item mb-2 p-2 border rounded">
                <div class="d-flex align-items-center justify-content-between mb-1">
                    <small class="text-muted">${execution.timestamp}</small>
                    <i class="fas ${statusIcon}"></i>
                </div>
                <code class="small">${escapeHtml(execution.code)}</code>
            </div>
        `;
    }).join('');
    
    historyElement.innerHTML = historyHTML;
}

// Utility functions
function copyCode(button) {
    const codeBlock = button.closest('.code-block').querySelector('code');
    const text = codeBlock.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
        button.classList.add('btn-success');
        button.classList.remove('btn-outline-light');
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-light');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy code:', err);
        showNotification('Failed to copy code to clipboard', 'error');
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function showToast(message, type = 'success') {
    showNotification(message, type);
}

// Lesson completion functions
function markLessonComplete(lessonId) {
    fetch('/complete_lesson', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ lesson_id: lessonId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Lesson marked as complete! 🎉', 'success');
            
            // Update UI to show completion
            const completionBadges = document.querySelectorAll('.completion-badge');
            completionBadges.forEach(badge => {
                badge.innerHTML = '<i class="fas fa-check-circle text-success"></i>';
                badge.style.display = 'block';
            });
        }
    })
    .catch(error => {
        console.error('Error marking lesson complete:', error);
        showNotification('Error marking lesson complete', 'error');
    });
}

// Animation helpers
function addFadeInAnimation(element) {
    element.classList.add('fade-in');
}

function addSlideUpAnimation(element) {
    element.classList.add('slide-up');
}

// Theme handling (for future dark mode support)
function toggleTheme() {
    // Future implementation for dark mode toggle
    console.log('Theme toggle clicked - feature coming soon!');
}

// Performance optimization
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for global access
window.runCode = runCode;
window.runExerciseCode = runExerciseCode;
window.runSidebarCode = runSidebarCode;
window.copyCode = copyCode;
window.markLessonComplete = markLessonComplete;
window.showToast = showToast;
window.showNotification = showNotification;
