"""
Preprocessing Module
Handles removal of comments and preprocessor directives
"""
import re


class Preprocessor:
    """Preprocessor for C/C++ code"""
    
    def __init__(self):
        self.preprocessed_code = ""
    
    def _blank_removed_line(self, line):
        """Keep line endings but blank out content"""
        if line.endswith('\r\n'):
            return '\r\n'
        if line.endswith('\n'):
            return '\n'
        return ''
    
    def _mask_removed_text(self, text):
        """Replace text with spaces but preserve newlines"""
        return ''.join(char if char in '\r\n' else ' ' for char in text)
    
    def _remove_preprocessor_directives(self, code):
        """Remove preprocessor directives while preserving line numbers"""
        lines = code.splitlines(keepends=True)
        processed_lines = []
        index = 0

        while index < len(lines):
            line = lines[index]

            # Check if line starts with preprocessor directive
            if re.match(r'^[ \t]*#', line):
                directive_lines = [line]

                # Handle multi-line directives (ending with \)
                while line.rstrip('\r\n').endswith('\\') and index + 1 < len(lines):
                    index += 1
                    line = lines[index]
                    directive_lines.append(line)
                
                # Blank out all directive lines
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
        """
        Main preprocessing function
        Removes comments and preprocessor directives while preserving line numbers
        """
        preprocessed = code
        
        # Remove multi-line comments /* ... */
        multi_comment_pattern = r'/\*[\s\S]*?\*/'
        preprocessed = re.sub(
            multi_comment_pattern,
            lambda match: self._mask_removed_text(match.group(0)),
            preprocessed
        )
        
        # Remove single-line comments // ...
        single_comment_pattern = r'//.*'
        preprocessed = re.sub(
            single_comment_pattern,
            lambda match: self._mask_removed_text(match.group(0)),
            preprocessed
        )

        # Remove preprocessor directives
        preprocessed = self._remove_preprocessor_directives(preprocessed)
        
        self.preprocessed_code = preprocessed
        return preprocessed
    
    def get_preprocessed_code(self):
        """Get the preprocessed code"""
        return self.preprocessed_code