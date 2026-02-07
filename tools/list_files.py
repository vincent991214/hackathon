"""
List Files Tool

Tool for listing files in a directory with filtering capabilities.
Supports grouped and flat output formats.
"""

import os
from collections import defaultdict
from pathlib import Path
from typing import List, Dict
from .base import BaseTool, ToolResult
from .config import ToolConfig


class ListFilesTool(BaseTool):
    """Tool to list files in a directory with filtering."""
    """Not in use"""

    def run(self, directory: str, group_by_dir: bool = True) -> ToolResult:
        """
        List files in a directory recursively.

        Args:
            directory: Path to the directory to list
            group_by_dir: Whether to group files by directory

        Returns:
            ToolResult with file listing
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Directory not found: {directory}"
                )

            if not dir_path.is_dir():
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Not a directory: {directory}"
                )

            if group_by_dir:
                result = self._list_grouped(dir_path)
            else:
                result = self._list_flat(dir_path)

            return ToolResult(success=True, data=result)

        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def _list_grouped(self, dir_path: Path) -> str:
        """List files grouped by directory."""
        dir_files = defaultdict(list)

        for root, dirs, files in os.walk(dir_path):
            root_path = Path(root)

            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore_directory(root_path / d)]

            # Get relative directory path
            try:
                rel_dir = root_path.relative_to(dir_path)
            except ValueError:
                rel_dir = Path("/")

            # Add files
            for filename in files:
                file_path = root_path / filename

                # Skip ignored files
                if self._should_ignore_file(file_path):
                    continue

                dir_files[str(rel_dir)].append(filename)

        # Format output
        if not dir_files:
            return f"No files found in {dir_path}."

        result = f"Files grouped by directory (relative to {dir_path}):\n\n"

        for dir_path_str in sorted(dir_files.keys()):
            files = sorted(dir_files[dir_path_str])
            result += f"{dir_path_str}: {files}\n"

        return result

    def _list_flat(self, dir_path: Path) -> str:
        """List all files in a flat list."""
        files = []

        for item in dir_path.rglob("*"):
            if item.is_file():
                # Skip if parent directory is ignored
                if self._should_ignore_directory(item.parent):
                    continue
                # Skip ignored files
                if self._should_ignore_file(item):
                    continue
                files.append(str(item.relative_to(dir_path)))

        if not files:
            return f"No files found in {dir_path}."

        files.sort()
        result = f"Files in {dir_path} ({len(files)} total):\n\n"
        result += "\n".join(files)

        return result

    def _should_ignore_directory(self, dir_path: Path) -> bool:
        """Check if directory should be ignored."""
        parts = dir_path.parts
        return any(ignored in parts for ignored in self.config.IGNORED_DIRS)

    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        return any(
            str(file_path).endswith(ext)
            for ext in self.config.IGNORED_EXTENSIONS
        )
