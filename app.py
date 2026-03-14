from flask import Flask, render_template, request, jsonify
import re

app = Flask(__name__)

class LexicalAnalyzer:
    """Lexical Analyzer for C and C++"""
    
    def __init__(self, language):
        self.language = language
        self.tokens = []
        self.original_code = ""
        self.preprocessed_code = ""
        self.removed_comments = []
        self.removed_directives = []
        self.setup_patterns()

    def _blank_removed_line(self, line):
        if line.endswith('\r\n'):
            return '\r\n'
        if line.endswith('\n'):
            return '\n'
        return ''

    def _mask_removed_text(self, text):
        return ''.join(char if char in '\r\n' else ' ' for char in text)

    def _remove_preprocessor_directives(self, code):
        lines = code.splitlines(keepends=True)
        processed_lines = []
        offset = 0
        index = 0

        while index < len(lines):
            line = lines[index]
            line_start = offset

            if re.match(r'^[ \t]*#', line):
                directive_lines = [line]
                offset += len(line)

                while line.rstrip('\r\n').endswith('\\') and index + 1 < len(lines):
                    index += 1
                    line = lines[index]
                    directive_lines.append(line)
                    offset += len(line)

                directive_value = ''.join(directive_lines)
                self.removed_directives.append({
                    'type': 'PREPROCESSOR_DIRECTIVE',
                    'value': directive_value,
                    'start': line_start,
                    'end': offset
                })
                processed_lines.extend(
                    self._blank_removed_line(directive_line)
                    for directive_line in directive_lines
                )
                index += 1
                continue

            processed_lines.append(line)
            offset += len(line)
            index += 1

        return ''.join(processed_lines)
    
    def preprocess(self, code):
        """Preprocessing Phase: Remove comments and preprocessor directives"""
        self.original_code = code
        self.removed_comments = []
        self.removed_directives = []
        preprocessed = code
        
        # Remove multi-line comments /* ... */
        multi_comment_pattern = r'/\*[\s\S]*?\*/'
        multi_comments = list(re.finditer(multi_comment_pattern, preprocessed))
        for match in multi_comments:
            self.removed_comments.append({
                'type': 'MULTI_LINE_COMMENT',
                'value': match.group(0),
                'start': match.start(),
                'end': match.end()
            })
        preprocessed = re.sub(
            multi_comment_pattern,
            lambda match: self._mask_removed_text(match.group(0)),
            preprocessed
        )
        
        # Remove single-line comments // ...
        single_comment_pattern = r'//.*'
        single_comments = list(re.finditer(single_comment_pattern, preprocessed))
        for match in single_comments:
            self.removed_comments.append({
                'type': 'SINGLE_LINE_COMMENT',
                'value': match.group(0),
                'start': match.start(),
                'end': match.end()
            })
        preprocessed = re.sub(
            single_comment_pattern,
            lambda match: self._mask_removed_text(match.group(0)),
            preprocessed
        )

        self.removed_comments.sort(key=lambda comment: comment['start'])

        preprocessed = self._remove_preprocessor_directives(preprocessed)
        
        self.preprocessed_code = preprocessed
        return preprocessed
    
    def setup_patterns(self):        
        # Keywords for each language
        self.keywords = {
            'C': {
                'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 
                'do', 'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 
                'if', 'int', 'long', 'register', 'return', 'short', 'signed', 
                'sizeof', 'static', 'struct', 'switch', 'typedef', 'union', 
                'unsigned', 'void', 'volatile', 'while'
            },
            'C++': {
                'auto', 'break', 'case', 'char', 'const', 'continue', 'default',
                'do', 'double', 'else', 'enum', 'extern', 'float', 'for', 'goto',
                'if', 'int', 'long', 'register', 'return', 'short', 'signed',
                'sizeof', 'static', 'struct', 'switch', 'typedef', 'union',
                'unsigned', 'void', 'volatile', 'while', 'class', 'private',
                'protected', 'public', 'try', 'catch', 'throw', 'new', 'delete',
                'this', 'operator', 'friend', 'inline', 'virtual', 'template',
                'namespace', 'using', 'bool', 'true', 'false', 'explicit',
                'typename', 'mutable', 'const_cast', 'dynamic_cast', 'reinterpret_cast',
                'static_cast', 'typeid', 'and', 'or', 'not', 'xor'
            }
        }
        
        # Patterns for tokens
        self.patterns = [
            # String literals
            ('STRING_LITERAL', r'"(?:[^"\\]|\\.)*"'),
            # Character literals
            ('CHAR_LITERAL', r"'(?:[^'\\]|\\.)+'"),
            # Floating point numbers
            ('FLOAT_LITERAL', r'\d+\.\d+([eE][+-]?\d+)?[fFlL]?'),
            # Integer literals (hex, octal, decimal)
            ('INT_LITERAL', r'0[xX][0-9a-fA-F]+[lLuU]*|0[0-7]+[lLuU]*|\d+[lLuU]*'),
            # Identifiers and keywords (will be separated later)
            ('IDENTIFIER', r'[a-zA-Z_]\w*'),
            # Operators and punctuation
            ('OPERATOR', r'\+\+|--|->|\*=|/=|%=|\+=|-=|<<=|>>=|&=|\^=|\|=|&&|\|\||<<|>>|<=|>=|==|!=|[+\-*/%=<>!&|^~]'),
            # Delimiters
            ('DELIMITER', r'[{}()\[\];,.:?]'),
            # Whitespace (to skip)
            ('WHITESPACE', r'\s+'),
            # Unknown characters
            ('UNKNOWN', r'.'),
        ]
        
        # Compile patterns
        self.compiled_patterns = [(name, re.compile(pattern)) for name, pattern in self.patterns]
    
    def analyze(self, code):
        """Perform lexical analysis on the code"""
        self.tokens = []
        
        # PHASE 1: PREPROCESSING - Remove comments and preprocessor directives
        preprocessed_code = self.preprocess(code)
        
        # PHASE 2: TOKENIZATION - Tokenize the preprocessed code
        lines = preprocessed_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            position = 0
            
            while position < len(line):
                match_found = False
                
                for token_type, pattern in self.compiled_patterns:
                    match = pattern.match(line, position)
                    
                    if match:
                        value = match.group(0)
                        
                        # Skip whitespace
                        if token_type == 'WHITESPACE':
                            position = match.end()
                            match_found = True
                            break
                        
                        # Check if identifier is actually a keyword
                        if token_type == 'IDENTIFIER':
                            if value in self.keywords[self.language]:
                                token_type = 'KEYWORD'
                        
                        # Add token
                        self.tokens.append({
                            'type': token_type,
                            'value': value,
                            'line': line_num,
                            'column': position + 1
                        })
                        
                        position = match.end()
                        match_found = True
                        break
                
                if not match_found:
                    position += 1
        
        return self.tokens
    
    def get_token_summary(self):
        """Get summary statistics of tokens"""
        summary = {}
        for token in self.tokens:
            token_type = token['type']
            summary[token_type] = summary.get(token_type, 0) + 1
        return summary


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze code and return tokens"""
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'C')
        
        if not code.strip():
            return jsonify({'error': 'No code provided'}), 400
        
        # Create analyzer and perform analysis
        analyzer = LexicalAnalyzer(language)
        tokens = analyzer.analyze(code)
        summary = analyzer.get_token_summary()
        
        return jsonify({
            'success': True,
            'tokens': tokens,
            'summary': summary,
            'total_tokens': len(tokens),
            'preprocessing': {
                'comments_removed': len(analyzer.removed_comments),
                'comment_details': analyzer.removed_comments,
                'directives_removed': len(analyzer.removed_directives),
                'directive_details': analyzer.removed_directives
            },
            'preprocessed_code': analyzer.preprocessed_code
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
