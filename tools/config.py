"""
Tool configuration for code parsing.

This module provides centralized configuration for all code parsing tools,
including file size thresholds, reading strategies, and ignored paths.
"""

from dataclasses import dataclass, field
from typing import List


# Default ignored directories (common build, dependency, and temp folders)
DEFAULT_IGNORED_DIRS = {
    '__pycache__', 'venv', 'virtualenv', '.venv', '.virtualenv',
    'node_modules', '.git', '.svn', '.hg', '.idea',
    'build', 'dist', 'target', 'bin', 'obj',
    '.tox', '.pytest_cache', '.mypy_cache',
    '.eggs', '*.egg-info', '.vscode',
    '.next', '.nuxt', 'coverage', '.coverage',
    'vendor', 'bower_components','assets','resources'
}


# Default ignored file extensions
DEFAULT_IGNORED_EXTENSIONS = {
    '.pyc', '.pyo', '.pyd', '.pyi',
    '.so', '.dll', '.dylib', '.exe', '.bin',
    '.o', '.a', '.lib', '.obj',
    '.class', '.jar', '.war', '.ear',
    '.log', '.bak', '.tmp', '.swp', '.swo',
    '.zip', '.tar', '.tar.gz', '.rar', '.7z',
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
    '.mp3', '.mp4', '.avi', '.mov', '.wav',
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
    '.pdb', '.idb', '.pch',
}

# Supported code file extensions
DEFAULT_CODE_EXTENSIONS = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.ts': 'TypeScript',
    '.java': 'Java',
    '.cpp': 'C++',
    '.c': 'C',
    '.h': 'C/C++ Header',
    '.cc': 'C++',
    '.hpp': 'C++ Header',
    '.cs': 'C#',
    '.go': 'Go',
    '.rs': 'Rust',
    '.rb': 'Ruby',
            '.php': 'PHP',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.sass': 'SASS',
            '.less': 'LESS',
            '.xml': 'XML',
            '.json': 'JSON',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.bat': 'Batch',
            '.md': 'Markdown',
            '.jsx': 'React JSX',
            '.tsx': 'React TSX',
            '.vue': 'Vue',
}

@dataclass
class ToolConfig:
    """Configuration for code parsing tools."""

    # Retry settings
    TOOL_FILE_READER_MAX_RETRIES: int = 3
    TOOL_LIST_FILES_MAX_RETRIES: int = 3

    # File size thresholds (in bytes)
    SMALL_FILE_SIZE: int = 10 * 1024      # 10KB
    MEDIUM_FILE_SIZE: int = 100 * 1024    # 100KB

    # Reading strategy settings
    LARGE_FILE_HEAD_PERCENT: int = 20     # Read first 20%
    LARGE_FILE_TAIL_PERCENT: int = 20     # Read last 20%
    LARGE_FILE_SAMPLE_COUNT: int = 5      # Number of middle samples

    # Deep analysis settings
    DEEP_PARSE_MAX_FILE_SIZE: int = 1024 * 1024  # 1MB per file
    DEEP_PARSE_MAX_FILES: int = 500

    # Ignored directories
    IGNORED_DIRS: set[str] = field(default_factory=lambda: DEFAULT_IGNORED_DIRS)

    # Ignored extensions
    IGNORED_EXTENSIONS: set[str] = field(default_factory=lambda: DEFAULT_IGNORED_EXTENSIONS)

    CODE_EXTENSIONS: dict[str,str] = field(default_factory=lambda: DEFAULT_CODE_EXTENSIONS)
