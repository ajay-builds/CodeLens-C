from flask import Flask, render_template, request, jsonify
import re

app = Flask(__name__)

class SymbolTable:
    """Symbol Table with simple frequency-based usage counting"""
    
    def __init__(self):
        self.symbols = []  # List of all symbol entries
        self.scope_stack = ["global"]
        self.scope_counter = 0
    
    def current_scope(self):
        return self.scope_stack[-1]
    
    def enter_scope(self, scope_name=None):
        """Enter a new scope"""
        if scope_name is None:
            self.scope_counter += 1
            scope_name = f"block_{self.scope_counter}"
        self.scope_stack.append(scope_name)
    
    def exit_scope(self):
        """Exit current scope"""
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
    
    def add_symbol(self, name, category, line, data_type=None, initialized=False):
        """Add a new symbol declaration"""
        scope = self.current_scope()
        
        # Check if already declared in current scope
        for entry in self.symbols:
            if entry['name'] == name and entry['scope'] == scope:
                return  # Already exists
        
        # Add new symbol
        self.symbols.append({
            'name': name,
            'category': category,
            'data_type': data_type,
            'scope': scope,
            'declared_line': line,
            'initialized': initialized,
            'usage_count': 0  # Will be calculated later
        })
    
    def calculate_usage_counts(self, tokens):
        """Calculate usage counts by counting frequency and subtracting 1"""
        # Count frequency of each identifier in tokens
        identifier_frequency = {}
        
        for token in tokens:
            if token['type'] == 'IDENTIFIER':
                name = token['value']
                identifier_frequency[name] = identifier_frequency.get(name, 0) + 1
        
        # Update usage counts: frequency - 1 (subtract the declaration)
        for symbol in self.symbols:
            name = symbol['name']
            if name in identifier_frequency:
                # Frequency - 1 = usage count (minus the declaration itself)
                symbol['usage_count'] = identifier_frequency[name] - 1
            else:
                symbol['usage_count'] = 0
    
    def get_all_symbols(self):
        """Get all symbol entries sorted by line"""
        return sorted(self.symbols, key=lambda x: x['declared_line'])
    
    def get_unused_symbols(self):
        """Get symbols that were declared but never used"""
        return [s for s in self.symbols if s['category'] == 'variable' and s['usage_count'] == 0]
    
    def get_statistics(self):
        """Get symbol table statistics"""
        variables = [s for s in self.symbols if s['category'] == 'variable']
        functions = [s for s in self.symbols if s['category'] == 'function']
        unused = [s for s in variables if s['usage_count'] == 0]
        uninitialized = [s for s in variables if not s['initialized']]
        
        return {
            'total_symbols': len(self.symbols),
            'variables': len(variables),
            'functions': len(functions),
            'unused_variables': len(unused),
            'uninitialized_variables': len(uninitialized)
        }
 

