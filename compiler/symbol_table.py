"""
CodeLens-C — Phase 4: Symbol Table
Manages identifier storage with scope support.
"""


class SymbolTable:
    """
    Symbol table with lexical scoping support.
    Uses a stack of scope dictionaries.
    """

    def __init__(self):
        # Stack of scopes — each scope is a dict of {name: symbol_info}
        self._scopes = [{}]  # start with global scope
        self._scope_names = ["global"]
        self._all_symbols = []  # flat list for export
        self._scope_counter = 0

    @property
    def current_scope_name(self):
        return self._scope_names[-1]

    def enter_scope(self, name=None):
        """Push a new scope onto the stack."""
        if name is None:
            self._scope_counter += 1
            name = f"block_{self._scope_counter}"
        self._scopes.append({})
        self._scope_names.append(name)

    def exit_scope(self):
        """Pop the current scope from the stack."""
        if len(self._scopes) > 1:
            self._scopes.pop()
            self._scope_names.pop()

    def declare(self, name, var_type, line, kind="variable", params=None,
                return_type=None, is_array=False, array_size=None):
        """
        Declare a symbol in the current scope.

        Returns:
            (bool, str): (success, error_message)
        """
        current = self._scopes[-1]
        if name in current:
            existing = current[name]
            return False, (
                f"'{name}' already declared in scope '{self.current_scope_name}' "
                f"(first declared at line {existing['line']})"
            )

        symbol = {
            "name": name,
            "type": var_type,
            "scope": self.current_scope_name,
            "line": line,
            "kind": kind,
            "params": params or [],
            "return_type": return_type,
            "is_array": is_array,
            "array_size": array_size,
        }
        current[name] = symbol
        self._all_symbols.append(symbol)
        return True, None

    def lookup(self, name):
        """
        Look up a symbol by name, searching from innermost to outermost scope.

        Returns:
            dict or None: Symbol info dict, or None if not found.
        """
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_current_scope(self, name):
        """Look up a symbol only in the current scope."""
        return self._scopes[-1].get(name)

    def get_all_symbols(self):
        """Return all symbols as a flat list for export."""
        return list(self._all_symbols)

    def to_json(self):
        """Return symbol table as JSON-serializable list."""
        return [
            {
                "name": s["name"],
                "type": s["type"],
                "scope": s["scope"],
                "line": s["line"],
                "kind": s["kind"],
                "params": [(p[0], p[1]) for p in s["params"]] if s["params"] else [],
                "return_type": s.get("return_type"),
                "is_array": s.get("is_array", False),
            }
            for s in self._all_symbols
        ]


def create_symbol_table():
    """Create a new symbol table pre-loaded with standard library declarations."""
    st = SymbolTable()

    # ── Auto-declare standard C library functions ──
    stdlib_functions = [
        # stdio.h
        ("printf",  "int",  [("char*", "format")],              "int"),
        ("scanf",   "int",  [("char*", "format")],              "int"),
        ("fprintf", "int",  [("void*", "stream"), ("char*", "format")], "int"),
        ("sprintf", "int",  [("char*", "str"), ("char*", "format")],    "int"),
        ("puts",    "int",  [("char*", "str")],                 "int"),
        ("gets",    "char*",[("char*", "str")],                  "char*"),
        ("getchar", "int",  [],                                   "int"),
        ("putchar", "int",  [("int", "ch")],                     "int"),
        ("fopen",   "void*",[("char*", "filename"), ("char*", "mode")], "void*"),
        ("fclose",  "int",  [("void*", "stream")],              "int"),

        # stdlib.h
        ("malloc",  "void*",[("int", "size")],                   "void*"),
        ("calloc",  "void*",[("int", "num"), ("int", "size")],  "void*"),
        ("realloc", "void*",[("void*", "ptr"), ("int", "size")],"void*"),
        ("free",    "void", [("void*", "ptr")],                  "void"),
        ("exit",    "void", [("int", "status")],                 "void"),
        ("atoi",    "int",  [("char*", "str")],                  "int"),
        ("atof",    "double",[("char*", "str")],                 "double"),
        ("abs",     "int",  [("int", "x")],                      "int"),
        ("rand",    "int",  [],                                   "int"),
        ("srand",   "void", [("int", "seed")],                   "void"),

        # string.h
        ("strlen",  "int",  [("char*", "str")],                  "int"),
        ("strcpy",  "char*",[("char*", "dest"), ("char*", "src")],"char*"),
        ("strncpy", "char*",[("char*", "dest"), ("char*", "src"), ("int", "n")], "char*"),
        ("strcmp",  "int",  [("char*", "s1"), ("char*", "s2")], "int"),
        ("strcat",  "char*",[("char*", "dest"), ("char*", "src")],"char*"),
        ("memset",  "void*",[("void*", "ptr"), ("int", "val"), ("int", "size")], "void*"),
        ("memcpy",  "void*",[("void*", "dest"), ("void*", "src"), ("int", "n")], "void*"),

        # math.h
        ("sqrt",    "double",[("double", "x")],                  "double"),
        ("pow",     "double",[("double", "base"), ("double", "exp")], "double"),
        ("sin",     "double",[("double", "x")],                  "double"),
        ("cos",     "double",[("double", "x")],                  "double"),
        ("tan",     "double",[("double", "x")],                  "double"),
        ("log",     "double",[("double", "x")],                  "double"),
        ("ceil",    "double",[("double", "x")],                  "double"),
        ("floor",   "double",[("double", "x")],                  "double"),

        # C++ <string> and utilities
        ("getline", "void",  [("void*", "stream"), ("string", "str")], "void"),
        ("to_string","string",[("int", "val")],                  "string"),
        ("stoi",    "int",   [("string", "str")],                "int"),
        ("stof",    "float", [("string", "str")],                "float"),
        ("stod",    "double",[("string", "str")],                "double"),
    ]

    for name, ret_type, params, return_type in stdlib_functions:
        st.declare(
            name=name,
            var_type="function",
            line=0,
            kind="function",
            params=params,
            return_type=return_type,
        )

    # ── Auto-declare C++ iostream objects ──
    cpp_objects = [
        ("cout",  "void*"),
        ("cin",   "void*"),
        ("cerr",  "void*"),
        ("endl",  "char*"),
    ]
    for name, obj_type in cpp_objects:
        st.declare(
            name=name,
            var_type=obj_type,
            line=0,
            kind="variable",
        )

    return st
