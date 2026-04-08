"""
CodeLens-C — Phase 2: Lexical Analyzer (Tokenizer)
Uses PLY Lex to tokenize C/C++ source code.
Detects invalid tokens, mistyped keywords, and invalid identifiers.
"""

import re
import ply.lex as lex


# ──────────────────────────────────────────────
#  Keyword list
# ──────────────────────────────────────────────
KEYWORDS = {
    'int', 'float', 'double', 'char', 'void',
    'short', 'long', 'unsigned', 'signed', 'const',
    'if', 'else', 'while', 'for', 'do',
    'return', 'break', 'continue',
    'switch', 'case', 'default',
    'struct', 'typedef', 'enum', 'sizeof',
    'printf', 'scanf',  # recognized as identifiers, but useful for suggestions
    'main',
    'cout', 'cin', 'endl',
    'include', 'define',
    'true', 'false',
    'NULL',
}

# Keywords that become token types
reserved = {
    'int': 'INT',
    'float': 'FLOAT',
    'double': 'DOUBLE',
    'char': 'CHAR',
    'void': 'VOID',
    'short': 'SHORT',
    'long': 'LONG',
    'unsigned': 'UNSIGNED',
    'signed': 'SIGNED',
    'const': 'CONST',
    'if': 'IF',
    'else': 'ELSE',
    'while': 'WHILE',
    'for': 'FOR',
    'do': 'DO',
    'return': 'RETURN',
    'break': 'BREAK',
    'continue': 'CONTINUE',
    'switch': 'SWITCH',
    'case': 'CASE',
    'default': 'DEFAULT',
    'struct': 'STRUCT',
    'typedef': 'TYPEDEF',
    'enum': 'ENUM',
    'sizeof': 'SIZEOF',
    'true': 'TRUE',
    'false': 'FALSE',
    'NULL': 'NULL_KW',
    # C++ keywords
    'using': 'USING',
    'namespace': 'NAMESPACE',
    'string': 'STRING_TYPE',
    'bool': 'BOOL',
}

# ──────────────────────────────────────────────
#  Token list
# ──────────────────────────────────────────────
tokens = [
    # Literals
    'ID', 'NUMBER_INT', 'NUMBER_FLOAT', 'STRING_LITERAL', 'CHAR_LITERAL',
    # Arithmetic
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MODULO',
    # Assignment
    'EQUALS', 'PLUS_ASSIGN', 'MINUS_ASSIGN', 'TIMES_ASSIGN', 'DIVIDE_ASSIGN',
    'MODULO_ASSIGN',
    # Comparison
    'EQ', 'NEQ', 'LT', 'GT', 'LTE', 'GTE',
    # Logical
    'AND', 'OR', 'NOT',
    # Bitwise
    'BIT_AND', 'BIT_OR', 'BIT_XOR', 'BIT_NOT', 'LSHIFT', 'RSHIFT',
    # Increment / Decrement
    'INCREMENT', 'DECREMENT',
    # Delimiters
    'SEMICOLON', 'COMMA', 'DOT',
    'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE', 'LBRACKET', 'RBRACKET',
    # Special
    'ARROW', 'COLON', 'QUESTION',
    # Stream operators for C++
    'STREAM_OUT', 'STREAM_IN',
] + list(reserved.values())


# ──────────────────────────────────────────────
#  Mistyped TYPE keyword detection
#  Only checks words that appear in a type position
#  (i.e., an unknown word followed by an identifier)
# ──────────────────────────────────────────────

# Type keywords that can appear before a variable name in declarations
TYPE_KEYWORDS = {'int', 'float', 'double', 'char', 'void', 'short', 'long',
                 'unsigned', 'signed', 'const', 'struct', 'enum', 'return',
                 'string'}


