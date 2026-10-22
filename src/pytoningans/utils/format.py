"""
Contains some formatting utilities.
"""

def formatted_size(size_bytes: int) -> str:
    """Returns human-readable size string (e.g. 1.2 MB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"