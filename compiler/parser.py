"""
CodeLens-C — Phase 3: Syntax Analyzer (Parser)
Uses PLY Yacc with a simplified C/C++ grammar.
Builds a lightweight AST and detects syntax errors.
"""

import ply.yacc as yacc
from .lexer import tokens, build_lexer  # noqa: F401 — PLY needs `tokens` in scope


def build_parser(error_collector):
    """Build and return a PLY parser with error recovery."""

    # Track bracket balance for unmatched bracket detection
    _bracket_stack = []

    # ── Precedence (lowest to highest) ──
    precedence = (
        ('left', 'OR'),
        ('left', 'AND'),
        ('left', 'BIT_OR'),
        ('left', 'BIT_XOR'),
        ('left', 'BIT_AND'),
        ('left', 'EQ', 'NEQ'),
        ('left', 'LT', 'GT', 'LTE', 'GTE'),
        ('left', 'LSHIFT', 'RSHIFT'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MODULO'),
        ('right', 'NOT', 'BIT_NOT', 'UMINUS', 'UPLUS'),
        ('left', 'INCREMENT', 'DECREMENT'),
        ('right', 'ELSE'),   # dangling else
    )

    # ════════════════════════════════════════════
    #  Top-level program
    # ════════════════════════════════════════════

    def p_program(p):
        '''program : declaration_list'''
        p[0] = ('program', p[1])

    def p_declaration_list(p):
        '''declaration_list : declaration_list declaration
                            | declaration'''
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = [p[1]]

    # ════════════════════════════════════════════
    #  Declarations
    # ════════════════════════════════════════════

    def p_declaration(p):
        '''declaration : var_declaration
                       | fun_declaration
                       | using_declaration
                       | statement'''
        p[0] = p[1]

    # ── using namespace std; ──

    def p_using_declaration(p):
        '''using_declaration : USING NAMESPACE ID SEMICOLON'''
        p[0] = ('using_namespace', p[3], p.lineno(1))

    # ── Variable declarations ──

    def p_var_declaration(p):
        '''var_declaration : type_spec ID SEMICOLON
                           | type_spec ID EQUALS expression SEMICOLON
                           | type_spec ID LBRACKET expression RBRACKET SEMICOLON
                           | type_spec ID LBRACKET RBRACKET SEMICOLON
                           | const_type_spec ID EQUALS expression SEMICOLON
                           | const_type_spec ID SEMICOLON'''
        if len(p) == 4:
            p[0] = ('var_decl', p[1], p[2], None, p.lineno(2))
        elif len(p) == 6 and p[3] == '=':
            p[0] = ('var_decl_init', p[1], p[2], p[4], p.lineno(2))
        elif len(p) == 7:
            p[0] = ('array_decl', p[1], p[2], p[4], p.lineno(2))
        elif len(p) == 6 and p[3] == '[':
            p[0] = ('array_decl', p[1], p[2], None, p.lineno(2))
        else:
            p[0] = ('var_decl', p[1], p[2], None, p.lineno(2))

    def p_const_type_spec(p):
        '''const_type_spec : CONST type_spec'''
        p[0] = p[2]

    def p_var_declaration_multi(p):
        '''var_declaration : type_spec ID COMMA init_declarator_list SEMICOLON
                           | type_spec ID EQUALS expression COMMA init_declarator_list SEMICOLON'''
        if len(p) == 6:
            # int a, b, c;  or  int a, b = 5, c;
            items = [('init_item', p[2], None)] + p[4]
            p[0] = ('multi_var_decl_init', p[1], items, p.lineno(2))
        else:
            # int a = 1, b = 2, c;
            items = [('init_item', p[2], p[4])] + p[6]
            p[0] = ('multi_var_decl_init', p[1], items, p.lineno(2))

    def p_init_declarator_list(p):
        '''init_declarator_list : init_declarator_list COMMA init_declarator
                                | init_declarator'''
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1]]

    def p_init_declarator(p):
        '''init_declarator : ID EQUALS expression
                           | ID'''
        if len(p) == 4:
            p[0] = ('init_item', p[1], p[3])
        else:
            p[0] = ('init_item', p[1], None)

    # ── Type specifiers ──

    def p_type_spec(p):
        '''type_spec : INT
                     | FLOAT
                     | DOUBLE
                     | CHAR
                     | VOID
                     | LONG
                     | SHORT
                     | UNSIGNED
                     | SIGNED
                     | STRING_TYPE
                     | BOOL'''
        p[0] = p[1]

    # ── Function declarations ──

    def p_fun_declaration(p):
        '''fun_declaration : type_spec ID LPAREN params RPAREN compound_stmt'''
        p[0] = ('fun_decl', p[1], p[2], p[4], p[6], p.lineno(2))

    def p_params(p):
        '''params : param_list
                  | VOID
                  | empty'''
        if p[1] == 'void' or p[1] is None:
            p[0] = []
        else:
            p[0] = p[1]

    def p_param_list(p):
        '''param_list : param_list COMMA param
                      | param'''
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1]]

    def p_param(p):
        '''param : type_spec ID
                 | type_spec ID LBRACKET RBRACKET'''
        if len(p) == 3:
            p[0] = ('param', p[1], p[2], False, p.lineno(2))
        else:
            p[0] = ('param', p[1], p[2], True, p.lineno(2))

    # ════════════════════════════════════════════
    #  Statements
    # ════════════════════════════════════════════

    def p_compound_stmt(p):
        '''compound_stmt : LBRACE local_decls stmt_list RBRACE'''
        p[0] = ('compound', p[2], p[3], p.lineno(1))

    def p_local_decls(p):
        '''local_decls : local_decls var_declaration
                       | empty'''
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = []

    def p_stmt_list(p):
        '''stmt_list : stmt_list statement
                     | empty'''
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = []

    def p_statement(p):
        '''statement : expression_stmt
                     | compound_stmt
                     | selection_stmt
                     | iteration_stmt
                     | return_stmt
                     | break_stmt
                     | continue_stmt
                     | var_declaration'''
        p[0] = p[1]

    def p_expression_stmt(p):
        '''expression_stmt : expression SEMICOLON
                           | SEMICOLON'''
        if len(p) == 3:
            p[0] = ('expr_stmt', p[1], p.lineno(2))
        else:
            p[0] = ('empty_stmt', p.lineno(1))

    # ── Selection (if/else) ──

    def p_selection_stmt(p):
        '''selection_stmt : IF LPAREN expression RPAREN statement
                          | IF LPAREN expression RPAREN statement ELSE statement'''
        if len(p) == 6:
            p[0] = ('if', p[3], p[5], None, p.lineno(1))
        else:
            p[0] = ('if_else', p[3], p[5], p[7], p.lineno(1))

    # ── Iteration (while, for, do-while) ──

    def p_iteration_while(p):
        '''iteration_stmt : WHILE LPAREN expression RPAREN statement'''
        p[0] = ('while', p[3], p[5], p.lineno(1))

    def p_iteration_for(p):
        '''iteration_stmt : FOR LPAREN for_init for_cond for_update RPAREN statement'''
        p[0] = ('for', p[3], p[4], p[5], p[7], p.lineno(1))

    def p_for_init(p):
        '''for_init : expression SEMICOLON
                    | var_declaration
                    | SEMICOLON'''
        if len(p) == 3:
            p[0] = p[1]
        elif len(p) == 2 and p[1] == ';':
            p[0] = None
        else:
            p[0] = p[1]

    def p_for_cond(p):
        '''for_cond : expression SEMICOLON
                    | SEMICOLON'''
        if len(p) == 3:
            p[0] = p[1]
        else:
            p[0] = None

    def p_for_update(p):
        '''for_update : expression
                      | empty'''
        p[0] = p[1]

    def p_iteration_do_while(p):
        '''iteration_stmt : DO statement WHILE LPAREN expression RPAREN SEMICOLON'''
        p[0] = ('do_while', p[5], p[2], p.lineno(1))

    # ── Return, Break, Continue ──

    def p_return_stmt(p):
        '''return_stmt : RETURN SEMICOLON
                       | RETURN expression SEMICOLON'''
        if len(p) == 3:
            p[0] = ('return', None, p.lineno(1))
        else:
            p[0] = ('return', p[2], p.lineno(1))

    def p_break_stmt(p):
        '''break_stmt : BREAK SEMICOLON'''
        p[0] = ('break', p.lineno(1))

    def p_continue_stmt(p):
        '''continue_stmt : CONTINUE SEMICOLON'''
        p[0] = ('continue', p.lineno(1))

    # ════════════════════════════════════════════
    #  Expressions
    # ════════════════════════════════════════════

    def p_expression_assign(p):
        '''expression : ID EQUALS expression
                      | ID PLUS_ASSIGN expression
                      | ID MINUS_ASSIGN expression
                      | ID TIMES_ASSIGN expression
                      | ID DIVIDE_ASSIGN expression
                      | ID MODULO_ASSIGN expression
                      | ID LBRACKET expression RBRACKET EQUALS expression'''
        if len(p) == 4:
            p[0] = ('assign', p[1], p[2], p[3], p.lineno(1))
        else:
            p[0] = ('array_assign', p[1], p[3], p[6], p.lineno(1))

    def p_expression_ternary(p):
        '''expression : expression QUESTION expression COLON expression'''
        p[0] = ('ternary', p[1], p[3], p[5], p.lineno(2))

    def p_expression_binop(p):
        '''expression : expression PLUS expression
                      | expression MINUS expression
                      | expression TIMES expression
                      | expression DIVIDE expression
                      | expression MODULO expression
                      | expression EQ expression
                      | expression NEQ expression
                      | expression LT expression
                      | expression GT expression
                      | expression LTE expression
                      | expression GTE expression
                      | expression AND expression
                      | expression OR expression
                      | expression BIT_AND expression
                      | expression BIT_OR expression
                      | expression BIT_XOR expression
                      | expression LSHIFT expression
                      | expression RSHIFT expression'''
        p[0] = ('binop', p[2], p[1], p[3], p.lineno(2))

    def p_expression_unary(p):
        '''expression : NOT expression
                      | BIT_NOT expression
                      | MINUS expression %prec UMINUS
                      | PLUS expression %prec UPLUS'''
        p[0] = ('unary', p[1], p[2], p.lineno(1))

    def p_expression_increment(p):
        '''expression : ID INCREMENT
                      | ID DECREMENT
                      | INCREMENT ID
                      | DECREMENT ID'''
        if p[1] in ('++', '--'):
            p[0] = ('pre_inc', p[1], p[2], p.lineno(1))
        else:
            p[0] = ('post_inc', p[2], p[1], p.lineno(1))

    def p_expression_group(p):
        '''expression : LPAREN expression RPAREN'''
        p[0] = p[2]

    def p_expression_call(p):
        '''expression : ID LPAREN args RPAREN'''
        p[0] = ('call', p[1], p[3], p.lineno(1))

    def p_expression_array_access(p):
        '''expression : ID LBRACKET expression RBRACKET'''
        p[0] = ('array_access', p[1], p[3], p.lineno(1))

    def p_expression_sizeof(p):
        '''expression : SIZEOF LPAREN type_spec RPAREN
                      | SIZEOF LPAREN expression RPAREN'''
        p[0] = ('sizeof', p[3], p.lineno(1))

    def p_expression_cast(p):
        '''expression : LPAREN type_spec RPAREN expression %prec UMINUS'''
        p[0] = ('cast', p[2], p[4], p.lineno(1))

    def p_expression_id(p):
        '''expression : ID'''
        p[0] = ('id', p[1], p.lineno(1))

    def p_expression_num_int(p):
        '''expression : NUMBER_INT'''
        p[0] = ('num_int', p[1], p.lineno(1))

    def p_expression_num_float(p):
        '''expression : NUMBER_FLOAT'''
        p[0] = ('num_float', p[1], p.lineno(1))

    def p_expression_string(p):
        '''expression : STRING_LITERAL'''
        p[0] = ('string', p[1], p.lineno(1))

    def p_expression_char(p):
        '''expression : CHAR_LITERAL'''
        p[0] = ('char_lit', p[1], p.lineno(1))

    def p_expression_true(p):
        '''expression : TRUE'''
        p[0] = ('num_int', 1, p.lineno(1))

    def p_expression_false(p):
        '''expression : FALSE'''
        p[0] = ('num_int', 0, p.lineno(1))

    def p_expression_null(p):
        '''expression : NULL_KW'''
        p[0] = ('num_int', 0, p.lineno(1))

    # ── C++ stream expressions: cout << ... and cin >> ... ──
    def p_expression_stream_out(p):
        '''expression : ID LSHIFT expression'''
        # Already handled by binop LSHIFT, but specifically for cout
        p[0] = ('binop', '<<', ('id', p[1], p.lineno(1)), p[3], p.lineno(1))

    # ── Function call arguments ──

    def p_args(p):
        '''args : arg_list
                | empty'''
        if p[1] is None:
            p[0] = []
        else:
            p[0] = p[1]

    def p_arg_list(p):
        '''arg_list : arg_list COMMA expression
                    | expression'''
        if len(p) == 4:
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1]]

    # ── Empty production ──

    def p_empty(p):
        '''empty :'''
        p[0] = None

    # ════════════════════════════════════════════
    #  Error recovery
    # ════════════════════════════════════════════

    def p_error(p):
        if p:
            # Try to give specific messages
            if p.type == 'RBRACE':
                error_collector.add_error(
                    "Syntax",
                    f"Unexpected '}}' — possible missing statement or extra closing brace",
                    p.lineno,
                )
            elif p.type == 'LBRACE':
                error_collector.add_error(
                    "Syntax",
                    f"Unexpected '{{' — possible missing ')' or ';' before block",
                    p.lineno,
                )
            elif p.type in ('INT', 'FLOAT', 'DOUBLE', 'CHAR', 'VOID', 'LONG', 'SHORT', 'STRING_TYPE', 'BOOL'):
                error_collector.add_error(
                    "Syntax",
                    f"Unexpected type keyword '{p.value}' — possible missing ';' on previous line",
                    p.lineno,
                    suggestion="Add ';' at the end of the previous statement"
                )
            elif p.type == 'ID':
                error_collector.add_error(
                    "Syntax",
                    f"Unexpected identifier '{p.value}'",
                    p.lineno,
                    suggestion="Check for missing operators, semicolons, or misplaced identifiers"
                )
            else:
                error_collector.add_error(
                    "Syntax",
                    f"Unexpected token '{p.value}' ({p.type})",
                    p.lineno,
                )
            # Panic-mode recovery: skip to next ; or }
            while True:
                tok = parser.token()
                if not tok:
                    break
                if tok.type in ('SEMICOLON', 'RBRACE'):
                    break
            parser.restart()
        else:
            # End of input errors
            error_collector.add_error(
                "Syntax",
                "Unexpected end of input — possible missing '}' or ';'",
                None,
                suggestion="Check for unclosed braces or missing semicolons at the end of the file"
            )

    # ── Missing semicolon recovery rules ──

    def p_var_declaration_missing_semi(p):
        '''var_declaration : type_spec ID EQUALS expression error'''
        error_collector.add_error(
            "Syntax",
            f"Missing ';' after variable declaration of '{p[2]}'",
            p.lineno(2),
            suggestion="Add ';' at the end of the declaration"
        )
        p[0] = ('var_decl_init', p[1], p[2], p[4], p.lineno(2))

    def p_var_declaration_missing_semi2(p):
        '''var_declaration : type_spec ID error'''
        error_collector.add_error(
            "Syntax",
            f"Missing ';' after declaration of '{p[2]}'",
            p.lineno(2),
            suggestion="Add ';' at the end of the declaration"
        )
        p[0] = ('var_decl', p[1], p[2], None, p.lineno(2))

    parser = yacc.yacc(debug=False, write_tables=False)
    return parser


def parse(source_code, error_collector):
    """
    Parse source code and return the AST.

    Args:
        source_code: Preprocessed C source code string.
        error_collector: ErrorCollector instance.

    Returns:
        tuple: AST root node, or None on critical failure.
    """
    lexer = build_lexer(error_collector)
    parser = build_parser(error_collector)

    try:
        ast = parser.parse(source_code, lexer=lexer, tracking=True)
    except Exception as e:
        error_collector.add_error("Syntax", f"Critical parse error: {str(e)}", None)
        ast = None

    return ast
