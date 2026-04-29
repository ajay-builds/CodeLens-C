"""
CodeLens-C — Phase 1: Preprocessor
Removes comments and preprocessor directives while preserving line numbers.
"""

import re


def preprocess(source_code, error_collector):
    # Returns:str: Cleaned source code with comments and directives removed.
    lines = source_code.split('\n')
    cleaned_lines = list(lines)  # work on a copy
    messages = []

    # ── Pass 1: Remove multi-line comments /* ... */ ──
    in_block_comment = False
    block_start_line = 0
    for i in range(len(cleaned_lines)):
        line = cleaned_lines[i]
        new_line = ""
        j = 0
        while j < len(line):
            if in_block_comment:
                if j + 1 < len(line) and line[j] == '*' and line[j + 1] == '/':
                    in_block_comment = False
                    j += 2
                    # keep the rest of the line after the comment ends
                    new_line += line[j:]
                    break
                else:
                    j += 1
            else:
                # Check for string literals — don't strip comments inside strings
                if line[j] == '"':
                    # copy the entire string literal
                    new_line += line[j]
                    j += 1
                    while j < len(line) and line[j] != '"':
                        if line[j] == '\\' and j + 1 < len(line):
                            new_line += line[j:j+2]
                            j += 2
                        else:
                            new_line += line[j]
                            j += 1
                    if j < len(line):
                        new_line += line[j]  # closing quote
                        j += 1
                elif line[j] == "'" :
                    new_line += line[j]
                    j += 1
                    while j < len(line) and line[j] != "'":
                        if line[j] == '\\' and j + 1 < len(line):
                            new_line += line[j:j+2]
                            j += 2
                        else:
                            new_line += line[j]
                            j += 1
                    if j < len(line):
                        new_line += line[j]
                        j += 1
                elif j + 1 < len(line) and line[j] == '/' and line[j + 1] == '*':
                    in_block_comment = True
                    block_start_line = i + 1
                    messages.append(f"Removed block comment starting at line {block_start_line}")
                    j += 2
                elif j + 1 < len(line) and line[j] == '/' and line[j + 1] == '/':
                    # single-line comment — discard the rest of the line
                    messages.append(f"Removed single-line comment at line {i + 1}")
                    break
                else:
                    new_line += line[j]
                    j += 1
        cleaned_lines[i] = new_line

    if in_block_comment:
        error_collector.add_warning(
            "Preprocessing",
            f"Unterminated block comment starting at line {block_start_line}",
            block_start_line
        )

    # ── Pass 2: Remove preprocessor directives ──
    i = 0
    while i < len(cleaned_lines):
        stripped = cleaned_lines[i].lstrip()
        if stripped.startswith('#'):
            directive = stripped.split()[0] if stripped.split() else '#'
            messages.append(
                f"Removed preprocessor directive '{directive}' at line {i + 1}"
            )
            # Handle multi-line directives (ending with \)
            while cleaned_lines[i].rstrip().endswith('\\') and i + 1 < len(cleaned_lines):
                cleaned_lines[i] = ""
                i += 1
            cleaned_lines[i] = ""
        i += 1

    # Log info messages
    for msg in messages:
        error_collector.add_info("Preprocessing", msg)

    return '\n'.join(cleaned_lines)