class LexicalAnalyzer:
    """Lexical Analyzer for C and C++"""
    
    def __init__(self, language):
        self.language = language
        self.tokens = []
        self.preprocessed_code = ""
        self.removed_comment_count = 0
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
        index = 0

        while index < len(lines):
            line = lines[index]

            if re.match(r'^[ \t]*#', line):
                directive_lines = [line]

                while line.rstrip('\r\n').endswith('\\') and index + 1 < len(lines):
                    index += 1
                    line = lines[index]
                    directive_lines.append(line)
                processed_lines.extend(
                    self._blank_removed_line(directive_line)
                    for directive_line in directive_lines
                )
                index += 1
                continue

            processed_lines.append(line)
            index += 1

        return ''.join(processed_lines)
    
    def preprocess(self, code):
        """Preprocessing Phase: Remove comments and preprocessor directives"""
        self.removed_comment_count = 0
        preprocessed = code
        
        # Remove multi-line comments /* ... */
        multi_comment_pattern = r'/\*[\s\S]*?\*/'
        self.removed_comment_count += sum(1 for _ in re.finditer(multi_comment_pattern, preprocessed))
        preprocessed = re.sub(
            multi_comment_pattern,
            lambda match: self._mask_removed_text(match.group(0)),
            preprocessed
        )
        
        # Remove single-line comments // ...
        single_comment_pattern = r'//.*'
        self.removed_comment_count += sum(1 for _ in re.finditer(single_comment_pattern, preprocessed))
        preprocessed = re.sub(
            single_comment_pattern,
            lambda match: self._mask_removed_text(match.group(0)),
            preprocessed
        )

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
        
        self.compiled_patterns = [
            ('STRING_LITERAL', re.compile(r'"(?:[^"\\]|\\.)*"')),
            ('CHAR_LITERAL', re.compile(r"'(?:[^'\\]|\\.)+'")),
            ('FLOAT_LITERAL', re.compile(r'\d+\.\d+([eE][+-]?\d+)?[fFlL]?')),
            ('INT_LITERAL', re.compile(r'0[xX][0-9a-fA-F]+[lLuU]*|0[0-7]+[lLuU]*|\d+[lLuU]*')),
            ('IDENTIFIER', re.compile(r'[a-zA-Z_]\w*')),
            ('OPERATOR', re.compile(r'\+\+|--|->|\*=|/=|%=|\+=|-=|<<=|>>=|&=|\^=|\|=|&&|\|\||<<|>>|<=|>=|==|!=|[+\-*/%=<>!&|^~]')),
            ('DELIMITER', re.compile(r'[{}()\[\];,.:?]')),
            ('WHITESPACE', re.compile(r'\s+')),
            ('UNKNOWN', re.compile(r'.')),
        ]
    
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
    
    def build_symbol_table(self):
        """Build symbol table with simple two-pass approach"""
        self.symbol_table = SymbolTable()
        
        data_types = {
            'int', 'float', 'double', 'char', 'void', 'long', 'short',
            'unsigned', 'signed', 'bool', 'size_t', 'auto'
        }
        
        # PASS 1: Find all declarations and build symbol table
        i = 0
        while i < len(self.tokens):
            token = self.tokens[i]
            
            # Track scope changes
            if token['type'] == 'DELIMITER':
                if token['value'] == '{':
                    self.symbol_table.enter_scope()
                elif token['value'] == '}':
                    self.symbol_table.exit_scope()
            
            # Find type declarations
            if token['type'] == 'KEYWORD' and token['value'] in data_types:
                base_type = token['value']
                j = i + 1
                
                # Handle type modifiers (unsigned int, long long, etc.)
                while j < len(self.tokens) and \
                    self.tokens[j]['type'] == 'KEYWORD' and \
                    self.tokens[j]['value'] in data_types:
                    base_type += ' ' + self.tokens[j]['value']
                    j += 1
                
                # Process all identifiers in this declaration
                while j < len(self.tokens):
                    t = self.tokens[j]
                    
                    # End of declaration
                    if t['type'] == 'DELIMITER' and t['value'] in [';', '{']:
                        break
                    
                    # Handle pointers
                    data_type = base_type
                    while j < len(self.tokens) and \
                        self.tokens[j]['type'] == 'OPERATOR' and \
                        self.tokens[j]['value'] == '*':
                        data_type += '*'
                        j += 1
                    
                    # Found identifier
                    if j < len(self.tokens) and self.tokens[j]['type'] == 'IDENTIFIER':
                        id_name = self.tokens[j]['value']
                        id_line = self.tokens[j]['line']
                        
                        # Check if function (followed by '(')
                        is_function = False
                        if j + 1 < len(self.tokens) and \
                        self.tokens[j + 1]['type'] == 'DELIMITER' and \
                        self.tokens[j + 1]['value'] == '(':
                            is_function = True
                            category = 'function'
                            # Enter function scope
                            self.symbol_table.enter_scope(id_name)
                        else:
                            category = 'variable'
                        
                        # Check if initialized
                        initialized = False
                        if j + 1 < len(self.tokens) and \
                        self.tokens[j + 1]['type'] == 'OPERATOR' and \
                        self.tokens[j + 1]['value'] == '=':
                            initialized = True
                        
                        # Add symbol
                        self.symbol_table.add_symbol(
                            id_name,
                            category,
                            id_line,
                            data_type,
                            initialized
                        )
                    
                    j += 1
            
            i += 1
        
        # PASS 2: Calculate usage counts based on frequency
        self.symbol_table.calculate_usage_counts(self.tokens)
        
        return self.symbol_table
    
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
        data = request.get_json(silent=True) or {}
        code = data.get('code', '')
        language = data.get('language', 'C')
        
        if not code.strip():
            return jsonify({'error': 'No code provided'}), 400
        
        # Create analyzer and perform analysis
        analyzer = LexicalAnalyzer(language)
        tokens = analyzer.analyze(code)
        summary = analyzer.get_token_summary()

        #build symbol table
        symbol_table = analyzer.build_symbol_table()
        symbol_stats = symbol_table.get_statistics()
        all_symbols = symbol_table.get_all_symbols()

        
        return jsonify({
            'tokens': tokens,
            'summary': summary,
            'total_tokens': len(tokens),
            'preprocessing': {
                'comments_removed': analyzer.removed_comment_count
            },
            'preprocessed_code': analyzer.preprocessed_code,
            'symbol_table': {
                'symbols': all_symbols,
                'statistics': symbol_stats
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
