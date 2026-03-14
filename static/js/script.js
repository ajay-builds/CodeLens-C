// Global variables
let currentLanguage = 'C';

// DOM Elements
const codeInput = document.getElementById('codeInput');
const lineNumbers = document.getElementById('lineNumbers');
const analyzeBtn = document.getElementById('analyzeBtn');
const uploadBtn = document.getElementById('uploadBtn');
const fileInput = document.getElementById('fileInput');
const clearCodeBtn = document.getElementById('clearCodeBtn');
const statusText = document.getElementById('statusText');
const analysisTime = document.getElementById('analysisTime');
const loadingOverlay = document.getElementById('loadingOverlay');
const currentLang = document.getElementById('currentLang');
const summaryStats = document.getElementById('summaryStats');
const tokenChart = document.getElementById('tokenChart');
const commentsRemovedValue = document.getElementById('commentsRemoved');
const removedCommentsList = document.getElementById('removedCommentsList');
const preprocessedCodeBlock = document.getElementById('preprocessedCode');
const tokensBody = document.getElementById('tokensBody');
const dumpPreview = document.getElementById('dumpPreview');

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
            updateStatus(`Language changed to ${currentLanguage}`);
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
        updateStatus(`Loaded: ${file.name}`);
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
    updateStatus('Code cleared');
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

    showLoading(true);
    const startTime = Date.now();

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

        const analysisTimeMs = Date.now() - startTime;
        setText(analysisTime, `Analysis completed in ${analysisTimeMs}ms`);

        // Update UI
        displaySummary(data);
        displayPreprocessing(data.preprocessing, data.preprocessed_code);
        displayTokens(data.tokens);
        displayDump(data);

        // Switch to preprocessing tab to show the phases
        switchTab('preprocessing');

        updateStatus(`Analysis complete: ${data.total_tokens} tokens found, ${data.preprocessing.comments_removed} comments removed`);

    } catch (error) {
        console.error('Error:', error);
        alert(`Analysis failed: ${error.message}`);
        updateStatus('Analysis failed');
    } finally {
        showLoading(false);
    }
}

// Display preprocessing information
function displayPreprocessing(preprocessing, preprocessedCode) {
    // Update comments removed count
    setText(commentsRemovedValue, preprocessing.comments_removed);
    
    // Display removed comments
    if (removedCommentsList) {
        removedCommentsList.innerHTML = '';
        
        if (preprocessing.comment_details && preprocessing.comment_details.length > 0) {
            preprocessing.comment_details.forEach((comment, index) => {
                const commentItem = document.createElement('div');
                commentItem.className = 'comment-item';
                commentItem.innerHTML = `
                    <span class="comment-type">${comment.type.replace('_', ' ')}</span>
                    <div class="comment-value">${escapeHtml(comment.value)}</div>
                `;
                removedCommentsList.appendChild(commentItem);
            });
        } else {
            removedCommentsList.innerHTML = '<p class="no-data">No comments found in code</p>';
        }
    }
    
    // Display preprocessed code
    setText(preprocessedCodeBlock, preprocessedCode);
}

