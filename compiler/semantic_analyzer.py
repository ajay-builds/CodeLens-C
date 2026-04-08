"""
CodeLens-C — Phase 5: Semantic Analyzer
Walks the AST and performs type checking, scope resolution,
declaration checks, and function validation.
"""


# ──────────────────────────────────────────────
#  Type compatibility
# ──────────────────────────────────────────────

NUMERIC_TYPES = {'int', 'float', 'double', 'char', 'short', 'long', 'unsigned', 'signed', 'bool'}
STRING_TYPES = {'char*', 'string'}

# Types that can be implicitly promoted to each other
PROMOTION_ORDER = {'bool': 0, 'char': 1, 'short': 2, 'int': 3, 'unsigned': 4, 'long': 5, 'float': 6, 'double': 7}


def _is_numeric(t):
    return t in NUMERIC_TYPES


def _is_string(t):
    return t in STRING_TYPES


def _types_compatible(left, right):
    """Check if two types are compatible for binary operations."""
    if left == right:
        return True, left
    if _is_numeric(left) and _is_numeric(right):
        # Promote to the wider type
        l_order = PROMOTION_ORDER.get(left, 2)
        r_order = PROMOTION_ORDER.get(right, 2)
        result_type = left if l_order >= r_order else right
        return True, result_type
    if _is_string(left) and _is_string(right):
        return True, 'char*'
    return False, None


def _type_assignable(target_type, value_type):
    """Check if value_type can be assigned to target_type."""
    if target_type == value_type:
        return True
    if _is_numeric(target_type) and _is_numeric(value_type):
        return True
    if target_type in ('void*',) and value_type in NUMERIC_TYPES | {'void*'}:
        return True
    if _is_string(target_type) and _is_string(value_type):
        return True
    # string type can be initialized with a string literal (char*)
    if target_type == 'string' and value_type == 'char*':
        return True
    if target_type == 'char*' and value_type == 'string':
        return True
    return False


# ──────────────────────────────────────────────
#  Printf / Scanf format checking
# ──────────────────────────────────────────────

FORMAT_SPECIFIERS = {
    '%d': 'int', '%i': 'int', '%u': 'unsigned',
    '%f': 'float', '%lf': 'double',
    '%c': 'char', '%s': 'char*',
    '%x': 'int', '%X': 'int', '%o': 'int',
    '%p': 'void*', '%ld': 'long', '%lu': 'unsigned',
    '%lld': 'long', '%llu': 'unsigned',
}

import re

def _count_format_specifiers(fmt_string):
    """Count format specifiers in a printf/scanf format string."""
    pattern = r'%(?:\d+\$)?[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|h|l|ll|L|z|j|t)?[diouxXeEfFgGaAcspn%]'
    matches = re.findall(pattern, fmt_string)
    # Exclude %% (literal percent)
    return [m for m in matches if m != '%%']


# ──────────────────────────────────────────────
#  Semantic Analyzer
# ──────────────────────────────────────────────

