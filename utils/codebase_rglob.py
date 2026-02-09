from pathlib import Path
from tools.config import ToolConfig

IGNORED_DIRS = ToolConfig().IGNORED_DIRS
IGNORED_EXTENSIONS = ToolConfig().IGNORED_EXTENSIONS

def safe_rglob(root_path: Path, pattern='*'):
    """Exclude ignored directories while performing recursive globbing."""
    def _recursive_search(current_path, pat):
        try:
            for item in current_path.iterdir():
                if item.name in IGNORED_DIRS:
                    continue
                if item.is_file():
                    if item.suffix.lower() in IGNORED_EXTENSIONS:
                        continue
                    if item.match(pat):
                        yield item
                elif item.is_dir():
                    yield from _recursive_search(item, pat)
        except PermissionError:
            pass

    return _recursive_search(root_path, pattern)