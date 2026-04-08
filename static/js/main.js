/**
 * CodeLens-C — Frontend Logic
 * Handles editor initialization, file upload, analysis requests, and result rendering.
 */

// ══════════════════════════════════════
//  CodeMirror Editor Setup
// ══════════════════════════════════════

const editor = CodeMirror.fromTextArea(document.getElementById('code-editor'), {
    mode: 'text/x-csrc',
    theme: 'material-darker',
    lineNumbers: true,
    matchBrackets: true,
    autoCloseBrackets: true,
    styleActiveLine: true,
    tabSize: 4,
    indentUnit: 4,
    indentWithTabs: false,
    lineWrapping: false,
    placeholder: '// Paste your C/C++ code here or upload a file...',
});

// Set initial sample code
const SAMPLE_CODE = `#include <stdio.h>
#include <stdlib.h>

// Global variable
int globalVar = 100;

/* Function to calculate factorial */
int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

// Function with error examples
float divide(int a, int b) {
    if (b == 0) {
        printf("Error: division by zero\\n");
        return 0;
    }
    return a / b;
}

int main() {
    int x = 10;
    int y = 20;
    int result;

    // Valid operations
    result = x + y;
    printf("Sum: %d\\n", result);

    // Function call
    int fact = factorial(5);
    printf("Factorial of 5: %d\\n", fact);

    // Type examples
    float pi = 3.14;
    char grade = 'A';

    // Loop example
    for (int i = 0; i < 5; i++) {
        printf("i = %d\\n", i);
    }

    // While loop
    int count = 0;
    while (count < 3) {
        count++;
    }

    return 0;
}
`;

editor.setValue(SAMPLE_CODE);

// ══════════════════════════════════════
//  DOM Element References
// ══════════════════════════════════════

const btnAnalyze    = document.getElementById('btn-analyze');
const btnSample     = document.getElementById('btn-sample');
const fileInput     = document.getElementById('file-input');
const fileName      = document.getElementById('file-name');
const loadingOverlay= document.getElementById('loading-overlay');

const errorsList    = document.getElementById('errors-list');
const tokensList    = document.getElementById('tokens-list');
const symbolsTbody  = document.getElementById('symbols-tbody');
const preprocessedCode = document.getElementById('preprocessed-code');

const errorsPlaceholder   = document.getElementById('errors-placeholder');
const tokensPlaceholder   = document.getElementById('tokens-placeholder');
const symbolsPlaceholder  = document.getElementById('symbols-placeholder');
const preprocessPlaceholder = document.getElementById('preprocess-placeholder');
const symbolsTableWrapper = document.getElementById('symbols-table-wrapper');

const errorCountBadge  = document.getElementById('error-count');
const tokenCountBadge  = document.getElementById('token-count');
const symbolCountBadge = document.getElementById('symbol-count');
const statsBadges      = document.getElementById('stats-badges');

// Track error markers
let errorMarkers = [];

// ══════════════════════════════════════
//  Tab Switching
// ══════════════════════════════════════

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Deactivate all tabs
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        // Activate clicked
        tab.classList.add('active');
        const pane = document.getElementById(tab.dataset.tab);
        if (pane) pane.classList.add('active');
    });
});

// ══════════════════════════════════════
//  File Upload
// ══════════════════════════════════════

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) loadFile(file);
});

function loadFile(file) {
    if (!file.name.match(/\.(c|cpp|h|hpp)$/)) {
        alert('Please upload a .c, .cpp, .h, or .hpp file.');
        return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
        editor.setValue(e.target.result);
        fileName.textContent = file.name;
    };
    reader.readAsText(file);
}

// Drag and drop
const editorPanel = document.getElementById('editor-panel');

editorPanel.addEventListener('dragover', (e) => {
    e.preventDefault();
    editorPanel.classList.add('drag-over');
});

editorPanel.addEventListener('dragleave', () => {
    editorPanel.classList.remove('drag-over');
});

editorPanel.addEventListener('drop', (e) => {
    e.preventDefault();
    editorPanel.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) loadFile(file);
});

// ══════════════════════════════════════
//  Sample Code Button
// ══════════════════════════════════════

btnSample.addEventListener('click', () => {
    editor.setValue(SAMPLE_CODE);
    fileName.textContent = 'sample.c';
    clearResults();
});

// ══════════════════════════════════════
//  Analyze Button
// ══════════════════════════════════════

btnAnalyze.addEventListener('click', analyzeCode);

// Ctrl+Enter shortcut
editor.setOption('extraKeys', {
    'Ctrl-Enter': analyzeCode,
});

