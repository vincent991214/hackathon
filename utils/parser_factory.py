"""
Parser Factory and Selection Logic

Provides a unified interface for different code parsing strategies.
Factory pattern selects the appropriate parser based on project type.
"""

from abc import ABC, abstractmethod
from typing import List, Any, Dict
from dataclasses import dataclass
from pathlib import Path
from tools.base import BaseTool, ToolResult
from .project_detector import ProjectInfo
from tools.file_reader import FileReadTool
from tools.config import ToolConfig
from utils.codebase_rglob import safe_rglob


@dataclass
class ProjectAnalysis:
    """Standardized project analysis result."""
    parser_type: str  # "smart_file_reader" or "tree_sitter_java"
    project_info: ProjectInfo
    files: List[Any]  # List of FileContent or JavaParseResult
    metadata: Dict
    total_files: int
    total_lines: int
    project_path: str  # Path to project (for reading README/CLAUDE.md)
    has_readme: bool = False  # Whether README.md was found
    has_claude_md: bool = False  # Whether CLAUDE.md was found

    def __str__(self) -> str:
        """Return a summary string for backward compatibility."""
        parts = []
        parts.append(f"Parser: {self.parser_type}")
        parts.append(f"Total Files: {self.total_files}")
        parts.append(f"Total Lines: {self.total_lines}")
        parts.append(f"Has README.md: {self.has_readme}")
        parts.append(f"Has CLAUDE.md: {self.has_claude_md}")
        return "\n".join(parts)


@dataclass
class FileContent:
    """Result from smart file reader."""
    file_path: str
    content: str
    language: str
    line_count: int
    file_size: int
    reading_strategy: str  # "full", "medium", "large", "structure"


class CodeParser(ABC):
    """Abstract interface for all code parsers."""

    def __init__(self, config: ToolConfig):
        self.config = config

    @abstractmethod
    def parse_project(self, project_path: str, **kwargs) -> ProjectAnalysis:
        """Parse entire project and return standardized result."""
        pass

    @abstractmethod
    def parse_file(self, file_path: str, **kwargs) -> ToolResult:
        """Parse single file."""
        pass


class SmartFileParser(CodeParser):
    """Parser using optimized file reading (for all project types)."""

    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.file_reader = FileReadTool(config)

    def parse_project(self, project_path: str, **kwargs) -> ProjectAnalysis:
        """Parse project using smart file reading."""
        files = []
        total_lines = 0
        path = Path(project_path)

        for file_path in safe_rglob(path):
            if file_path.is_file():

                # Check if it's a code file
                suffix = file_path.suffix.lower()
                if suffix in self.config.CODE_EXTENSIONS:
                    # Skip ignored extensions
                    # if any(str(file_path).endswith(ext) for ext in self.config.IGNORED_EXTENSIONS):
                    #     print("ignored extensions")
                    #     continue

                    try:
                        # Read file
                        result = self.file_reader.run(file_path=str(file_path), context="smart")

                        if result.success:
                            content = result.data
                            file_content = FileContent(
                                file_path=str(file_path),
                                content=content,
                                language=self.config.CODE_EXTENSIONS[suffix],
                                line_count=content.count('\n') + 1,
                                file_size=file_path.stat().st_size,
                                reading_strategy="smart"
                            )
                            files.append(file_content)
                            total_lines += file_content.line_count
                    except Exception:
                        pass

        # Check for project documentation files
        has_readme = (path / "README.md").exists() or (path / "readme.md").exists()
        has_claude_md = (path / "CLAUDE.md").exists() or (path / "claude.md").exists()
        return ProjectAnalysis(
            parser_type="smart_file_reader",
            project_info=None,
            files=files,
            metadata={
                "strategy": "smart_file_reading",
                "extensions_supported": list(self.config.CODE_EXTENSIONS.keys())
            },
            total_files=len(files),
            total_lines=total_lines,
            project_path=project_path,
            has_readme=has_readme,
            has_claude_md=has_claude_md
        )

    def parse_file(self, file_path: str, context: str = "smart", **kwargs) -> ToolResult:
        """Parse single file."""
        return self.file_reader.run(file_path=file_path, context=context)


def get_parser(project_info: ProjectInfo, enable_deep: bool, config: ToolConfig = None) -> CodeParser:
    """
    Factory function to get the appropriate parser.

    Args:
        project_info: Detected project information
        enable_deep: Whether to enable deep parsing
        config: Tool configuration (uses default if None)

    Returns:
        Appropriate CodeParser instance
    """
    if config is None:
        from ..tools.config import ToolConfig
        config = ToolConfig()

    # Decision tree:
    # 1. Java project + deep parse enabled + supported → Tree-sitter Java parser
    # 2. Everything else → Smart file reader

    # For now, always use SmartFileParser
    # Tree-sitter Java parser will be added in a future update
    return SmartFileParser(config)