// Display summary
function displaySummary(data) {
    if (!summaryStats || !tokenChart) {
        return;
    }

    // Create stats cards
    summaryStats.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${data.total_tokens}</div>
            <div class="stat-label">Total Tokens</div>
        </div>
    `;

    // Create chart
    tokenChart.innerHTML = '<h3 style="margin-bottom: 20px; color: #1e293b;">Token Distribution</h3>';

    const sortedSummary = Object.entries(data.summary).sort((a, b) => b[1] - a[1]);
    const maxCount = Math.max(...Object.values(data.summary));

    sortedSummary.forEach(([type, count]) => {
        const percentage = (count / maxCount) * 100;
        const row = document.createElement('div');
        row.className = 'chart-row';
        row.innerHTML = `
            <div class="chart-label">${type}</div>
            <div class="chart-bar-container">
                <div class="chart-bar" style="width: ${percentage}%">
                    ${percentage > 15 ? count : ''}
                </div>
            </div>
            <div class="chart-count">${count}</div>
        `;
        tokenChart.appendChild(row);
    });
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

// Display dump preview
function displayDump(data) {
    if (!dumpPreview) {
        return;
    }
    
    let dumpText = `${'='.repeat(80)}\n`;
    dumpText += `LEXICAL ANALYSIS DUMP\n`;
    dumpText += `Language: ${currentLanguage}\n`;
    dumpText += `Date: ${new Date().toLocaleString()}\n`;
    dumpText += `Total Tokens: ${data.total_tokens}\n`;
    dumpText += `Comments Removed: ${data.preprocessing.comments_removed}\n`;
    dumpText += `${'='.repeat(80)}\n\n`;
    
    dumpText += `PHASE 1: PREPROCESSING\n`;
    dumpText += `${'-'.repeat(80)}\n`;
    dumpText += `Comments Removed: ${data.preprocessing.comments_removed}\n\n`;
    
    if (data.preprocessing.comment_details && data.preprocessing.comment_details.length > 0) {
        dumpText += `Removed Comments:\n`;
        data.preprocessing.comment_details.forEach((comment, index) => {
            dumpText += `  ${index + 1}. ${comment.type}: ${comment.value.substring(0, 50)}${comment.value.length > 50 ? '...' : ''}\n`;
        });
    }
    
    dumpText += `\nPHASE 2: TOKENIZATION\n`;
    dumpText += `${'-'.repeat(80)}\n`;
    dumpText += `TOKEN SUMMARY:\n`;
    dumpText += `${'-'.repeat(80)}\n`;
    
    const sortedSummary = Object.entries(data.summary).sort((a, b) => a[0].localeCompare(b[0]));
    sortedSummary.forEach(([type, count]) => {
        dumpText += `${type.padEnd(25)} : ${count.toString().padStart(5)}\n`;
    });
    
    dumpText += `\n${'='.repeat(80)}\n`;
    dumpText += `DETAILED TOKEN LIST:\n`;
    dumpText += `${'='.repeat(80)}\n\n`;
    
    dumpText += `${'#'.padEnd(6)} ${'Type'.padEnd(25)} ${'Lexeme'.padEnd(30)} ${'Line'.padEnd(6)} ${'Col'.padEnd(6)}\n`;
    dumpText += `${'-'.repeat(80)}\n`;
    
    data.tokens.forEach((token, index) => {
        let lexeme = token.value;
        if (lexeme.length > 28) {
            lexeme = lexeme.substring(0, 25) + '...';
        }
        
        dumpText += `${(index + 1).toString().padEnd(6)} `;
        dumpText += `${token.type.padEnd(25)} `;
        dumpText += `${lexeme.padEnd(30)} `;
        dumpText += `${token.line.toString().padEnd(6)} `;
        dumpText += `${token.column.toString().padEnd(6)}\n`;
    });
    
    dumpText += `\n${'='.repeat(80)}\n`;
    dumpText += `END OF DUMP\n`;
    dumpText += `${'='.repeat(80)}\n`;
    
    dumpPreview.textContent = dumpText;
}

// Update status
function updateStatus(message) {
    setText(statusText, message);
}

// Show/hide loading overlay
function showLoading(show) {
    if (!loadingOverlay) {
        return;
    }

    loadingOverlay.style.display = show ? 'flex' : 'none';
}

function setText(element, value) {
    if (element) {
        element.textContent = value;
    }
}

function validateDom() {
    const requiredElements = [
        ['codeInput', codeInput],
        ['lineNumbers', lineNumbers],
        ['analyzeBtn', analyzeBtn],
        ['statusText', statusText],
        ['analysisTime', analysisTime],
        ['commentsRemoved', commentsRemovedValue],
        ['removedCommentsList', removedCommentsList],
        ['preprocessedCode', preprocessedCodeBlock],
        ['summaryStats', summaryStats],
        ['tokenChart', tokenChart],
        ['tokensBody', tokensBody],
        ['dumpPreview', dumpPreview]
    ];

    const missingIds = requiredElements
        .filter(([, element]) => !element)
        .map(([id]) => id);

    if (missingIds.length > 0) {
        console.warn(`Missing DOM elements: ${missingIds.join(', ')}`);
    }
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}