def _levenshtein(s1, s2):
    """Compute edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def _suggest_type_keyword(token_value):
    """
    Check if token_value is a mistyped TYPE keyword only.
    Only compares against type keywords (int, float, char, etc.),
    NOT against all keywords like if/else/while.
    """
    best_match = None
    best_dist = 999
    lower = token_value.lower()
    for kw in TYPE_KEYWORDS:
        dist = _levenshtein(lower, kw)
        if dist < best_dist:
            best_dist = dist
            best_match = kw
    # Suggest only if edit distance <= 2, and it's not already the keyword
    if best_dist <= 2 and best_dist > 0 and len(token_value) >= 2:
        return best_match
    return None


# ──────────────────────────────────────────────
#  Build the PLY Lexer
# ──────────────────────────────────────────────
def build_lexer(error_collector):
    """Build and return a PLY lexer configured with error reporting."""

    # ── Multi-character operators (order matters — longest first) ──
    t_INCREMENT     = r'\+\+'
    t_DECREMENT     = r'--'
    t_PLUS_ASSIGN   = r'\+='
    t_MINUS_ASSIGN  = r'-='
    t_TIMES_ASSIGN  = r'\*='
    t_DIVIDE_ASSIGN = r'/='
    t_MODULO_ASSIGN = r'%='
    t_EQ            = r'=='
    t_NEQ           = r'!='
    t_LTE           = r'<='
    t_GTE           = r'>='
    t_AND           = r'&&'
    t_OR            = r'\|\|'
    t_LSHIFT        = r'<<'
    t_RSHIFT        = r'>>'
    t_ARROW         = r'->'

    # ── Single-character operators ──
    t_PLUS      = r'\+'
    t_MINUS     = r'-'
    t_TIMES     = r'\*'
    t_DIVIDE    = r'/'
    t_MODULO    = r'%'
    t_EQUALS    = r'='
    t_LT        = r'<'
    t_GT        = r'>'
    t_NOT       = r'!'
    t_BIT_AND   = r'&'
    t_BIT_OR    = r'\|'
    t_BIT_XOR   = r'\^'
    t_BIT_NOT   = r'~'

    # ── Delimiters ──
    t_SEMICOLON  = r';'
    t_COMMA      = r','
    t_DOT        = r'\.'
    t_LPAREN     = r'\('
    t_RPAREN     = r'\)'
    t_LBRACE     = r'\{'
    t_RBRACE     = r'\}'
    t_LBRACKET   = r'\['
    t_RBRACKET   = r'\]'
    t_COLON      = r':'
    t_QUESTION   = r'\?'

    # ── Floating-point numbers (must come before integers) ──
    def t_NUMBER_FLOAT(t):
        r'(\d+\.\d*|\.\d+)([eE][+-]?\d+)?[fFlL]?'
        t.value = float(t.value.rstrip('fFlL'))
        return t

    # ── Integer numbers ──
    def t_NUMBER_INT(t):
        r'(0[xX][0-9a-fA-F]+|0[bB][01]+|0[0-7]+|\d+)[uUlL]*'
        # Convert to int
        raw = t.value.rstrip('uUlL')
        if raw.startswith(('0x', '0X')):
            t.value = int(raw, 16)
        elif raw.startswith(('0b', '0B')):
            t.value = int(raw, 2)
        elif raw.startswith('0') and len(raw) > 1 and raw[1:].isdigit():
            t.value = int(raw, 8)
        else:
            t.value = int(raw)
        return t

    # ── String literals ──
    def t_STRING_LITERAL(t):
        r'"([^"\\]|\\.)*"'
        t.value = t.value[1:-1]  # strip quotes
        return t

    # ── Character literals ──
    def t_CHAR_LITERAL(t):
        r"'([^'\\]|\\.)*'"
        raw = t.value[1:-1]  # strip quotes
        # Check length: valid char literal is 1 char or a single escape like \n
        if len(raw) == 0:
            error_collector.add_error(
                "Lexical",
                "Empty character literal ''",
                t.lexer.lineno,
                suggestion="A character literal must contain exactly one character, e.g. 'a'"
            )
        elif len(raw) > 1 and not (len(raw) == 2 and raw[0] == '\\'):
            # More than 1 char AND not a single escape sequence → error
            error_collector.add_error(
                "Lexical",
                f"Multi-character constant '{raw}' in single quotes",
                t.lexer.lineno,
                suggestion=f"Use double quotes for strings: \"{raw}\", or a single character in single quotes: '{raw[0]}'"
            )
        t.value = raw
        return t

    # ── Invalid identifier: starts with digit(s) followed by letters ──
    def t_INVALID_NUM_ID(t):
        r'\d+[a-zA-Z_]\w*'
        error_collector.add_error(
            "Lexical",
            f"Invalid identifier '{t.value}' — identifiers cannot start with a digit",
            t.lexer.lineno,
            suggestion="Identifiers must start with a letter or underscore"
        )
        # Treat as ID so parser can continue
        t.type = 'ID'
        return t

    # ── Identifiers and keywords ──
    def t_ID(t):
        r'[a-zA-Z_]\w*'
        # Check if it's a reserved keyword
        if t.value in reserved:
            t.type = reserved[t.value]
        else:
            t.type = 'ID'
        return t

    # ── Track line numbers ──
    def t_newline(t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    # ── Ignore spaces and tabs ──
    t_ignore = ' \t\r'

    # ── Error handling for invalid characters ──
    def t_error(t):
        char = t.value[0]
        error_collector.add_error(
            "Lexical",
            f"Invalid character '{char}'",
            t.lexer.lineno,
            suggestion=f"Remove or replace the invalid character '{char}'"
        )
        t.lexer.skip(1)

    lexer = lex.lex()
    return lexer


def tokenize(source_code, error_collector):
    """
    Tokenize source code and return a list of token dicts.
    After tokenization, runs a second pass to detect mistyped type keywords
    by looking for ID-ID patterns (e.g., 'inty x' or 'flot y').

    Returns:
        list[dict]: Each token as {"type", "value", "line"}
    """
    lexer = build_lexer(error_collector)
    lexer.input(source_code)
    token_list = []

    while True:
        tok = lexer.token()
        if not tok:
            break
        token_list.append({
            "type": tok.type,
            "value": str(tok.value),
            "line": tok.lineno,
        })

    # ── Post-tokenization: detect mistyped type keywords ──
    # Pattern: ID followed by ID means the first ID might be a misspelled
    # type keyword (e.g., "inty x", "flot y", "boolen flag")
    # Also check: ID followed by ID EQUALS (e.g., "inty x = 5")
    # Also check: ID followed by ID LBRACKET (e.g., "inty arr[10]")
    _check_mistyped_types(token_list, error_collector)

    return token_list, lexer


def _check_mistyped_types(token_list, error_collector):
    """
    Scan the token list for patterns where an unknown identifier
    appears in a type position (before another identifier).
    Only then check if it's a mistyped type keyword.
    """
    for i in range(len(token_list) - 1):
        curr = token_list[i]
        nxt = token_list[i + 1]

        # Pattern: ID followed by ID — looks like a type declaration
        # e.g., "inty x" → 'inty' tokenized as ID, 'x' tokenized as ID
        if curr['type'] == 'ID' and nxt['type'] == 'ID':
            suggestion = _suggest_type_keyword(curr['value'])
            if suggestion:
                error_collector.add_warning(
                    "Lexical",
                    f"Unknown type '{curr['value']}' — did you mean '{suggestion}'?",
                    curr['line'],
                    suggestion=f"Replace '{curr['value']}' with '{suggestion}'"
                )

        # Pattern: ID followed by TIMES then ID — pointer declaration
        # e.g., "inty *x" → 'inty' tokenized as ID
        if (curr['type'] == 'ID' and nxt['type'] == 'TIMES'
                and i + 2 < len(token_list)
                and token_list[i + 2]['type'] == 'ID'):
            suggestion = _suggest_type_keyword(curr['value'])
            if suggestion:
                error_collector.add_warning(
                    "Lexical",
                    f"Unknown type '{curr['value']}' — did you mean '{suggestion}'?",
                    curr['line'],
                    suggestion=f"Replace '{curr['value']}' with '{suggestion}'"
                )
