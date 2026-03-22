"""
Symbol Table Module
Manages symbol table for identifier tracking
"""


class SymbolTable:
    """Symbol Table with simple frequency-based usage counting"""
    
    def __init__(self):
        self.symbols = []  # List of all symbol entries
        self.scope_stack = ["global"]
        self.scope_counter = 0
    
    def current_scope(self):
        """Get current scope name"""
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
                return  # Already exists, don't add duplicate
        
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
        """
        Calculate usage counts by counting frequency and subtracting 1
        Frequency - 1 = usage count (subtract the declaration itself)
        """
        # Count frequency of each identifier in tokens
        identifier_frequency = {}
        
        for token in tokens:
            if token['type'] == 'IDENTIFIER':
                name = token['value']
                identifier_frequency[name] = identifier_frequency.get(name, 0) + 1
        
        # Update usage counts: frequency - 1
        for symbol in self.symbols:
            name = symbol['name']
            if name in identifier_frequency:
                symbol['usage_count'] = identifier_frequency[name] - 1
            else:
                symbol['usage_count'] = 0
    
    def get_all_symbols(self):
        """Get all symbol entries sorted by declared line"""
        return sorted(self.symbols, key=lambda x: x['declared_line'])
    
    def get_unused_symbols(self):
        """Get symbols that were declared but never used"""
        return [s for s in self.symbols 
                if s['category'] == 'variable' and s['usage_count'] == 0]
    
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