async function analyzeCode() {
    const code = editor.getValue().trim();
    if (!code) {
        alert('Please enter some C/C++ code to analyze.');
        return;
    }

    // Show loading
    loadingOverlay.classList.remove('hidden');
    clearResults();

    try {
        const formData = new FormData();
        formData.append('code', code);

        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
            alert(data.error || 'Analysis failed.');
            return;
        }

        renderResults(data);
    } catch (err) {
        console.error('Analysis error:', err);
        alert('Could not connect to the server. Make sure Flask is running.');
    } finally {
        loadingOverlay.classList.add('hidden');
    }
}

// ══════════════════════════════════════
//  Clear Results
// ══════════════════════════════════════

function clearResults() {
    errorsList.innerHTML = '';
    tokensList.innerHTML = '';
    symbolsTbody.innerHTML = '';
    preprocessedCode.textContent = '';
    preprocessedCode.style.display = 'none';
    symbolsTableWrapper.style.display = 'none';
    statsBadges.innerHTML = '';

    errorsPlaceholder.classList.remove('hidden');
    tokensPlaceholder.classList.remove('hidden');
    symbolsPlaceholder.classList.remove('hidden');
    preprocessPlaceholder.classList.remove('hidden');

    errorCountBadge.textContent = '0';
    tokenCountBadge.textContent = '0';
    symbolCountBadge.textContent = '0';

    // Clear error markers from editor
    errorMarkers.forEach(m => m.clear());
    errorMarkers = [];
    editor.eachLine(line => {
        editor.removeLineClass(line, 'background');
    });
}

// ══════════════════════════════════════
//  Render Results
// ══════════════════════════════════════

function renderResults(data) {
    renderErrors(data.errors || []);
    renderTokens(data.tokens || []);
    renderSymbolTable(data.symbol_table || []);
    renderPreprocessed(data.preprocessed_code || '');
    renderStats(data.stats || {});
    highlightErrorLines(data.errors || []);
}

// ── Errors ──

function renderErrors(errors) {
    const errorsOnly = errors.filter(e => e.type !== 'info');
    errorsPlaceholder.classList.add('hidden');

    if (errorsOnly.length === 0) {
        errorsList.innerHTML = `
            <div class="success-msg">
                <svg width="48" height="48" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/>
                </svg>
                <h3>No Errors Found!</h3>
                <p>Your code passed all checks successfully.</p>
            </div>`;
        errorCountBadge.textContent = '0';
        return;
    }

    errorCountBadge.textContent = errorsOnly.length;

    errorsOnly.forEach((err, i) => {
        const card = document.createElement('div');
        card.className = `error-card ${err.type}-type`;
        card.style.animationDelay = `${i * 40}ms`;

        const icon = err.type === 'error' ? '✕' : err.type === 'warning' ? '!' : 'i';
        const lineText = err.line ? `Line ${err.line}` : 'EOF';

        card.innerHTML = `
            <div class="error-icon">${icon}</div>
            <div class="error-content">
                <div class="error-header">
                    <span class="error-phase">${err.phase}</span>
                    <span class="error-line">${lineText}</span>
                </div>
                <div class="error-message">${escapeHtml(err.message)}</div>
                ${err.suggestion ? `<div class="error-suggestion">💡 ${escapeHtml(err.suggestion)}</div>` : ''}
            </div>`;

        // Click to jump to line
        if (err.line) {
            card.addEventListener('click', () => {
                const lineNum = err.line - 1;
                editor.setCursor(lineNum, 0);
                editor.scrollIntoView({ line: lineNum, ch: 0 }, 200);
                editor.focus();
            });
        }

        errorsList.appendChild(card);
    });
}

// ── Tokens ──