class SemanticAnalyzer:
    """Walk the AST and perform semantic checks."""

    def __init__(self, symbol_table, error_collector):
        self.st = symbol_table
        self.ec = error_collector
        self._current_function = None      # name of function being analyzed
        self._current_return_type = None   # return type of current function
        self._has_main = False

    def analyze(self, ast):
        """Entry point: analyze the full program AST."""
        if ast is None:
            return

        node_type = ast[0] if isinstance(ast, tuple) else None

        if node_type == 'program':
            for decl in ast[1]:
                self._analyze_node(decl)
        else:
            self._analyze_node(ast)

        # ── Check for main() entry point ──
        if not self._has_main:
            self.ec.add_warning(
                "Semantic",
                "No 'main()' function found — program has no entry point",
                None,
                suggestion="Add a 'main()' function as the program entry point"
            )

    def _analyze_node(self, node):
        """Dispatch analysis based on node type."""
        if node is None or not isinstance(node, tuple):
            return None

        node_type = node[0]

        dispatch = {
            'var_decl': self._analyze_var_decl,
            'var_decl_init': self._analyze_var_decl_init,
            'multi_var_decl_init': self._analyze_multi_var_decl_init,
            'array_decl': self._analyze_array_decl,
            'fun_decl': self._analyze_fun_decl,
            'compound': self._analyze_compound,
            'if': self._analyze_if,
            'if_else': self._analyze_if_else,
            'while': self._analyze_while,
            'for': self._analyze_for,
            'do_while': self._analyze_do_while,
            'return': self._analyze_return,
            'expr_stmt': self._analyze_expr_stmt,
            'assign': self._analyze_assign,
            'array_assign': self._analyze_array_assign,
            'binop': self._analyze_binop,
            'unary': self._analyze_unary,
            'call': self._analyze_call,
            'id': self._analyze_id,
            'num_int': self._analyze_num_int,
            'num_float': self._analyze_num_float,
            'string': self._analyze_string,
            'char_lit': self._analyze_char_lit,
            'array_access': self._analyze_array_access,
            'pre_inc': self._analyze_inc,
            'post_inc': self._analyze_inc,
            'cast': self._analyze_cast,
            'sizeof': self._analyze_sizeof,
            'ternary': self._analyze_ternary,
            'using_namespace': self._analyze_using_namespace,
        }

        handler = dispatch.get(node_type)
        if handler:
            return handler(node)

        # For unknown node types, try to recurse into children
        for child in node[1:]:
            if isinstance(child, tuple):
                self._analyze_node(child)
            elif isinstance(child, list):
                for item in child:
                    self._analyze_node(item)

        return None

    # ── Declarations ──

    def _analyze_using_namespace(self, node):
        """Handle 'using namespace std;' — accepted silently."""
        # No semantic action needed; just acknowledge it
        return None

    def _analyze_var_decl(self, node):
        _, var_type, name, _, line = node
        ok, msg = self.st.declare(name, var_type, line, kind="variable")
        if not ok:
            self.ec.add_error("Semantic", f"Duplicate declaration: {msg}", line)
        return var_type

    def _analyze_var_decl_init(self, node):
        _, var_type, name, init_expr, line = node
        ok, msg = self.st.declare(name, var_type, line, kind="variable")
        if not ok:
            self.ec.add_error("Semantic", f"Duplicate declaration: {msg}", line)

        # Check initializer type
        init_type = self._analyze_node(init_expr)
        if init_type and not _type_assignable(var_type, init_type):
            # Specific message for char vs string mismatch
            if var_type == 'char' and _is_string(init_type):
                self.ec.add_error(
                    "Semantic",
                    f"Cannot assign a string to 'char {name}' — "
                    f"a char holds only one character",
                    line,
                    suggestion=f"Use single quotes for a character literal, e.g. '{name} = \'a\''"
                )
            else:
                self.ec.add_error(
                    "Semantic",
                    f"Type mismatch: cannot initialize '{var_type} {name}' with value of type '{init_type}'",
                    line
                )
        return var_type

    def _analyze_multi_var_decl_init(self, node):
        """Handle: int a, b = 5, c = 10;  (comma-separated with optional init)"""
        _, var_type, items, line = node
        for item in items:
            # Each item is ('init_item', name, init_expr_or_None)
            _, name, init_expr = item
            ok, msg = self.st.declare(name, var_type, line, kind="variable")
            if not ok:
                self.ec.add_error("Semantic", f"Duplicate declaration: {msg}", line)
            # Check initializer type if present
            if init_expr is not None:
                init_type = self._analyze_node(init_expr)
                if init_type and not _type_assignable(var_type, init_type):
                    if var_type == 'char' and _is_string(init_type):
                        self.ec.add_error(
                            "Semantic",
                            f"Cannot assign a string to 'char {name}' — "
                            f"a char holds only one character",
                            line,
                            suggestion=f"Use single quotes for a character literal, e.g. '{name} = \'a\''"
                        )
                    else:
                        self.ec.add_error(
                            "Semantic",
                            f"Type mismatch: cannot initialize '{var_type} {name}' with value of type '{init_type}'",
                            line
                        )
        return var_type

    def _analyze_array_decl(self, node):
        _, var_type, name, size_expr, line = node
        ok, msg = self.st.declare(name, var_type, line, kind="variable", is_array=True)
        if not ok:
            self.ec.add_error("Semantic", f"Duplicate declaration: {msg}", line)
        if size_expr:
            self._analyze_node(size_expr)
        return var_type

    def _analyze_fun_decl(self, node):
        _, ret_type, name, params, body, line = node

        if name == 'main':
            self._has_main = True

        # Build param list
        param_types = []
        for p in params:
            if isinstance(p, tuple) and p[0] == 'param':
                param_types.append((p[1], p[2]))

        # Declare the function in current scope
        ok, msg = self.st.declare(
            name, "function", line,
            kind="function",
            params=param_types,
            return_type=ret_type,
        )
        if not ok:
            self.ec.add_error("Semantic", f"Duplicate declaration: {msg}", line)

        # Enter function scope
        prev_func = self._current_function
        prev_ret = self._current_return_type
        self._current_function = name
        self._current_return_type = ret_type

        self.st.enter_scope(name)

        # Declare parameters in function scope
        for p in params:
            if isinstance(p, tuple) and p[0] == 'param':
                _, p_type, p_name, is_arr, p_line = p
                self.st.declare(p_name, p_type, p_line, kind="parameter", is_array=is_arr)

        # Analyze body (but don't create another scope since compound will)
        if body and body[0] == 'compound':
            # Analyze local decls and statements directly
            _, local_decls, stmts, _ = body
            for decl in local_decls:
                self._analyze_node(decl)
            for stmt in stmts:
                self._analyze_node(stmt)
        else:
            self._analyze_node(body)

        self.st.exit_scope()
        self._current_function = prev_func
        self._current_return_type = prev_ret
        return ret_type

    # ── Compound statement (block) ──

    def _analyze_compound(self, node):
        _, local_decls, stmts, line = node
        self.st.enter_scope()
        for decl in local_decls:
            self._analyze_node(decl)
        for stmt in stmts:
            self._analyze_node(stmt)
        self.st.exit_scope()

    # ── Control flow ──

    def _analyze_if(self, node):
        _, cond, then_stmt, _, line = node
        self._analyze_node(cond)
        self._analyze_node(then_stmt)

    def _analyze_if_else(self, node):
        _, cond, then_stmt, else_stmt, line = node
        self._analyze_node(cond)
        self._analyze_node(then_stmt)
        self._analyze_node(else_stmt)

    def _analyze_while(self, node):
        _, cond, body, line = node
        self._analyze_node(cond)
        self._analyze_node(body)

    def _analyze_for(self, node):
        _, init, cond, update, body, line = node
        self.st.enter_scope()
        self._analyze_node(init)
        self._analyze_node(cond)
        self._analyze_node(update)
        self._analyze_node(body)
        self.st.exit_scope()

    def _analyze_do_while(self, node):
        _, cond, body, line = node
        self._analyze_node(body)
        self._analyze_node(cond)

    # ── Return ──

    def _analyze_return(self, node):
        _, expr, line = node
        if expr is None:
            if self._current_return_type and self._current_return_type != 'void':
                self.ec.add_error(
                    "Semantic",
                    f"Missing return value in function '{self._current_function}' "
                    f"(expected '{self._current_return_type}')",
                    line
                )
            return 'void'

        ret_type = self._analyze_node(expr)
        if ret_type and self._current_return_type:
            if self._current_return_type == 'void':
                self.ec.add_error(
                    "Semantic",
                    f"Function '{self._current_function}' declared void but returns a value",
                    line
                )
            elif not _type_assignable(self._current_return_type, ret_type):
                self.ec.add_error(
                    "Semantic",
                    f"Return type mismatch in '{self._current_function}': "
                    f"expected '{self._current_return_type}', got '{ret_type}'",
                    line
                )
        return ret_type

    def _analyze_expr_stmt(self, node):
        _, expr, line = node
        return self._analyze_node(expr)

    # ── Assignment ──

    def _analyze_assign(self, node):
        _, name, op, expr, line = node
        sym = self.st.lookup(name)
        if sym is None:
            self.ec.add_error(
                "Semantic",
                f"Variable '{name}' used before declaration",
                line,
                suggestion=f"Declare '{name}' before using it"
            )
            return None

        expr_type = self._analyze_node(expr)
        var_type = sym['type']

        if expr_type and not _type_assignable(var_type, expr_type):
            # Specific message for char vs string mismatch
            if var_type == 'char' and _is_string(expr_type):
                self.ec.add_error(
                    "Semantic",
                    f"Cannot assign a string to 'char {name}' — "
                    f"a char holds only one character",
                    line,
                    suggestion=f"Use single quotes for a character literal, e.g. '{name} = \'a\''"
                )
            else:
                self.ec.add_error(
                    "Semantic",
                    f"Type mismatch: cannot assign '{expr_type}' to '{var_type} {name}'",
                    line
                )
        return var_type

    def _analyze_array_assign(self, node):
        _, name, index, expr, line = node
        sym = self.st.lookup(name)
        if sym is None:
            self.ec.add_error("Semantic", f"Variable '{name}' used before declaration", line)
            return None
        self._analyze_node(index)
        self._analyze_node(expr)
        return sym['type']

    # ── Binary operations ──

    def _analyze_binop(self, node):
        _, op, left, right, line = node
        left_type = self._analyze_node(left)
        right_type = self._analyze_node(right)

        if left_type is None or right_type is None:
            return None

        compatible, result_type = _types_compatible(left_type, right_type)
        if not compatible:
            self.ec.add_error(
                "Semantic",
                f"Type mismatch: cannot apply '{op}' to '{left_type}' and '{right_type}'",
                line
            )
            return None

        # Comparison operators return int (boolean)
        if op in ('==', '!=', '<', '>', '<=', '>=', '&&', '||'):
            return 'int'

        return result_type

    def _analyze_unary(self, node):
        _, op, expr, line = node
        expr_type = self._analyze_node(expr)
        if op == '!' :
            return 'int'
        return expr_type

    def _analyze_inc(self, node):
        # pre_inc or post_inc
        _, op, name, line = node
        sym = self.st.lookup(name)
        if sym is None:
            self.ec.add_error("Semantic", f"Variable '{name}' used before declaration", line)
            return None
        if not _is_numeric(sym['type']):
            self.ec.add_error(
                "Semantic",
                f"Cannot apply '{op}' to non-numeric type '{sym['type']}'",
                line
            )
        return sym['type']

    # ── Function calls ──

    def _analyze_call(self, node):
        _, name, args, line = node

        sym = self.st.lookup(name)
        if sym is None:
            self.ec.add_error(
                "Semantic",
                f"Function '{name}' called but not declared",
                line,
                suggestion=f"Declare function '{name}' before calling it"
            )
            # Still analyze arguments
            for arg in args:
                self._analyze_node(arg)
            return None

        if sym['kind'] != 'function':
            self.ec.add_error(
                "Semantic",
                f"'{name}' is not a function (declared as '{sym['type']}')",
                line
            )
            return None

        # ── Special handling for printf/scanf ──
        if name in ('printf', 'sprintf', 'fprintf'):
            return self._check_printf_call(name, args, sym, line)
        if name in ('scanf',):
            return self._check_scanf_call(name, args, sym, line)

        # ── General function: check argument count ──
        expected_params = sym.get('params', [])
        if len(args) != len(expected_params):
            self.ec.add_error(
                "Semantic",
                f"Function '{name}' expects {len(expected_params)} argument(s), "
                f"but {len(args)} provided",
                line
            )
        else:
            # Check argument types
            for i, (arg, param) in enumerate(zip(args, expected_params)):
                arg_type = self._analyze_node(arg)
                param_type = param[0] if isinstance(param, (list, tuple)) else param
                if arg_type and not _type_assignable(param_type, arg_type):
                    param_name = param[1] if isinstance(param, (list, tuple)) and len(param) > 1 else f"arg{i+1}"
                    self.ec.add_error(
                        "Semantic",
                        f"Argument type mismatch in call to '{name}': "
                        f"parameter '{param_name}' expects '{param_type}', got '{arg_type}'",
                        line
                    )

        return sym.get('return_type', 'int')

    def _check_printf_call(self, name, args, sym, line):
        """Special validation for printf-family functions."""
        if len(args) == 0:
            self.ec.add_error(
                "Semantic",
                f"Function '{name}' requires at least a format string argument",
                line
            )
            return 'int'

        # Analyze first argument (format string)
        fmt_arg = args[0]
        fmt_type = self._analyze_node(fmt_arg)

        if fmt_arg[0] == 'string':
            fmt_string = fmt_arg[1]
            specifiers = _count_format_specifiers(fmt_string)
            extra_args = args[1:]

            # Analyze all extra arguments
            arg_types = []
            for arg in extra_args:
                t = self._analyze_node(arg)
                arg_types.append(t)

            if len(specifiers) != len(extra_args):
                self.ec.add_error(
                    "Semantic",
                    f"'{name}' format string has {len(specifiers)} specifier(s) "
                    f"but {len(extra_args)} argument(s) provided",
                    line
                )
        else:
            # Format string is not a literal — just analyze args
            for arg in args[1:]:
                self._analyze_node(arg)

        return 'int'

    def _check_scanf_call(self, name, args, sym, line):
        """Special validation for scanf."""
        if len(args) == 0:
            self.ec.add_error(
                "Semantic",
                f"Function '{name}' requires at least a format string argument",
                line
            )
            return 'int'

        fmt_arg = args[0]
        self._analyze_node(fmt_arg)

        if fmt_arg[0] == 'string':
            fmt_string = fmt_arg[1]
            specifiers = _count_format_specifiers(fmt_string)
            extra_args = args[1:]

            for arg in extra_args:
                self._analyze_node(arg)

            if len(specifiers) != len(extra_args):
                self.ec.add_error(
                    "Semantic",
                    f"'{name}' format string has {len(specifiers)} specifier(s) "
                    f"but {len(extra_args)} argument(s) provided",
                    line
                )
        else:
            for arg in args[1:]:
                self._analyze_node(arg)

        return 'int'

    # ── Leaves ──

    def _analyze_id(self, node):
        _, name, line = node
        sym = self.st.lookup(name)
        if sym is None:
            self.ec.add_error(
                "Semantic",
                f"Variable '{name}' used before declaration",
                line,
                suggestion=f"Declare '{name}' before using it"
            )
            return None
        return sym['type']

    def _analyze_num_int(self, node):
        return 'int'

    def _analyze_num_float(self, node):
        return 'float'

    def _analyze_string(self, node):
        return 'char*'

    def _analyze_char_lit(self, node):
        return 'char'

    def _analyze_array_access(self, node):
        _, name, index, line = node
        sym = self.st.lookup(name)
        if sym is None:
            self.ec.add_error("Semantic", f"Variable '{name}' used before declaration", line)
            return None
        self._analyze_node(index)
        return sym['type']

    def _analyze_cast(self, node):
        _, target_type, expr, line = node
        self._analyze_node(expr)
        return target_type

    def _analyze_sizeof(self, node):
        return 'int'

    def _analyze_ternary(self, node):
        _, cond, then_expr, else_expr, line = node
        self._analyze_node(cond)
        t1 = self._analyze_node(then_expr)
        t2 = self._analyze_node(else_expr)
        if t1 and t2:
            compatible, result = _types_compatible(t1, t2)
            if not compatible:
                self.ec.add_error(
                    "Semantic",
                    f"Type mismatch in ternary expression: '{t1}' vs '{t2}'",
                    line
                )
            return result
        return t1 or t2


def analyze_semantics(ast, symbol_table, error_collector):
    """
    Run semantic analysis on the AST.

    Args:
        ast: The AST from the parser.
        symbol_table: SymbolTable instance (pre-loaded with stdlib).
        error_collector: ErrorCollector instance.
    """
    analyzer = SemanticAnalyzer(symbol_table, error_collector)
    analyzer.analyze(ast)
