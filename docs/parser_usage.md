# Code Parser Usage Guide

## Overview

DevMate AI provides intelligent code parsing strategies for documentation generation:

1. **Smart File Reading** - Fast analysis using adaptive file reading
2. **Deep Analysis (Java)** - Complete AST parsing using Tree-sitter (coming soon)

## Parser Selection

The parser is automatically selected based on project type and user preferences:

```
Project Type    | Deep Parse | Parser Used
----------------|------------|-------------
Java/Maven      | Yes        | Smart File Reader (Java AST coming soon)
Java/Gradle     | No         | Smart File Reader
Python          | Yes/No     | Smart File Reader
JavaScript      | Yes/No     | Smart File Reader
Other           | Yes/No     | Smart File Reader
```

## Smart File Reading Strategy

### Small Files (<10KB)
- Complete file content is read
- Best for: Configuration files, small scripts

### Medium Files (10-100KB)
- Head 50% + Tail 50% (with 50-line overlap)
- Best for: Medium-sized source files

### Large Files (>100KB)
- Head 20% + Tail 20% + 5 middle samples
- Best for: Large source files, generated code

### Structure-Only Mode
- Reads only imports, classes, functions, decorators
- Best for: Quick overview of code structure

## Supported File Types

| Extension | Language    |
|-----------|-------------|
| .py       | Python      |
| .js, .jsx | JavaScript  |
| .ts, .tsx | TypeScript  |
| .java     | Java        |
| .cpp, .c  | C/C++       |
| .go       | Go          |
| .rs       | Rust        |
| .rb       | Ruby        |
| .php      | PHP         |
| .html     | HTML        |
| .css, .scss | CSS       |
| .xml      | XML         |
| .json     | JSON        |
| .yaml, .yml | YAML       |
| .sql      | SQL         |
| .sh       | Shell       |
| .md       | Markdown    |

## Ignored Directories

The following directories are automatically ignored:
- `__pycache__`, `venv`, `.venv`, `virtualenv`
- `node_modules`, `.git`, `.svn`, `.hg`, `.idea`
- `build`, `dist`, `target`, `bin`, `obj`
- `.tox`, `.pytest_cache`, `.mypy_cache`
- `.eggs`, `*.egg-info`, `.vscode`
- `vendor`, `bower_components`

## Ignored File Extensions

- Compiled files: `.pyc`, `.class`, `.o`, `.so`, `.dll`
- Archives: `.zip`, `.tar`, `.gz`, `.rar`
- Images: `.png`, `.jpg`, `.gif`, `.svg`
- Audio/Video: `.mp3`, `.mp4`, `.avi`
- Fonts: `.ttf`, `.otf`, `.woff`

## API Usage

### Detect Project Type

```python
from tools import ProjectDetector, ToolConfig

detector = ProjectDetector(ToolConfig())
result = detector.run(project_path="/path/to/project")

if result.success:
    info = result.data
    print(f"Project: Java={info.is_java_project}")
    print(f"Build tool: {info.build_tool}")
    print(f"Frameworks: {info.frameworks}")
```

### Parse Project

```python
from tools import get_parser, ProjectDetector, ToolConfig

# Detect project type
detector = ProjectDetector(ToolConfig())
detection_result = detector.run(project_path="/path/to/project")
project_info = detection_result.data

# Get parser
parser = get_parser(
    project_info=project_info,
    enable_deep=True  # Enable deep analysis if supported
)

# Parse project
analysis = parser.parse_project("/path/to/project")

# Access results
print(f"Parser: {analysis.parser_type}")
print(f"Files: {analysis.total_files}")
print(f"Lines: {analysis.total_lines}")
print(f"Has README.md: {analysis.has_readme}")
print(f"Has CLAUDE.md: {analysis.has_claude_md}")
```

### Read Single File

```python
from tools import FileReadTool, ToolConfig

reader = FileReadTool(ToolConfig())
result = reader.run(file_path="/path/to/file.py", context="smart")

if result.success:
    print(result.data)
```

### List Files

```python
from tools import ListFilesTool, ToolConfig

lister = ListFilesTool(ToolConfig())
result = lister.run(directory="/path/to/project", group_by_dir=True)

if result.success:
    print(result.data)
```

## Configuration

Edit `tools/config.py` to customize:

- File size thresholds (`SMALL_FILE_SIZE`, `MEDIUM_FILE_SIZE`)
- Reading strategy percentages (`LARGE_FILE_HEAD_PERCENT`)
- Ignored directories and files
- Retry settings

## Project Documentation Integration

The parser automatically detects and includes:
- `README.md` or `readme.md` for project overview
- `CLAUDE.md` or `claude.md` for project-specific AI instructions

These files are automatically included in the LLM prompt when generating documentation.
