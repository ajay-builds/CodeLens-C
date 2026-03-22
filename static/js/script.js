// Global variables
let currentLanguage = 'C';

// DOM Elements
const codeInput = document.getElementById('codeInput');
const lineNumbers = document.getElementById('lineNumbers');
const analyzeBtn = document.getElementById('analyzeBtn');
const uploadBtn = document.getElementById('uploadBtn');
const fileInput = document.getElementById('fileInput');
const clearCodeBtn = document.getElementById('clearCodeBtn');
const currentLang = document.getElementById('currentLang');
const preprocessedCodeBlock = document.getElementById('preprocessedCode');
const tokensBody = document.getElementById('tokensBody');
const symbolTableBody = document.getElementById('symbolTableBody');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    updateLineNumbers();
    validateDom();
});

// Event Listeners
function setupEventListeners() {
    // Language selection
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentLanguage = this.dataset.lang;
            setText(currentLang, currentLanguage);
        });
    });

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            switchTab(tabName);
        });
    });

    // Code input
    if (codeInput) {
        codeInput.addEventListener('input', updateLineNumbers);
        codeInput.addEventListener('scroll', syncScroll);
    }

    // Buttons
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeCode);
    }
    if (uploadBtn && fileInput) {
        uploadBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileUpload);
    }
    if (clearCodeBtn) {
        clearCodeBtn.addEventListener('click', clearCode);
    }
}

// Update line numbers
function updateLineNumbers() {
    if (!codeInput || !lineNumbers) {
        return;
    }

    const lines = codeInput.value.split('\n').length;
    let lineNumbersText = '';
    for (let i = 1; i <= lines; i++) {
        lineNumbersText += i + '\n';
    }
    setText(lineNumbers, lineNumbersText);
}

// Sync scroll
function syncScroll() {
    if (!codeInput || !lineNumbers) {
        return;
    }

    lineNumbers.scrollTop = codeInput.scrollTop;
}

// Switch tabs
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    const nextTab = document.getElementById(`${tabName}-tab`);
    if (nextTab) {
        nextTab.classList.add('active');
    }
}

// Handle file upload
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        if (!codeInput) {
            return;
        }

        codeInput.value = e.target.result;
        updateLineNumbers();
    };
    reader.readAsText(file);
}

// Clear code
function clearCode() {
    if (!codeInput) {
        return;
    }

    codeInput.value = '';
    updateLineNumbers();
}

// Analyze code
async function analyzeCode() {
    if (!codeInput) {
        alert('Code editor is not available.');
        return;
    }

    const code = codeInput.value.trim();

    if (!code) {
        alert('Please enter or upload code first!');
        return;
    }

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                language: currentLanguage
            })
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Update UI
        displayPreprocessing(data.preprocessed_code);
        displayTokens(data.tokens);
        displaySymbolTable(data.symbol_table);

        // Switch to preprocessing tab
        switchTab('preprocessing');

    } catch (error) {
        console.error('Error:', error);
        alert(`Analysis failed: ${error.message}`);
    }
}

// Display preprocessing information
function displayPreprocessing(preprocessedCode) {
    setText(preprocessedCodeBlock, preprocessedCode);
}

// Display tokens in table
function displayTokens(tokens) {
    if (!tokensBody) {
        return;
    }

    tokensBody.innerHTML = '';

    if (tokens.length === 0) {
        tokensBody.innerHTML = '<tr><td colspan="5" class="no-data">No tokens found</td></tr>';
        return;
    }

    tokens.forEach((token, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index + 1}</td>
            <td><span class="token-type token-${token.type}">${token.type}</span></td>
            <td><code>${escapeHtml(token.value)}</code></td>
            <td>${token.line}</td>
            <td>${token.column}</td>
        `;
        tokensBody.appendChild(row);
    });
}

// Display symbol table
function displaySymbolTable(symbolTableData) {
    if (!symbolTableBody) {
        return;
    }

    const { symbols } = symbolTableData;

    symbolTableBody.innerHTML = '';

    if (!symbols || symbols.length === 0) {
        symbolTableBody.innerHTML = '<tr><td colspan="8" class="no-data">No symbols found</td></tr>';
        return;
    }

    // Sort symbols by declaration line
    symbols.sort((a, b) => a.declared_line - b.declared_line);

    symbols.forEach((symbol, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index + 1}</td>
            <td><code>${escapeHtml(symbol.name)}</code></td>
            <td><span class="symbol-type-${symbol.category}">${symbol.category}</span></td>
            <td>${symbol.data_type || 'N/A'}</td>
            <td>${symbol.scope}</td>
            <td>${symbol.declared_line}</td>
            <td>${symbol.initialized ? 'Yes' : 'No'}</td>
            <td>${symbol.usage_count}</td>
        `;
        symbolTableBody.appendChild(row);
    });
}

// Utility function to set text safely
function setText(element, value) {
    if (element) {
        element.textContent = value;
    }
}

// Validate DOM elements
function validateDom() {
    const requiredElements = [
        ['codeInput', codeInput],
        ['lineNumbers', lineNumbers],
        ['analyzeBtn', analyzeBtn],
        ['preprocessedCode', preprocessedCodeBlock],
        ['tokensBody', tokensBody],
        ['symbolTableBody', symbolTableBody]
    ];

    const missingIds = requiredElements
        .filter(([, element]) => !element)
        .map(([id]) => id);

    if (missingIds.length > 0) {
        console.warn(`Missing DOM elements: ${missingIds.join(', ')}`);
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}