const TOKEN_CATEGORIES = {
    'INT': 'keyword', 'FLOAT': 'keyword', 'DOUBLE': 'keyword', 'CHAR': 'keyword',
    'VOID': 'keyword', 'IF': 'keyword', 'ELSE': 'keyword', 'WHILE': 'keyword',
    'FOR': 'keyword', 'DO': 'keyword', 'RETURN': 'keyword', 'BREAK': 'keyword',
    'CONTINUE': 'keyword', 'SWITCH': 'keyword', 'CASE': 'keyword', 'DEFAULT': 'keyword',
    'STRUCT': 'keyword', 'TYPEDEF': 'keyword', 'ENUM': 'keyword', 'SIZEOF': 'keyword',
    'CONST': 'keyword', 'LONG': 'keyword', 'SHORT': 'keyword', 'UNSIGNED': 'keyword',
    'SIGNED': 'keyword', 'TRUE': 'keyword', 'FALSE': 'keyword', 'NULL_KW': 'keyword',

    'ID': 'identifier',

    'NUMBER_INT': 'number', 'NUMBER_FLOAT': 'number',

    'STRING_LITERAL': 'string', 'CHAR_LITERAL': 'string',

    'PLUS': 'operator', 'MINUS': 'operator', 'TIMES': 'operator', 'DIVIDE': 'operator',
    'MODULO': 'operator', 'EQUALS': 'operator', 'EQ': 'operator', 'NEQ': 'operator',
    'LT': 'operator', 'GT': 'operator', 'LTE': 'operator', 'GTE': 'operator',
    'AND': 'operator', 'OR': 'operator', 'NOT': 'operator',
    'BIT_AND': 'operator', 'BIT_OR': 'operator', 'BIT_XOR': 'operator', 'BIT_NOT': 'operator',
    'LSHIFT': 'operator', 'RSHIFT': 'operator',
    'INCREMENT': 'operator', 'DECREMENT': 'operator',
    'PLUS_ASSIGN': 'operator', 'MINUS_ASSIGN': 'operator',
    'TIMES_ASSIGN': 'operator', 'DIVIDE_ASSIGN': 'operator',
    'MODULO_ASSIGN': 'operator', 'ARROW': 'operator',
    'QUESTION': 'operator', 'COLON': 'operator',

    'SEMICOLON': 'delimiter', 'COMMA': 'delimiter', 'DOT': 'delimiter',
    'LPAREN': 'delimiter', 'RPAREN': 'delimiter',
    'LBRACE': 'delimiter', 'RBRACE': 'delimiter',
    'LBRACKET': 'delimiter', 'RBRACKET': 'delimiter',
};

function renderTokens(tokens) {
    if (tokens.length === 0) return;

    tokensPlaceholder.classList.add('hidden');
    tokenCountBadge.textContent = tokens.length;

    tokens.forEach((tok, i) => {
        const category = TOKEN_CATEGORIES[tok.type] || 'delimiter';
        const chip = document.createElement('span');
        chip.className = `token-chip token-${category}`;
        chip.style.animationDelay = `${Math.min(i * 8, 500)}ms`;
        chip.title = `${tok.type} at line ${tok.line}`;
        chip.innerHTML = `
            <span class="token-type-label">${category}</span>
            <span class="token-value">${escapeHtml(tok.value)}</span>
            <span class="token-line-num">:${tok.line}</span>`;
        tokensList.appendChild(chip);
    });
}

// ── Symbol Table ──

function renderSymbolTable(symbols) {
    if (symbols.length === 0) return;

    symbolsPlaceholder.classList.add('hidden');
    symbolsTableWrapper.style.display = 'block';
    symbolCountBadge.textContent = symbols.length;

    symbols.forEach((sym, i) => {
        const row = document.createElement('tr');
        row.style.animationDelay = `${i * 30}ms`;
        row.innerHTML = `
            <td>${escapeHtml(sym.name)}</td>
            <td>${sym.kind === 'function' ? (sym.return_type || 'void') : escapeHtml(sym.type)}</td>
            <td><span class="kind-badge kind-${sym.kind}">${sym.kind}</span></td>
            <td>${escapeHtml(sym.scope)}</td>
            <td>${sym.line}</td>`;
        symbolsTbody.appendChild(row);
    });
}

// ── Preprocessed Code ──

function renderPreprocessed(code) {
    if (!code) return;
    preprocessPlaceholder.classList.add('hidden');
    preprocessedCode.style.display = 'block';
    preprocessedCode.textContent = code;
}

// ── Stats ──

function renderStats(stats) {
    statsBadges.innerHTML = '';

    if (stats.total_errors > 0) {
        statsBadges.innerHTML += `<span class="stat-badge errors">✕ ${stats.total_errors} error${stats.total_errors !== 1 ? 's' : ''}</span>`;
    }
    if (stats.total_warnings > 0) {
        statsBadges.innerHTML += `<span class="stat-badge warnings">⚠ ${stats.total_warnings} warning${stats.total_warnings !== 1 ? 's' : ''}</span>`;
    }
    if (stats.total_errors === 0 && stats.total_warnings === 0) {
        statsBadges.innerHTML += `<span class="stat-badge success">✓ Clean</span>`;
    }
}

// ── Highlight error lines in editor ──

function highlightErrorLines(errors) {
    errors.forEach(err => {
        if (err.line && err.type !== 'info') {
            const lineNum = err.line - 1;
            const className = err.type === 'error' ? 'line-error' : 'line-warning';
            editor.addLineClass(lineNum, 'background', className);
        }
    });
}

// ══════════════════════════════════════
//  Utility
// ══════════════════════════════════════

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
