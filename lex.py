"""
Lexical Analyzer Module
Tokenizes C/C++ code
"""
import re
from symbol_table import SymbolTable


class LexicalAnalyzer:
    """Lexical Analyzer for C and C++"""
    
    def __init__(self, language):
        self.language = language
        self.tokens = []
        self.symbol_table = None
        self.setup_patterns()
    
    def setup_patterns(self):
        """Setup token patterns and keywords for C/C++"""
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
        
        # Compiled regex patterns for token recognition
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
    
    def tokenize(self, code):
        """
        Tokenize the preprocessed code
        Returns list of tokens
        """
        self.tokens = []
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            position = 0
            
            while position < len(line):
                match_found = False
                
                for token_type, pattern in self.compiled_patterns:
                    match = pattern.match(line, position)
                    
                    if match:
                        value = match.group(0)
                        
                        # Skip whitespace tokens
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
        """Build symbol table from tokens"""
        self.symbol_table = SymbolTable()
        
        # C/C++ data types
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
                        if j + 1 < len(self.tokens) and \
                           self.tokens[j + 1]['type'] == 'DELIMITER' and \
                           self.tokens[j + 1]['value'] == '(':
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
    
    def get_tokens(self):
        """Get all tokens"""
        return self.tokens
    
    def get_symbol_table(self):
        """Get symbol table"""
        return self.symbol_table