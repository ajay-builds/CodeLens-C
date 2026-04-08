"""
CodeLens-C — Flask Application
Static Source Code Analyzer for C/C++
"""

from flask import Flask, render_template, request, jsonify
from compiler.error_collector import ErrorCollector
from compiler.preprocessor import preprocess
from compiler.lexer import tokenize
from compiler.parser import parse
from compiler.symbol_table import create_symbol_table
from compiler.semantic_analyzer import analyze_semantics
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max upload


@app.route('/')
def index():
    """Serve the main editor page."""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Analyze C/C++ source code through all compiler phases.
    Accepts either raw code in 'code' field or a file upload in 'file' field.
    """
    source_code = None

    # Get source code from request
    if 'file' in request.files:
        file = request.files['file']
        if file.filename:
            if not file.filename.endswith(('.c', '.cpp', '.h', '.hpp')):
                return jsonify({
                    'success': False,
                    'error': 'Invalid file type. Please upload a .c, .cpp, .h, or .hpp file.'
                }), 400
            source_code = file.read().decode('utf-8', errors='replace')

    if source_code is None:
        source_code = request.form.get('code', '') or request.json.get('code', '') if request.is_json else request.form.get('code', '')

    if not source_code or not source_code.strip():
        return jsonify({
            'success': False,
            'error': 'No source code provided.'
        }), 400

    # ── Initialize components ──
    error_collector = ErrorCollector()

    # ── Phase 1: Preprocessing ──
    cleaned_code = preprocess(source_code, error_collector)

    # ── Phase 2: Lexical Analysis ──
    tokens, lexer = tokenize(cleaned_code, error_collector)

    # ── Phase 3: Syntax Analysis (Parse) ──
    ast = parse(cleaned_code, error_collector)

    # ── Phase 4: Symbol Table ──
    symbol_table = create_symbol_table()

    # ── Phase 5: Semantic Analysis ──
    if ast is not None:
        analyze_semantics(ast, symbol_table, error_collector)

    # ── Phase 6: Collect Results ──
    # Filter out stdlib symbols from symbol table display (line 0 = auto-declared)
    user_symbols = [s for s in symbol_table.to_json() if s['line'] != 0]

    result = {
        'success': True,
        'preprocessed_code': cleaned_code,
        'tokens': tokens,
        'errors': error_collector.to_json(),
        'symbol_table': user_symbols,
        'has_errors': error_collector.has_errors(),
        'stats': {
            'total_tokens': len(tokens),
            'total_errors': sum(1 for e in error_collector.to_json() if e['type'] == 'error'),
            'total_warnings': sum(1 for e in error_collector.to_json() if e['type'] == 'warning'),
            'total_info': sum(1 for e in error_collector.to_json() if e['type'] == 'info'),
            'total_symbols': len(user_symbols),
        }
    }

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
