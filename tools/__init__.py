"""
Code parsing tools for DevMate AI.

This module provides:
- Smart file reading with adaptive strategies
- Tree-sitter based Java parsing
- Project type detection
- Parser factory for automatic selection
"""

from .base import BaseTool, ToolResult
from .config import ToolConfig
from .file_reader import FileReadTool
from .list_files import ListFilesTool
from .project_detector import ProjectDetector, ProjectInfo
from .parser_factory import (
    get_parser,
    CodeParser,
    SmartFileParser,
    ProjectAnalysis,
    FileContent
)

__all__ = [
    # Base
    "BaseTool",
    "ToolResult",

    # Config
    "ToolConfig",

    # Tools
    "FileReadTool",
    "ListFilesTool",
    "ProjectDetector",

    # Data classes
    "ProjectInfo",
    "ProjectAnalysis",
    "FileContent",

    # Factory
    "get_parser",
    "CodeParser",
    "SmartFileParser",
]
