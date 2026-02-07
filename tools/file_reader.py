"""
Optimized File Reader Tool

Intelligent file reading with adaptive strategies based on file size.
Provides multiple reading modes: full, smart, structure_only, and more.
"""

from typing import Optional
from pathlib import Path
from .base import BaseTool, ToolResult
from .config import ToolConfig


class FileReadTool(BaseTool):
    """Intelligent file reading with adaptive strategies."""

    def run(self, file_path: str, context: str = "smart") -> ToolResult:
        """
        Read a file using the best strategy based on file size and type.

        Args:
            file_path: Path to the file to read
            context: Reading strategy - "full", "smart", "structure_only", "more"

        Returns:
            ToolResult with file content
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"File not found: {file_path}"
                )

            file_size = path.stat().st_size

            if context == "full":
                content = self._read_full(file_path)
            elif context == "structure_only":
                content = self._read_structure(file_path)
            elif context == "more":
                content = self._read_more(file_path)
            else:  # smart (default)
                content = self._read_smart(file_path, file_size)

            return ToolResult(success=True, data=content)

        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def _read_smart(self, file_path: str, file_size: int) -> str:
        """Adaptive reading based on file size."""
        if file_size <= self.config.SMALL_FILE_SIZE:
            return self._read_full(file_path)
        elif file_size <= self.config.MEDIUM_FILE_SIZE:
            return self._read_medium(file_path)
        else:
            return self._read_large(file_path)

    def _read_full(self, file_path: str) -> str:
        """Read entire file content."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _read_medium(self, file_path: str) -> str:
        """Read head 50% and tail 50%, overlapping at middle."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            total = len(lines)
            mid = total // 2

            # First half + second half with overlap
            head = lines[:mid]
            tail = lines[mid - 50:] if mid > 50 else lines[mid:]

            result = (
                f"File: {file_path} | Total lines: {total} | Showing: Smart sample\n"
                f"{'=' * 60}\n"
                f"[FIRST HALF - lines 1-{mid}]\n"
                f"{''.join(head)}\n"
                f"\n{'=' * 60}\n"
                f"[SECOND HALF - lines {mid - 50 if mid > 50 else mid}-{total}]\n"
                f"{''.join(tail)}\n"
            )
            return result

    def _read_large(self, file_path: str) -> str:
        """Read head 20%, tail 20%, and 5 evenly spaced samples from middle."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            total = len(lines)

            if total == 0:
                return f"File: {file_path} | Empty file\n"

            head_percent = self.config.LARGE_FILE_HEAD_PERCENT
            tail_percent = self.config.LARGE_FILE_TAIL_PERCENT
            sample_count = self.config.LARGE_FILE_SAMPLE_COUNT

            head_end = max(1, total * head_percent // 100)
            tail_start = max(head_end + 1, total * (100 - tail_percent) // 100)

            head = lines[:head_end]
            tail = lines[tail_start:]

            # Middle samples
            middle_lines = lines[head_end:tail_start]
            sample_size = max(1, len(middle_lines) // sample_count)
            samples = []
            for i in range(sample_count):
                start = i * sample_size
                end = min(start + sample_size, len(middle_lines))
                if start < len(middle_lines):
                    sample_lines = middle_lines[start:end]
                    samples.append(
                        f"[SAMPLE {i + 1} - lines {head_end + start}-{head_end + end}]\n"
                        f"{''.join(sample_lines)}\n"
                    )

            result = (
                f"File: {file_path} | Total lines: {total} | Showing: Large file sample\n"
                f"{'=' * 60}\n"
                f"[HEAD - lines 1-{head_end}]\n{''.join(head)}\n"
                f"\n{'=' * 60}\n"
                f"[MIDDLE SAMPLES]\n{''.join(samples)}\n"
                f"\n{'=' * 60}\n"
                f"[TAIL - lines {tail_start}-{total}]\n{''.join(tail)}\n"
            )
            return result

    def _read_structure(self, file_path: str) -> str:
        """Read only structural elements (imports, classes, functions)."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        structure_lines = []
        in_block_comment = False
        in_java_block_comment = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track Python-style block comments (""", ''')
            if '"""' in stripped or "'''" in stripped:
                in_block_comment = not in_block_comment
                continue

            # Track Java/C-style block comments (/* ... */)
            if '/*' in stripped:
                in_java_block_comment = True
            if '*/' in stripped:
                in_java_block_comment = False
                continue

            if in_block_comment or in_java_block_comment:
                continue

            # Keep single-line comments (javadoc, etc)
            if stripped.startswith(('/**', '/*!', '/*', '*', '//')):
                structure_lines.append(f"{i:4d}: {line}")
                continue

            # Keep imports
            if stripped.startswith(('import ', 'from ', '#include ', '#import ', 'using ', 'package ')):
                structure_lines.append(f"{i:4d}: {line}")

            # Keep class/function/interface definitions and decorators
            elif any(stripped.startswith(kw) for kw in [
                'class ', 'def ', '@', 'async def ', 'func ', 'function ',
                'interface ', 'type ', 'struct ', 'enum ',
                'public ', 'private ', 'protected ', '@Override',
                '@Controller', '@Service', '@Repository', '@Component',
                '@RestController', '@Entity', '@Configuration',
                '@Slf4j', '@Data', '@Builder', '@NoArgsConstructor',
                '@AllArgsConstructor', '@Getter', '@Setter', '@Value',
                'abstract ', 'static ', 'final ', 'synchronized ',
                '@Configuration', '@Bean', '@Autowired'
            ]):
                structure_lines.append(f"{i:4d}: {line}")

            # Keep key keywords
            elif any(stripped.startswith(kw) for kw in ['if __name__', '#!', '# -*-', 'pragma', 'define']):
                structure_lines.append(f"{i:4d}: {line}")

        if not structure_lines:
            return self._read_head(file_path, 50)  # Fallback to head 50 lines

        return (
            f"File: {file_path} | Structure view\n"
            f"{'=' * 60}\n"
            f"{''.join(structure_lines)}\n"
        )

    def _read_head(self, file_path: str, lines_count: int = 50) -> str:
        """Read first N lines of file."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= lines_count:
                    break
                lines.append(line)

            return (
                f"File: {file_path} | Showing first {len(lines)} lines\n"
                f"{'=' * 60}\n"
                f"{''.join(lines)}\n"
            )

    def _read_more(self, file_path: str, offset: int = 0) -> str:
        """Read more content (continuation) - placeholder for future use."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            total = len(lines)

            start_line = offset
            end_line = min(offset + 200, total)

            return (
                f"File: {file_path} | Lines {start_line}-{end_line} of {total}\n"
                f"{'=' * 60}\n"
                f"{''.join(lines[start_line:end_line])}\n"
            )
