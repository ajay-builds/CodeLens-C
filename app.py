from flask import Flask, render_template, request, jsonify
from preprocessing import Preprocessor
from lex import LexicalAnalyzer

app = Flask(__name__)


def analyze_code(code, language):
    """
    Main analysis function that coordinates all phases
    
    Args:
        code: Source code string
        language: Programming language ('C' or 'C++')
    
    Returns:
        dict: Analysis results including tokens, preprocessed code, and symbol table
    """
    # Phase 1: Preprocessing
    preprocessor = Preprocessor()
    preprocessed_code = preprocessor.preprocess(code)
    
    # Phase 2: Lexical Analysis (Tokenization)
    lexer = LexicalAnalyzer(language)
    tokens = lexer.tokenize(preprocessed_code)
    
    # Phase 3: Symbol Table Generation
    symbol_table = lexer.build_symbol_table()
    
    # Gather results
    results = {
        'tokens': tokens,
        'total_tokens': len(tokens),
        'preprocessed_code': preprocessed_code,
        'symbol_table': {
            'symbols': symbol_table.get_all_symbols(),
            'statistics': symbol_table.get_statistics()
        }
    }
    
    return results


@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    API endpoint for code analysis
    Accepts JSON with 'code' and 'language' fields
    Returns analysis results
    """
    try:
        # Get request data
        data = request.get_json(silent=True) or {}
        code = data.get('code', '')
        language = data.get('language', 'C')
        
        # Validate input
        if not code.strip():
            return jsonify({'error': 'No code provided'}), 400
        
        # Perform analysis
        results = analyze_code(code, language)
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)