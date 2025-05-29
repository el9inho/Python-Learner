// Code runner specific functionality for Learn Python Interactive

// Code execution management
class CodeRunner {
    constructor() {
        this.isRunning = false;
        this.executionQueue = [];
        this.maxExecutionTime = 10000; // 10 seconds timeout
    }

    async executeCode(code, outputElement, button = null) {
        if (this.isRunning) {
            this.showMessage(outputElement, 'Another code execution is in progress...', 'warning');
            return;
        }

        this.isRunning = true;
        this.updateButtonState(button, true);
        
        try {
            const result = await this.sendCodeToServer(code);
            this.displayResult(result, outputElement);
            this.addToHistory(code, result);
        } catch (error) {
            this.handleExecutionError(error, outputElement);
        } finally {
            this.isRunning = false;
            this.updateButtonState(button, false);
        }
    }

    async sendCodeToServer(code) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.maxExecutionTime);

        try {
            const response = await fetch('/run_code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ code: code }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }

    displayResult(result, outputElement) {
        // Clear previous content
        outputElement.innerHTML = '';
        
        // Show output container if hidden
        const outputContainer = outputElement.closest('.code-output');
        if (outputContainer) {
            outputContainer.style.display = 'block';
        }

        if (result.success) {
            if (result.output && result.output.trim()) {
                outputElement.textContent = result.output;
                outputElement.className = 'output-content';
            } else {
                this.showMessage(outputElement, 'Code executed successfully (no output)', 'success');
            }
        } else {
            this.showMessage(outputElement, result.error || 'Unknown error occurred', 'error');
        }

        // Scroll to output
        this.scrollToElement(outputElement);
    }

    showMessage(outputElement, message, type = 'info') {
        const iconMap = {
            success: 'fa-check-circle text-success',
            warning: 'fa-exclamation-triangle text-warning',
            error: 'fa-times-circle text-danger',
            info: 'fa-info-circle text-info'
        };

        const icon = iconMap[type] || iconMap.info;
        
        outputElement.innerHTML = `
            <div class="execution-message text-center py-3">
                <i class="fas ${icon} fa-2x mb-2"></i>
                <p class="mb-0">${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    updateButtonState(button, isRunning) {
        if (!button) return;

        if (isRunning) {
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Running...';
            button.disabled = true;
            button.classList.add('loading');
        } else {
            button.innerHTML = '<i class="fas fa-play me-1"></i>Run Code';
            button.disabled = false;
            button.classList.remove('loading');
        }
    }

    handleExecutionError(error, outputElement) {
        console.error('Code execution error:', error);
        
        let errorMessage = 'Failed to execute code';
        
        if (error.name === 'AbortError') {
            errorMessage = 'Code execution timed out (10 second limit)';
        } else if (error.message) {
            errorMessage = error.message;
        }

        this.showMessage(outputElement, errorMessage, 'error');
    }

    addToHistory(code, result) {
        const historyEntry = {
            id: Date.now(),
            code: code.substring(0, 150) + (code.length > 150 ? '...' : ''),
            success: result.success,
            timestamp: new Date().toISOString(),
            output: result.output || result.error || ''
        };

        let history = this.getExecutionHistory();
        history.unshift(historyEntry);
        
        // Keep only the last 20 executions
        if (history.length > 20) {
            history = history.slice(0, 20);
        }

        this.saveExecutionHistory(history);
        this.updateHistoryDisplay();
    }

    getExecutionHistory() {
        try {
            const stored = localStorage.getItem('codeExecutionHistory');
            return stored ? JSON.parse(stored) : [];
        } catch (error) {
            console.error('Error loading execution history:', error);
            return [];
        }
    }

    saveExecutionHistory(history) {
        try {
            localStorage.setItem('codeExecutionHistory', JSON.stringify(history));
        } catch (error) {
            console.error('Error saving execution history:', error);
        }
    }

    updateHistoryDisplay() {
        const historyElement = document.getElementById('execution-history');
        if (!historyElement) return;

        const history = this.getExecutionHistory();
        
        if (history.length === 0) {
            historyElement.innerHTML = '<p class="text-muted text-center small">No executions yet</p>';
            return;
        }

        const historyHTML = history.slice(0, 5).map(entry => {
            const statusIcon = entry.success ? 'fa-check text-success' : 'fa-times text-danger';
            const timestamp = new Date(entry.timestamp).toLocaleTimeString();
            
            return `
                <div class="history-entry mb-2 p-2 border rounded-2 bg-light">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <small class="text-muted">${timestamp}</small>
                        <i class="fas ${statusIcon}"></i>
                    </div>
                    <code class="small d-block text-truncate" title="${this.escapeHtml(entry.code)}">
                        ${this.escapeHtml(entry.code)}
                    </code>
                </div>
            `;
        }).join('');

        historyElement.innerHTML = historyHTML;
    }

    clearHistory() {
        localStorage.removeItem('codeExecutionHistory');
        this.updateHistoryDisplay();
        showNotification('Execution history cleared', 'info');
    }

    scrollToElement(element) {
        element.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'nearest',
            inline: 'nearest'
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Code editor enhancements
class CodeEditor {
    constructor(textareaElement) {
        this.textarea = textareaElement;
        this.setupEditor();
    }

    setupEditor() {
        // Add line numbers (basic implementation)
        this.addLineNumbers();
        
        // Setup keyboard shortcuts
        this.setupKeyboardShortcuts();
        
        // Auto-indentation
        this.setupAutoIndentation();
        
        // Auto-resize
        this.setupAutoResize();
    }

    addLineNumbers() {
        // Simple line numbers - could be enhanced with a proper editor
        this.textarea.addEventListener('input', () => {
            this.updateLineNumbers();
        });
        
        this.textarea.addEventListener('scroll', () => {
            this.syncLineNumberScroll();
        });
    }

    updateLineNumbers() {
        const lines = this.textarea.value.split('\n').length;
        // Implementation would depend on HTML structure
    }

    setupKeyboardShortcuts() {
        this.textarea.addEventListener('keydown', (e) => {
            // Tab for indentation
            if (e.key === 'Tab') {
                e.preventDefault();
                this.insertAtCursor('    '); // 4 spaces
            }
            
            // Ctrl/Cmd + / for comments
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                this.toggleComment();
            }
            
            // Ctrl/Cmd + D for duplicate line
            if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
                e.preventDefault();
                this.duplicateLine();
            }
        });
    }

    setupAutoIndentation() {
        this.textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                setTimeout(() => {
                    this.autoIndent();
                }, 0);
            }
        });
    }

    setupAutoResize() {
        this.textarea.addEventListener('input', () => {
            this.autoResize();
        });
        
        // Initial resize
        this.autoResize();
    }

    insertAtCursor(text) {
        const start = this.textarea.selectionStart;
        const end = this.textarea.selectionEnd;
        const value = this.textarea.value;
        
        this.textarea.value = value.substring(0, start) + text + value.substring(end);
        this.textarea.selectionStart = this.textarea.selectionEnd = start + text.length;
        this.textarea.focus();
    }

    toggleComment() {
        const start = this.textarea.selectionStart;
        const end = this.textarea.selectionEnd;
        const value = this.textarea.value;
        
        // Get current line
        const beforeCursor = value.substring(0, start);
        const lineStart = beforeCursor.lastIndexOf('\n') + 1;
        const afterCursor = value.substring(end);
        const lineEnd = afterCursor.indexOf('\n');
        const lineEndPos = lineEnd === -1 ? value.length : end + lineEnd;
        
        const line = value.substring(lineStart, lineEndPos);
        
        let newLine;
        if (line.trimStart().startsWith('#')) {
            // Remove comment
            newLine = line.replace(/^(\s*)#\s?/, '$1');
        } else {
            // Add comment
            const indent = line.match(/^\s*/)[0];
            newLine = indent + '# ' + line.trimStart();
        }
        
        this.textarea.value = value.substring(0, lineStart) + newLine + value.substring(lineEndPos);
        this.textarea.focus();
    }

    duplicateLine() {
        const start = this.textarea.selectionStart;
        const value = this.textarea.value;
        
        const beforeCursor = value.substring(0, start);
        const lineStart = beforeCursor.lastIndexOf('\n') + 1;
        const afterCursor = value.substring(start);
        const lineEnd = afterCursor.indexOf('\n');
        const lineEndPos = lineEnd === -1 ? value.length : start + lineEnd;
        
        const line = value.substring(lineStart, lineEndPos);
        const newValue = value.substring(0, lineEndPos) + '\n' + line + value.substring(lineEndPos);
        
        this.textarea.value = newValue;
        this.textarea.selectionStart = this.textarea.selectionEnd = lineEndPos + 1 + line.length;
        this.textarea.focus();
    }

    autoIndent() {
        const start = this.textarea.selectionStart;
        const value = this.textarea.value;
        
        // Get previous line
        const beforeCursor = value.substring(0, start - 1);
        const lastNewline = beforeCursor.lastIndexOf('\n');
        const previousLine = beforeCursor.substring(lastNewline + 1);
        
        // Get indentation of previous line
        const indent = previousLine.match(/^\s*/)[0];
        
        // Add extra indentation for certain keywords
        const extraIndentKeywords = ['if', 'else', 'elif', 'for', 'while', 'def', 'class', 'try', 'except', 'finally', 'with'];
        const shouldIndentMore = extraIndentKeywords.some(keyword => 
            previousLine.trim().startsWith(keyword) && previousLine.trim().endsWith(':')
        );
        
        const newIndent = shouldIndentMore ? indent + '    ' : indent;
        this.insertAtCursor(newIndent);
    }

    autoResize() {
        this.textarea.style.height = 'auto';
        this.textarea.style.height = Math.max(this.textarea.scrollHeight, 120) + 'px';
    }
}

// Global code runner instance
const codeRunner = new CodeRunner();

// Enhanced global functions
window.runCode = function() {
    const codeInput = document.getElementById('code-input');
    if (!codeInput) return;
    
    const code = codeInput.value.trim();
    if (!code) {
        showNotification('Please enter some Python code to run.', 'warning');
        return;
    }
    
    const outputElement = document.getElementById('output-content');
    const runButton = document.getElementById('run-code-btn');
    
    codeRunner.executeCode(code, outputElement, runButton);
};

window.runExerciseCode = function(button) {
    const container = button.closest('.exercise-block, .mini-editor');
    const codeInput = container.querySelector('.code-input');
    const outputElement = container.querySelector('.output-content');
    
    if (!codeInput || !outputElement) return;
    
    const code = codeInput.value.trim();
    if (!code) {
        showNotification('Please enter some Python code to run.', 'warning');
        return;
    }
    
    codeRunner.executeCode(code, outputElement, button);
};

window.runSidebarCode = function(button) {
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
    
    codeRunner.executeCode(code, outputElement, button);
};

window.clearOutput = function() {
    const outputElement = document.getElementById('output-content');
    if (outputElement) {
        outputElement.innerHTML = `
            <div class="output-placeholder">
                <i class="fas fa-play-circle fa-2x text-muted mb-2"></i>
                <p class="text-muted">Click "Run Code" to see your output here</p>
            </div>
        `;
    }
};

window.clearExecutionHistory = function() {
    codeRunner.clearHistory();
};

// Initialize code editors when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize code runners
    codeRunner.updateHistoryDisplay();
    
    // Enhance all code input textareas
    const codeInputs = document.querySelectorAll('.code-input');
    codeInputs.forEach(textarea => {
        new CodeEditor(textarea);
    });
    
    // Setup syntax highlighting refresh on input
    codeInputs.forEach(textarea => {
        textarea.addEventListener('input', debounce(() => {
            if (typeof Prism !== 'undefined') {
                Prism.highlightAll();
            }
        }, 500));
    });
});

// Utility function for debouncing
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
