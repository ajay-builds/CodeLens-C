"""
CodeLens-C — Phase 6: Centralized Error Collector
Collects errors, warnings, and info messages from all compiler phases.
"""


class ErrorCollector:
    """Centralized store for all compilation errors, warnings, and info messages."""

    def __init__(self):
        self._errors = []

    def add_error(self, phase, message, line=None, suggestion=None):
        """Add an error from a specific compiler phase."""
        entry = {
            "phase": phase,
            "type": "error",
            "line": line,
            "message": message,
        }
        if suggestion:
            entry["suggestion"] = suggestion
        self._errors.append(entry)

    def add_warning(self, phase, message, line=None, suggestion=None):
        """Add a warning from a specific compiler phase."""
        entry = {
            "phase": phase,
            "type": "warning",
            "line": line,
            "message": message,
        }
        if suggestion:
            entry["suggestion"] = suggestion
        self._errors.append(entry)

    def add_info(self, phase, message, line=None):
        """Add an informational message."""
        self._errors.append({
            "phase": phase,
            "type": "info",
            "line": line,
            "message": message,
        })

    def has_errors(self):
        """Check if any errors (not warnings/info) exist."""
        return any(e["type"] == "error" for e in self._errors)

    def get_errors_by_phase(self, phase):
        """Get all entries for a specific phase."""
        return [e for e in self._errors if e["phase"] == phase]

    def get_all(self):
        """Get all entries sorted by line number (None lines last)."""
        return sorted(
            self._errors,
            key=lambda e: (e["line"] if e["line"] is not None else 999999)
        )

    def to_json(self):
        """Return all entries as a JSON-serializable list."""
        return self.get_all()

    def clear(self):
        """Clear all collected entries."""
        self._errors = []

    def __len__(self):
        return len(self._errors)
