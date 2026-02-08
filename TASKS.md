# Code Parser Optimization Tasks

## IMPORTANT NOTE
**DON'T OVERENGINEER!** Utilize the current structure and extend it efficiently. Keep solutions simple and focused on the actual requirements.

---

## Project Goal

**Enable the LLM to generate better documentation by providing structured code/AST instead of raw truncated code.**

### Current Problem
- Code is truncated to 15,000 characters
- Raw code string is passed to LLM (inefficient)
- No structure/context awareness

### Target Solution
```
┌─────────────────────────────────────────────────────────────┐
│                    DOCUMENTATION GENERATION                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. USER SELECTS PROJECT (Tab 1)                            │
│           │                                                  │
│           ▼                                                  │
│  2. PARSE CODE                                               │
│     • Smart file reading → FileContent (all languages)      │
│     • AST parsing → JavaParseResult (Java only)             │
│           │                                                  │
│           ▼                                                  │
│  3. FORMAT STRUCTURED DATA                                  │
│     • _format_java_parse_results() → Markdown structure      │
│     • _format_file_contents() → File metadata + content     │
│     • Include README.md & CLAUDE.md if found                │
│           │                                                  │
│           ▼                                                  │
│  4. SEND TO LLM                                              │
│     • Template + Structured Code + Instructions → Docs       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Output
`generate_docs(template_md, project_analysis, instructions)`
- `project_analysis` contains **structured parsed code**, not raw string
- LLM receives classes, methods, fields, annotations in readable format
- No arbitrary truncation limit

---

## Task Management Legend
- **Status**: `[ ]` Pending | `[~]` In Progress | `[x]` Completed
- **Priority**: `P0` Critical | `P1` High | `P2` Medium | `P3` Low
- **Complexity**: `L1` Simple | `L2` Moderate | `L3` Complex

---

## [ ] TASK 1: Create Unified Tool System Architecture
**Priority**: P0 | **Complexity**: L2 | **Estimated Files**: 5

### Description
Create a unified tool system to replace the current simple file reading approach. Establish a proper architecture with base classes, configuration management, and consistent interfaces.

### Current State
- File reading is done via `utils/file_reader.py` with simple `os.walk()` and line-based reading
- No unified tool interface exists
- Configuration is scattered across multiple files

### Requirements

#### 1.1 Directory Structure
Create the following files:
```
tools/
├── __init__.py           # Tool module exports
├── base.py               # Base tool class and interfaces
├── config.py             # Tool-specific configuration
├── file_reader.py        # Optimized file reading tool
├── list_files.py         # File listing tool
├── project_detector.py   # Project type detection
├── java_parser.py        # Tree-sitter Java parser
└── parser_factory.py     # Parser selection logic
```

#### 1.2 Configuration (`tools/config.py`)
```python
from dataclasses import dataclass
from typing import List

@dataclass
class ToolConfig:
    """Configuration for code parsing tools"""

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
    IGNORED_DIRS: List[str] = None  # Will be set to DEFAULT_IGNORED_DIRS

    # Ignored extensions
    IGNORED_EXTENSIONS: List[str] = None  # Will be set to DEFAULT_IGNORED_EXTENSIONS
```

#### 1.3 Base Tool Class (`tools/base.py`)
```python
from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass
from opentelemetry import trace

@dataclass
class ToolResult:
    """Standard result format for all tools"""
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Optional[dict] = None

class BaseTool(ABC):
    """Abstract base class for all parsing tools"""

    def __init__(self, config: ToolConfig):
        self.config = config

    @abstractmethod
    def run(self, **kwargs) -> ToolResult:
        """Execute the tool's primary function"""
        pass

    def _trace_input(self, **kwargs):
        """Record input to OpenTelemetry trace"""
        current_span = trace.get_current_span()
        if current_span.is_recording():
            for key, value in kwargs.items():
                current_span.set_attribute(f"input.{key}", str(value))

    def _trace_output(self, result: ToolResult):
        """Record output to OpenTelemetry trace"""
        current_span = trace.get_current_span()
        if current_span.is_recording():
            current_span.set_attribute("output.success", str(result.success))
            if result.error:
                current_span.set_attribute("output.error", result.error)
```

#### 1.4 Update Main Config
Update or create `config.py` at project root to import tool config:
```python
from tools.config import ToolConfig

tool_config = ToolConfig()
```

### Acceptance Criteria
- [ ] `tools/` directory created with all required files
- [ ] `ToolConfig` dataclass with all configuration values
- [ ] `BaseTool` abstract class with `run()` method
- [ ] `ToolResult` dataclass for consistent return format
- [ ] OpenTelemetry integration in base class
- [ ] Main config file imports and exposes tool_config

### Dependencies
None

---

## [ ] TASK 2: Implement Optimized File Reader Tool
**Priority**: P0 | **Complexity**: L3 | **Estimated Files**: 1

### Description
Replace the naive "read first 200 lines" approach with an intelligent reading strategy that adapts based on file size and preserves code structure.

### Current State
- Current `read_codebase()` in `utils/file_reader.py` reads entire files
- No consideration for file size
- No structural preservation (imports, class signatures, etc.)

### Requirements

#### 2.1 File Reading Strategy (`tools/file_reader.py`)
```python
from typing import Optional, List
from pathlib import Path
from .base import BaseTool, ToolResult
from .config import ToolConfig
from utils import Logger

class FileReadTool(BaseTool):
    """Intelligent file reading with adaptive strategies"""

    def run(self, file_path: str, context: str = "smart") -> ToolResult:
        """
        Read a file using the best strategy based on file size and type.

        Args:
            file_path: Path to the file to read
            context: Reading strategy - "full", "smart", "structure_only", "more"
        """
        try:
            file_size = Path(file_path).stat().st_size

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
        """Adaptive reading based on file size"""
        if file_size <= self.config.SMALL_FILE_SIZE:
            return self._read_full(file_path)
        elif file_size <= self.config.MEDIUM_FILE_SIZE:
            return self._read_medium(file_path)
        else:
            return self._read_large(file_path)

    def _read_full(self, file_path: str) -> str:
        """Read entire file content"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _read_medium(self, file_path: str) -> str:
        """Read head 50% and tail 50%, overlapping at middle"""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            total = len(lines)
            mid = total // 2

            # First half + second half with overlap
            head = lines[:mid]
            tail = lines[mid-50:]  # 50 line overlap

            result = (
                f"File: {file_path} | Total lines: {total} | Showing: Smart sample\n"
                f"{'='*60}\n"
                f"[FIRST HALF - lines 1-{mid}]\n"
                f"{''.join(head)}\n"
                f"\n{'='*60}\n"
                f"[SECOND HALF - lines {mid-50}-{total}]\n"
                f"{''.join(tail)}\n"
            )
            return result

    def _read_large(self, file_path: str) -> str:
        """Read head 20%, tail 20%, and 5 evenly spaced samples from middle"""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            total = len(lines)

            head_percent = self.config.LARGE_FILE_HEAD_PERCENT
            tail_percent = self.config.LARGE_FILE_TAIL_PERCENT
            sample_count = self.config.LARGE_FILE_SAMPLE_COUNT

            head_end = total * head_percent // 100
            tail_start = total * (100 - tail_percent) // 100

            head = lines[:head_end]
            tail = lines[tail_start:]

            # Middle samples
            middle_lines = lines[head_end:tail_start]
            sample_size = len(middle_lines) // sample_count
            samples = []
            for i in range(sample_count):
                start = i * sample_size
                end = start + sample_size
                samples.append(f"[SAMPLE {i+1} - lines {head_end+start}-{head_end+end}]\n{''.join(middle_lines[start:end])}\n")

            result = (
                f"File: {file_path} | Total lines: {total} | Showing: Large file sample\n"
                f"{'='*60}\n"
                f"[HEAD - lines 1-{head_end}]\n{''.join(head)}\n"
                f"\n{'='*60}\n"
                f"[MIDDLE SAMPLES]\n{''.join(samples)}\n"
                f"\n{'='*60}\n"
                f"[TAIL - lines {tail_start}-{total}]\n{''.join(tail)}\n"
            )
            return result

    def _read_structure(self, file_path: str) -> str:
        """Read only structural elements (imports, classes, functions)"""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        structure_lines = []
        in_block_comment = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track block comments
            if '"""' in stripped or "'''" in stripped:
                in_block_comment = not in_block_comment
                continue

            if in_block_comment:
                continue

            # Keep imports
            if stripped.startswith(('import ', 'from ')):
                structure_lines.append(f"{i:4d}: {line}")

            # Keep class/function definitions and decorators
            elif stripped.startswith(('class ', 'def ', '@', 'async def ')):
                structure_lines.append(f"{i:4d}: {line}")

            # Keep key keywords
            elif any(stripped.startswith(kw) for kw in ['if __name__', '#!', '# -*-']):
                structure_lines.append(f"{i:4d}: {line}")

        if not structure_lines:
            return self._read_head(file_path, 50)  # Fallback to head 50 lines

        return (
            f"File: {file_path} | Structure view\n"
            f"{'='*60}\n"
            f"{''.join(structure_lines)}\n"
        )

    def _read_more(self, file_path: str, offset: int = 0) -> str:
        """Read more content (continuation) - placeholder for future use"""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            total = len(lines)

            start_line = offset
            end_line = min(offset + 200, total)

            return (
                f"File: {file_path} | Lines {start_line}-{end_line} of {total}\n"
                f"{'='*60}\n"
                f"{''.join(lines[start_line:end_line])}\n"
            )
```

#### 2.2 Update Existing Code
Update `utils/file_reader.py` to use the new tool:
```python
from tools.file_reader import FileReadTool
from tools.config import ToolConfig

# Keep existing function signature for backward compatibility
def read_codebase(folder_path: str, file_pattern: str = "*") -> dict:
    """Read codebase using optimized file reader"""
    tool = FileReadTool(ToolConfig())

    # ... existing walk logic ...
    # Replace simple file read with tool.run()
    result = tool.run(file_path=full_path, context="smart")
    if result.success:
        file_contents[full_path] = result.data
```

### Acceptance Criteria
- [ ] `FileReadTool` class inherits from `BaseTool`
- [ ] Small files (<10KB) are read completely
- [ ] Medium files (10-100KB) read head 50% + tail 50%
- [ ] Large files (>100KB) read head 20% + tail 20% + 5 middle samples
- [ ] Structure-only mode reads imports, class/function definitions
- [ ] All results include file metadata (line numbers, total size)
- [ ] Backward compatibility with existing `read_codebase()` function
- [ ] Error handling returns `ToolResult` with error details

### Dependencies
TASK 1 (Base tool architecture must exist)

---

## [ ] TASK 3: Implement Tree-sitter Java Parser
**Priority**: P0 | **Complexity**: L3 | **Estimated Files**: 1

### Description
Create a Tree-sitter-based Java parser for complete code structure extraction, including Spring framework annotations detection.

### Current State
- No Java-specific parser exists
- Only generic file reading is available
- Spring annotations are not recognized

### Requirements

#### 3.1 Install Dependencies
Update `requirements.txt`:
```
tree-sitter>=0.21.0
tree-sitter-languages>=1.10.0
```

#### 3.2 Java Parser Implementation (`tools/java_parser.py`)
```python
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser, Node
from .base import BaseTool, ToolResult
from .config import ToolConfig
from utils import Logger

# Initialize Java language (singleton)
_JAVA_LANGUAGE = None

def get_java_language():
    global _JAVA_LANGUAGE
    if _JAVA_LANGUAGE is None:
        _JAVA_LANGUAGE = Language(tsjava.language())
    return _JAVA_LANGUAGE

@dataclass
class SpringMetadata:
    """Spring framework specific metadata"""
    controllers: List[Dict] = field(default_factory=list)  # @Controller/@RestController
    services: List[Dict] = field(default_factory=list)     # @Service
    repositories: List[Dict] = field(default_factory=list) # @Repository
    components: List[Dict] = field(default_factory=list)   # @Component
    entities: List[Dict] = field(default_factory=list)     # @Entity
    request_mappings: Dict[str, List[Dict]] = field(default_factory=dict)  # @RequestMapping

@dataclass
class MethodInfo:
    """Method information"""
    name: str
    return_type: str
    parameters: List[Dict]  # [{"type": "String", "name": "id"}]
    annotations: List[str]
    modifiers: Set[str]  # ["public", "static"]
    line_number: int
    is_abstract: bool
    spring_mapping: Optional[Dict] = None  # HTTP mapping info if Spring controller

@dataclass
class FieldInfo:
    """Field information"""
    name: str
    type_name: str
    annotations: List[str]
    modifiers: Set[str]
    line_number: int
    is_autowired: bool  # @Autowired or @Inject

@dataclass
class ClassInfo:
    """Class/interface/enum information"""
    name: str
    type: str  # "class", "interface", "enum", "record"
    package: str
    imports: List[str]
    extends: Optional[str]
    implements: List[str]
    annotations: List[str]
    modifiers: Set[str]
    methods: List[MethodInfo]
    fields: List[FieldInfo]
    line_number: int
    is_spring_component: bool

@dataclass
class JavaParseResult:
    """Complete Java file parse result"""
    file_path: str
    package: str
    imports: List[str]
    classes: List[ClassInfo]
    spring_metadata: SpringMetadata
    total_lines: int
    encoding: str

class TreeSitterJavaParser(BaseTool):
    """Java parser using Tree-sitter for complete AST analysis"""

    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.language = get_java_language()
        self.parser = Parser(self.language)

    def run(self, file_path: str) -> ToolResult:
        """Parse a Java file completely"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()

            tree = self.parser.parse(bytes(source_code, "utf8"))
            root_node = tree.root_node

            result = self._parse_file(file_path, source_code, root_node)
            return ToolResult(success=True, data=result)

        except Exception as e:
            Logger.error(f"Failed to parse Java file: {file_path}", error=str(e))
            return ToolResult(success=False, data=None, error=str(e))

    def _parse_file(self, file_path: str, source_code: str, root_node: Node) -> JavaParseResult:
        """Parse complete Java file"""
        # Extract package
        package = self._extract_package(root_node)

        # Extract imports
        imports = self._extract_imports(root_node)

        # Extract all classes/interfaces/enums
        classes = []
        spring_metadata = SpringMetadata()

        for child in root_node.children:
            if child.type == "class_declaration":
                class_info = self._parse_class(child, source_code)
                classes.append(class_info)
                self._collect_spring_metadata(class_info, spring_metadata)
            elif child.type == "interface_declaration":
                class_info = self._parse_interface(child, source_code)
                classes.append(class_info)
            elif child.type == "enum_declaration":
                class_info = self._parse_enum(child, source_code)
                classes.append(class_info)

        return JavaParseResult(
            file_path=file_path,
            package=package,
            imports=imports,
            classes=classes,
            spring_metadata=spring_metadata,
            total_lines=source_code.count('\n') + 1,
            encoding="utf-8"
        )

    def _extract_package(self, root_node: Node) -> str:
        """Extract package declaration"""
        for child in root_node.children:
            if child.type == "package_declaration":
                # Extract package name from (package_declaration (scoped_identifier (identifier)))
                for subchild in child.children:
                    if subchild.type == "scoped_identifier" or subchild.type == "identifier":
                        return self._get_node_text(subchild)
        return ""

    def _extract_imports(self, root_node: Node) -> List[str]:
        """Extract all import statements"""
        imports = []
        for child in root_node.children:
            if child.type == "import_declaration":
                # Extract import from (import_declaration (scoped_identifier))
                for subchild in child.children:
                    if subchild.type == "scoped_identifier" or subchild.type == "identifier":
                        imports.append(self._get_node_text(subchild))
        return imports

    def _parse_class(self, node: Node, source_code: str) -> ClassInfo:
        """Parse a class declaration"""
        name = self._extract_class_name(node)
        annotations = self._extract_annotations(node)
        modifiers = self._extract_modifiers(node)
        extends = self._extract_extends(node)
        implements = self._extract_implements(node)

        methods = self._extract_methods(node, source_code)
        fields = self._extract_fields(node)

        # Check if Spring component
        is_spring = any(ann in annotations for ann in [
            "Controller", "RestController", "Service", "Repository",
            "Component", "Configuration", "ControllerAdvice"
        ])

        return ClassInfo(
            name=name,
            type="class",
            package="",  # Set at file level
            imports=[],
            extends=extends,
            implements=implements,
            annotations=annotations,
            modifiers=modifiers,
            methods=methods,
            fields=fields,
            line_number=node.start_point[0] + 1,
            is_spring_component=is_spring
        )

    def _parse_interface(self, node: Node, source_code: str) -> ClassInfo:
        """Parse an interface declaration"""
        name = self._extract_class_name(node)
        annotations = self._extract_annotations(node)
        modifiers = self._extract_modifiers(node)
        extends_list = self._extract_extends_interfaces(node)

        methods = self._extract_methods(node, source_code)
        fields = self._extract_fields(node)

        return ClassInfo(
            name=name,
            type="interface",
            package="",
            imports=[],
            extends=None,
            implements=extends_list,
            annotations=annotations,
            modifiers=modifiers,
            methods=methods,
            fields=fields,
            line_number=node.start_point[0] + 1,
            is_spring_component=False
        )

    def _parse_enum(self, node: Node, source_code: str) -> ClassInfo:
        """Parse an enum declaration"""
        name = self._extract_class_name(node)
        annotations = self._extract_annotations(node)
        modifiers = self._extract_modifiers(node)

        # Enums can have methods and fields
        methods = self._extract_methods(node, source_code)
        fields = self._extract_fields(node)

        return ClassInfo(
            name=name,
            type="enum",
            package="",
            imports=[],
            extends=None,
            implements=[],
            annotations=annotations,
            modifiers=modifiers,
            methods=methods,
            fields=fields,
            line_number=node.start_point[0] + 1,
            is_spring_component=False
        )

    def _extract_annotations(self, node: Node) -> List[str]:
        """Extract all annotations from a node"""
        annotations = []
        for child in node.children:
            if child.type == "marker_annotation" or child.type == "annotation":
                name = self._get_annotation_name(child)
                if name:
                    annotations.append(name)
        return annotations

    def _get_annotation_name(self, node: Node) -> Optional[str]:
        """Extract annotation name"""
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child)
        return None

    def _extract_modifiers(self, node: Node) -> Set[str]:
        """Extract modifiers (public, private, static, etc.)"""
        modifiers = set()
        for child in node.children:
            if child.type in ["public", "private", "protected", "static", "final", "abstract", "synchronized"]:
                modifiers.add(child.type)
        return modifiers

    def _extract_class_name(self, node: Node) -> str:
        """Extract class/interface/enum name"""
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child)
        return ""

    def _extract_extends(self, node: Node) -> Optional[str]:
        """Extract extends clause"""
        for child in node.children:
            if child.type == "superclass":
                for subchild in child.children:
                    if subchild.type == "type_identifier":
                        return self._get_node_text(subchild)
        return None

    def _extract_extends_interfaces(self, node: Node) -> List[str]:
        """Extract extends clause for interfaces"""
        interfaces = []
        for child in node.children:
            if child.type == "super_interfaces":
                for subchild in child.children:
                    if subchild.type == "type_list":
                        interfaces.extend(self._extract_type_list(subchild))
        return interfaces

    def _extract_implements(self, node: Node) -> List[str]:
        """Extract implements clause"""
        interfaces = []
        for child in node.children:
            if child.type == "super_interfaces":
                for subchild in child.children:
                    if subchild.type == "type_list":
                        interfaces.extend(self._extract_type_list(subchild))
        return interfaces

    def _extract_type_list(self, node: Node) -> List[str]:
        """Extract list of types from a type_list node"""
        types = []
        for child in node.children:
            if child.type == "type_identifier":
                types.append(self._get_node_text(child))
        return types

    def _extract_methods(self, node: Node, source_code: str) -> List[MethodInfo]:
        """Extract all methods from a class/interface/enum"""
        methods = []

        for child in node.children:
            if child.type == "method_declaration" or child.type == "interface_declaration":
                method_info = self._parse_method(child, source_code)
                methods.append(method_info)
            # Also check for nested classes
            elif child.type == "class_declaration":
                # Recursively extract from nested class
                methods.extend(self._extract_methods(child, source_code))

        return methods

    def _parse_method(self, node: Node, source_code: str) -> MethodInfo:
        """Parse a single method"""
        name = self._extract_method_name(node)
        annotations = self._extract_annotations(node)
        modifiers = self._extract_modifiers(node)
        return_type = self._extract_return_type(node)
        parameters = self._extract_parameters(node)

        # Check for Spring mapping annotations
        spring_mapping = self._extract_spring_mapping(annotations, source_code, node)

        line_number = node.start_point[0] + 1
        is_abstract = "abstract" in modifiers

        return MethodInfo(
            name=name,
            return_type=return_type,
            parameters=parameters,
            annotations=annotations,
            modifiers=modifiers,
            line_number=line_number,
            is_abstract=is_abstract,
            spring_mapping=spring_mapping
        )

    def _extract_method_name(self, node: Node) -> str:
        """Extract method name"""
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child)
        return ""

    def _extract_return_type(self, node: Node) -> str:
        """Extract method return type"""
        for child in node.children:
            if child.type == "type_identifier" or child.type == "generic_type" or child.type == "void_type":
                return self._get_node_text(child)
            # Handle typed return types
            elif child.type == "array_type":
                return self._get_node_text(child) + "[]"
        return ""

    def _extract_parameters(self, node: Node) -> List[Dict]:
        """Extract method parameters"""
        parameters = []

        for child in node.children:
            if child.type == "formal_parameters":
                for param_child in child.children:
                    if param_child.type == "formal_parameter":
                        param_info = self._parse_parameter(param_child)
                        parameters.append(param_info)

        return parameters

    def _parse_parameter(self, node: Node) -> Dict:
        """Parse a single parameter"""
        param_type = ""
        param_name = ""

        for child in node.children:
            if child.type in ["type_identifier", "generic_type", "array_type"]:
                param_type = self._get_node_text(child)
            elif child.type == "identifier":
                param_name = self._get_node_text(child)

        return {"type": param_type, "name": param_name}

    def _extract_spring_mapping(self, annotations: List[str], source_code: str, node: Node) -> Optional[Dict]:
        """Extract Spring HTTP mapping information"""
        mapping_annotations = {
            "RequestMapping": "ALL",
            "GetMapping": "GET",
            "PostMapping": "POST",
            "PutMapping": "PUT",
            "DeleteMapping": "DELETE",
            "PatchMapping": "PATCH",
        }

        for ann in annotations:
            if ann in mapping_annotations:
                # Try to extract path and other attributes
                # This requires more complex parsing of annotation arguments
                return {
                    "type": mapping_annotations[ann],
                    "annotation": ann,
                    "line": node.start_point[0] + 1
                }

        return None

    def _extract_fields(self, node: Node) -> List[FieldInfo]:
        """Extract all fields from a class"""
        fields = []

        for child in node.children:
            if child.type == "field_declaration":
                field_info = self._parse_field(child)
                fields.append(field_info)

        return fields

    def _parse_field(self, node: Node) -> FieldInfo:
        """Parse a single field declaration"""
        name = self._extract_field_name(node)
        field_type = self._extract_field_type(node)
        annotations = self._extract_annotations(node)
        modifiers = self._extract_modifiers(node)

        # Check for dependency injection
        is_autowired = any(ann in annotations for ann in ["Autowired", "Inject", "Resource"])

        return FieldInfo(
            name=name,
            type_name=field_type,
            annotations=annotations,
            modifiers=modifiers,
            line_number=node.start_point[0] + 1,
            is_autowired=is_autowired
        )

    def _extract_field_name(self, node: Node) -> str:
        """Extract field name"""
        for child in node.children:
            if child.type == "variable_declarator":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        return self._get_node_text(subchild)
        return ""

    def _extract_field_type(self, node: Node) -> str:
        """Extract field type"""
        for child in node.children:
            if child.type in ["type_identifier", "generic_type", "array_type"]:
                return self._get_node_text(child)
        return ""

    def _collect_spring_metadata(self, class_info: ClassInfo, metadata: SpringMetadata):
        """Collect Spring-specific metadata from a class"""
        if not class_info.is_spring_component:
            return

        # Determine component type
        annotations_set = set(class_info.annotations)

        class_dict = {
            "name": class_info.name,
            "package": class_info.package,
            "line": class_info.line_number,
            "methods": [m.name for m in class_info.methods]
        }

        if "Controller" in annotations_set or "RestController" in annotations_set:
            metadata.controllers.append(class_dict)
        elif "Service" in annotations_set:
            metadata.services.append(class_dict)
        elif "Repository" in annotations_set:
            metadata.repositories.append(class_dict)
        elif "Component" in annotations_set:
            metadata.components.append(class_dict)

        if "Entity" in annotations_set:
            metadata.entities.append(class_dict)

        # Collect request mappings
        for method in class_info.methods:
            if method.spring_mapping:
                mapping_key = method.spring_mapping["type"]
                if mapping_key not in metadata.request_mappings:
                    metadata.request_mappings[mapping_key] = []
                metadata.request_mappings[mapping_key].append({
                    "class": class_info.name,
                    "method": method.name,
                    "line": method.line_number
                })

    def _get_node_text(self, node: Node) -> str:
        """Get the text content of a node"""
        return node.text.decode('utf-8') if node.text else ""

    def parse_project(self, project_path: str) -> List[JavaParseResult]:
        """Parse all Java files in a project"""
        results = []

        for java_file in Path(project_path).rglob("*.java"):
            # Skip test files and generated files
            if "test" in str(java_file) or "generated" in str(java_file):
                continue

            result = self.run(file_path=str(java_file))
            if result.success:
                results.append(result.data)

        return results
```

### Acceptance Criteria
- [ ] Tree-sitter Java parser installed and initialized
- [ ] `JavaParseResult` contains complete AST information
- [ ] `SpringMetadata` detects all Spring annotations (@Controller, @Service, etc.)
- [ ] `MethodInfo` includes method signatures and HTTP mappings
- [ ] `FieldInfo` detects dependency injection (@Autowired)
- [ ] Parser correctly extracts package, imports, classes, methods, fields
- [ ] Supports nested classes
- [ ] `parse_project()` iterates through all .java files (excluding tests/generated)

### Dependencies
TASK 1 (Base tool architecture must exist)

---

## [ ] TASK 4: Implement Simple Java Project Detection
**Priority**: P1 | **Complexity**: L1 | **Estimated Files**: 1

### Description
Simple detection to check if a project contains Java files.

### Current State
- No project type detection exists

### Requirements

#### 4.1 Simple Detection (`utils/file_reader.py` - extend existing)

Add a simple function to detect Java projects:

```python
def is_java_project(folder_path: str) -> bool:
    """Check if project contains .java files"""
    path = Path(folder_path)
    return any(path.rglob("*.java"))
```

#### 4.2 Update GUI (`gui/app.py`)

Add checkbox state based on detection:

```python
def select_folder(self):
    folder_path = filedialog.askdirectory()
    if folder_path:
        self.path_var.set(folder_path)
        # Check if Java project
        has_java = is_java_project(folder_path)
        if has_java:
            self.deep_parse_checkbox.state(["!disabled"])
        else:
            self.deep_parse_checkbox.state(["disabled"])
```

### Acceptance Criteria
- [ ] `is_java_project()` function checks for .java files
- [ ] Deep parse checkbox enabled when .java files found
- [ ] Deep parse checkbox disabled when no .java files

### Dependencies
None

---

## [ ] TASK 5: Update UI with Deep Parse Option
**Priority**: P1 | **Complexity**: L2 | **Estimated Files**: 1

### Description
Add a checkbox in the Project Setup tab to enable deep code analysis. Auto-detect project type and enable/disable the option accordingly.

### Current State
- Project Setup tab is in `gui/app.py` (lines ~257-300)
- No deep parse option exists
- No project type detection feedback

### Requirements

#### 5.1 UI Components to Add (`gui/app.py`)

In the `_build_tab_setup()` method, add after the folder selection section:

```python
def _build_tab_setup(self):
    # ... existing code ...

    # Add project type detection indicator
    self.project_type_var = tk.StringVar(value="Detecting...")
    self.project_type_frame = ttk.LabelFrame(
        sel_frame,
        text="Project Type",
        padding=(10, 5)
    )
    self.project_type_frame.pack(fill="x", pady=(10, 0))

    self.project_type_label = ttk.Label(
        self.project_type_frame,
        textvariable=self.project_type_var,
        foreground=FG_COLOR
    )
    self.project_type_label.pack(anchor="w")

    # Add deep parse checkbox
    self.deep_parse_var = tk.BooleanVar(value=False)
    self.deep_parse_checkbox = ttk.Checkbutton(
        self.project_type_frame,
        text="Enable Deep Code Analysis (Java/Spring projects only)",
        variable=self.deep_parse_var,
        state="disabled",  # Initially disabled until detection
        command=self._on_deep_parse_toggle
    )
    self.deep_parse_checkbox.pack(anchor="w", pady=(5, 0))

    # Add parse mode indicator
    self.parse_mode_var = tk.StringVar(value="Mode: Fast scan")
    self.parse_mode_label = ttk.Label(
        self.project_type_frame,
        textvariable=self.parse_mode_var,
        foreground=ACCENT_COLOR,
        font=("TkDefaultFont", 9)
    )
    self.parse_mode_label.pack(anchor="w", pady=(2, 0))

    # Add help text
    help_frame = ttk.Frame(self.project_type_frame)
    help_frame.pack(fill="x", pady=(5, 0))

    help_text = (
        "• Fast scan: Quick analysis using smart file reading\n"
        "• Deep analysis: Complete AST parsing (Java projects only)"
    )
    ttk.Label(
        help_frame,
        text=help_text,
        foreground=COMMENT_COLOR,
        font=("TkDefaultFont", 8)
    ).pack(anchor="w")

    # ... rest of existing code ...
```

#### 5.2 Add Color Constants (if not present)

At the top of `gui/app.py`, ensure these colors are defined:

```python
COMMENT_COLOR = "#6A9955"
ACCENT_COLOR = "#4EC9B0"
WARNING_COLOR = "#CE9178"
```

#### 5.3 Update `select_folder()` Method

```python
def select_folder(self):
    folder_path = filedialog.askdirectory()
    if folder_path:
        self.path_var.set(folder_path)
        # Trigger project type detection
        self._detect_and_update_project_type()
```

#### 5.4 Add Detection Handler

```python
def _detect_and_update_project_type(self):
    """Detect project type and update UI accordingly"""
    folder_path = self.path_var.get()

    if not folder_path:
        return

    # Run detection in background to avoid UI freeze
    def detect_task():
        from tools.project_detector import ProjectDetector
        from tools.config import ToolConfig

        detector = ProjectDetector(ToolConfig())
        result = detector.run(project_path=folder_path)

        # Update UI from main thread
        if result.success:
            project_info = result.data
            self.root.after(0, lambda: self._update_project_type_ui(project_info))
        else:
            self.root.after(0, lambda: self._show_detection_error(result.error))

    threading.Thread(target=detect_task, daemon=True).start()

def _update_project_type_ui(self, project_info):
    """Update UI based on detected project type"""
    from tools.project_detector import ProjectInfo

    if not isinstance(project_info, ProjectInfo):
        return

    # Update project type label
    if project_info.is_java_project:
        type_text = f"Detected: Java Project ({project_info.build_tool})"

        if project_info.frameworks:
            frameworks_str = ", ".join(project_info.frameworks)
            type_text += f"\nFrameworks: {frameworks_str}"

        if project_info.java_version:
            type_text += f"\nJava Version: {project_info.java_version}"

        self.project_type_var.set(type_text)

        # Enable deep parse checkbox if supported
        if project_info.supports_deep_parse:
            self.deep_parse_checkbox.state(["!disabled"])
            self.parse_mode_var.set("Mode: Fast scan (enable deep analysis for complete parsing)")
        else:
            self.deep_parse_checkbox.state(["disabled"])
            self.parse_mode_var.set("Mode: Fast scan (deep analysis not available)")

    else:
        self.project_type_var.set("Detected: Non-Java Project")
        self.deep_parse_checkbox.state(["disabled"])
        self.parse_mode_var.set("Mode: Fast scan")

def _show_detection_error(self, error):
    """Show detection error"""
    self.project_type_var.set(f"Detection Error: {error}")
    self.deep_parse_checkbox.state(["disabled"])

def _on_deep_parse_toggle(self):
    """Handle deep parse checkbox toggle"""
    if self.deep_parse_var.get():
        self.parse_mode_var.set("Mode: Deep analysis (complete AST parsing)")
    else:
        self.parse_mode_var.set("Mode: Fast scan (smart file reading)")
```

#### 5.5 Update `load_project()` Method

Modify to pass deep parse option:

```python
def load_project(self):
    """Load and parse the project"""
    folder_path = self.path_var.get()

    if not folder_path:
        messagebox.showwarning("Warning", "Please select a folder first.")
        return

    self.load_btn.config(state="disabled")
    self.status_lbl.config(text="Loading project...")

    def load_task():
        try:
            from tools.project_detector import ProjectDetector
            from tools.parser_factory import get_parser
            from tools.config import ToolConfig

            # Detect project type
            detector = ProjectDetector(ToolConfig())
            detection_result = detector.run(project_path=folder_path)

            if not detection_result.success:
                raise Exception(detection_result.error)

            project_info = detection_result.data

            # Get appropriate parser
            parser = get_parser(
                project_info=project_info,
                enable_deep=self.deep_parse_var.get()
            )

            # Parse project
            parse_result = parser.parse_project(folder_path)

            # Store for later use (parse_result already contains project_path)
            self.project_info = project_info
            self.project_data = parse_result

            # Update UI
            mode = "Deep Analysis" if self.deep_parse_var.get() else "Fast Scan"
            file_count = len(parse_result) if isinstance(parse_result, list) else "N/A"

            # Show detected docs status
            doc_status = ""
            if parse_result.has_readme or parse_result.has_claude_md:
                found_docs = []
                if parse_result.has_readme:
                    found_docs.append("README.md")
                if parse_result.has_claude_md:
                    found_docs.append("CLAUDE.md")
                doc_status = f" | Docs found: {', '.join(found_docs)}"

            self.root.after(0, lambda: self._on_project_loaded(mode, file_count, doc_status))

        except Exception as e:
            self.root.after(0, lambda: self._on_project_error(str(e)))

    threading.Thread(target=load_task, daemon=True).start()

def _on_project_loaded(self, mode: str, file_count, doc_status=""):
    """Handle successful project load"""
    self.load_btn.config(state="normal")
    self.status_lbl.config(
        text=f"Project loaded! Mode: {mode} | Files analyzed: {file_count}{doc_status}"
    )

    # Enable other tabs
    # ... existing code ...

def _on_project_error(self, error: str):
    """Handle project load error"""
    self.load_btn.config(state="normal")
    self.status_lbl.config(text=f"Error: {error}")
    messagebox.showerror("Error", f"Failed to load project:\n{error}")
```

### Acceptance Criteria
- [ ] "Project Type" frame added below folder selection
- [ ] Checkbox "Enable Deep Code Analysis" added with proper label
- [ ] Checkbox is disabled until project type is detected
- [ ] Checkbox is only enabled for Java projects with deep parse support
- [ ] Project type label shows: Java/Gradle/Maven, frameworks, Java version
- [ ] Parse mode indicator shows current mode (Fast/Deep)
- [ ] Help text explains the difference between modes
- [ ] Detection runs in background thread (no UI freeze)
- [ ] `load_project()` uses deep parse option from checkbox
- [ ] `ProjectAnalysis` contains `project_path`, `has_readme`, `has_claude_md` fields
- [ ] Status message shows mode and file count after loading
- [ ] Status message also indicates if README.md or CLAUDE.md was found

#### 5.6 Update Documentation Generation Tab

Update the documentation generation tab to pass project_path:

```python
def generate_documentation(self):
    """Generate documentation using the parsed project"""
    if not hasattr(self, 'project_data') or not self.project_data:
        messagebox.showwarning("Warning", "Please load a project first.")
        return

    template = self.template_text.get("1.0", tk.END).strip()
    instructions = self.instructions_text.get("1.0", tk.END).strip()

    # Check if project docs were detected during parsing
    doc_status = ""
    if self.project_data.has_readme or self.project_data.has_claude_md:
        found_docs = []
        if self.project_data.has_readme:
            found_docs.append("README.md")
        if self.project_data.has_claude_md:
            found_docs.append("CLAUDE.md")
        doc_status = f" | Using: {', '.join(found_docs)}"

    self.status_lbl.config(text=f"Generating documentation{doc_status}...")

    def gen_task():
        try:
            from ai.doc_gen_llm import generate_docs

            result = generate_docs(
                template_md=template,
                project_analysis=self.project_data,  # Contains project_path internally
                instructions=instructions
            )

            self.root.after(0, lambda: self._on_doc_generated(result))

        except Exception as e:
            self.root.after(0, lambda: self._on_doc_error(str(e)))

    threading.Thread(target=gen_task, daemon=True).start()
```

### Dependencies
TASK 4 (Project detection must be implemented first)

---

## [ ] TASK 6: Implement Parser Factory and Selection Logic
**Priority**: P0 | **Complexity**: L2 | **Estimated Files**: 1

### Description
Create a factory pattern for parser selection and define a unified interface for both parsing strategies.

### Current State
- No unified parser interface exists
- No factory for parser selection

### Requirements

#### 6.1 Unified Parser Interface (`tools/parser_factory.py`)

```python
from abc import ABC, abstractmethod
from typing import List, Any, Dict
from dataclasses import dataclass
from pathlib import Path
from .base import BaseTool, ToolResult
from .project_detector import ProjectInfo
from .file_reader import FileReadTool
from .java_parser import TreeSitterJavaParser
from .config import ToolConfig

@dataclass
class ProjectAnalysis:
    """Standardized project analysis result"""
    parser_type: str  # "smart_file_reader" or "tree_sitter_java"
    project_info: ProjectInfo
    files: List[Any]  # List of FileContent or JavaParseResult
    metadata: Dict
    total_files: int
    total_lines: int
    project_path: str  # Path to project (for reading README/CLAUDE.md)
    has_readme: bool = False  # Whether README.md was found
    has_claude_md: bool = False  # Whether CLAUDE.md was found

@dataclass
class FileContent:
    """Result from smart file reader"""
    file_path: str
    content: str
    language: str
    line_count: int
    file_size: int
    reading_strategy: str  # "full", "medium", "large", "structure"

class CodeParser(ABC):
    """Abstract interface for all code parsers"""

    def __init__(self, config: ToolConfig):
        self.config = config

    @abstractmethod
    def parse_project(self, project_path: str, **kwargs) -> ProjectAnalysis:
        """Parse entire project and return standardized result"""
        pass

    @abstractmethod
    def parse_file(self, file_path: str, **kwargs) -> ToolResult:
        """Parse single file"""
        pass

class SmartFileParser(CodeParser):
    """Parser using optimized file reading (for all project types)"""

    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.file_reader = FileReadTool(config)

    def parse_project(self, project_path: str, **kwargs) -> ProjectAnalysis:
        """Parse project using smart file reading"""
        files = []
        total_lines = 0
        path = Path(project_path)

        # Supported code file extensions
        code_extensions = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.h': 'C/C++ Header',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.xml': 'XML',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.bat': 'Batch',
            '.md': 'Markdown',
        }

        for file_path in path.rglob('*'):
            if file_path.is_file():
                # Skip ignored directories
                if any(ignored in str(file_path) for ignored in self.config.IGNORED_DIRS):
                    continue

                # Check if it's a code file
                if file_path.suffix.lower() in code_extensions:
                    # Read file
                    result = self.file_reader.run(file_path=str(file_path), context="smart")

                    if result.success:
                        file_content = FileContent(
                            file_path=str(file_path),
                            content=result.data,
                            language=code_extensions[file_path.suffix.lower()],
                            line_count=result.data.count('\n') + 1,
                            file_size=file_path.stat().st_size,
                            reading_strategy="smart"
                        )
                        files.append(file_content)
                        total_lines += file_content.line_count

        # Check for project documentation files
        has_readme = (path / "README.md").exists() or (path / "readme.md").exists()
        has_claude_md = (path / "CLAUDE.md").exists() or (path / "claude.md").exists()

        return ProjectAnalysis(
            parser_type="smart_file_reader",
            project_info=None,  # Not set at this level
            files=files,
            metadata={
                "strategy": "smart_file_reading",
                "extensions_supported": list(code_extensions.keys())
            },
            total_files=len(files),
            total_lines=total_lines,
            project_path=project_path,
            has_readme=has_readme,
            has_claude_md=has_claude_md
        )

    def parse_file(self, file_path: str, context: str = "smart", **kwargs) -> ToolResult:
        """Parse single file"""
        return self.file_reader.run(file_path=file_path, context=context)

class TreeSitterJavaParserWrapper(CodeParser):
    """Parser using Tree-sitter for Java projects"""

    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.java_parser = TreeSitterJavaParser(config)

    def parse_project(self, project_path: str, **kwargs) -> ProjectAnalysis:
        """Parse Java project using Tree-sitter"""
        parse_results = self.java_parser.parse_project(project_path)
        total_lines = sum(r.total_lines for r in parse_results)

        # Convert to standardized format
        files = parse_results  # Already in structured format

        # Check for project documentation files
        path = Path(project_path)
        has_readme = (path / "README.md").exists() or (path / "readme.md").exists()
        has_claude_md = (path / "CLAUDE.md").exists() or (path / "claude.md").exists()

        return ProjectAnalysis(
            parser_type="tree_sitter_java",
            project_info=None,
            files=files,
            metadata={
                "strategy": "tree_sitter_ast",
                "spring_detected": any(
                    r.spring_metadata.controllers or
                    r.spring_metadata.services or
                    r.spring_metadata.repositories
                    for r in parse_results
                )
            },
            total_files=len(parse_results),
            total_lines=total_lines,
            project_path=project_path,
            has_readme=has_readme,
            has_claude_md=has_claude_md
        )

    def parse_file(self, file_path: str, **kwargs) -> ToolResult:
        """Parse single Java file"""
        return self.java_parser.run(file_path=file_path)

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
        from tools.config import ToolConfig
        config = ToolConfig()

    # Decision tree:
    # 1. Java project + deep parse enabled + supported → Tree-sitter Java parser
    # 2. Everything else → Smart file reader

    if (project_info.is_java_project and
        enable_deep and
        project_info.supports_deep_parse):
        return TreeSitterJavaParserWrapper(config)
    else:
        return SmartFileParser(config)
```

#### 6.2 Update Existing Code

Update `gui/app.py` to use the new parser:

```python
def load_project(self):
    # ... existing folder check ...

    def load_task():
        try:
            from tools.project_detector import ProjectDetector
            from tools.parser_factory import get_parser, ProjectAnalysis
            from tools.config import ToolConfig

            config = ToolConfig()

            # Detect project type
            detector = ProjectDetector(config)
            detection_result = detector.run(project_path=folder_path)
            if not detection_result.success:
                raise Exception(detection_result.error)

            project_info = detection_result.data

            # Get parser and parse
            parser = get_parser(
                project_info=project_info,
                enable_deep=self.deep_parse_var.get(),
                config=config
            )

            analysis: ProjectAnalysis = parser.parse_project(folder_path)

            # Store results
            self.project_info = project_info
            self.project_analysis = analysis

            # Update UI
            self.root.after(0, lambda: self._on_project_loaded(analysis))

        except Exception as e:
            self.root.after(0, lambda: self._on_project_error(str(e)))

    threading.Thread(target=load_task, daemon=True).start()
```

### Acceptance Criteria
- [ ] `CodeParser` abstract class defined with `parse_project()` and `parse_file()` methods
- [ ] `SmartFileParser` implements optimized file reading for all languages
- [ ] `TreeSitterJavaParserWrapper` wraps the Tree-sitter parser
- [ ] `ProjectAnalysis` dataclass provides standardized output format
- [ ] `ProjectAnalysis.project_path` contains the project directory path
- [ ] `ProjectAnalysis.has_readme` indicates if README.md was found
- [ ] `ProjectAnalysis.has_claude_md` indicates if CLAUDE.md was found
- [ ] `FileContent` dataclass for smart reader results
- [ ] `get_parser()` factory function implements decision tree correctly:
    - Java + deep + supported → Tree-sitter
    - Otherwise → Smart file reader
- [ ] Parser results include metadata about parsing strategy
- [ ] `gui/app.py` updated to use new parser factory

### Dependencies
TASK 1, 2, 3, 4 (All core components must exist)

---

## [ ] TASK 7: Update List Files Tool
**Priority**: P2 | **Complexity**: L2 | **Estimated Files**: 1

### Description
Implement the `ListFilesTool` with proper ignored directories and extensions configuration.

### Current State
- No separate list files tool exists
- File listing is embedded in `read_codebase()`

### Requirements

#### 7.1 List Files Tool (`tools/list_files.py`)

```python
import os
from collections import defaultdict
from pathlib import Path
from typing import List, Dict
from .base import BaseTool, ToolResult
from .config import ToolConfig
from utils import Logger

class ListFilesTool(BaseTool):
    """Tool to list files in a directory with filtering"""

    def run(self, directory: str, group_by_dir: bool = True) -> ToolResult:
        """
        List files in a directory recursively.

        Args:
            directory: Path to the directory to list
            group_by_dir: Whether to group files by directory

        Returns:
            ToolResult with file listing
        """
        Logger.debug("Tool Call: List Files", data={"directory": directory})

        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Directory not found: {directory}"
                )

            if group_by_dir:
                result = self._list_grouped(dir_path)
            else:
                result = self._list_flat(dir_path)

            return ToolResult(success=True, data=result)

        except Exception as e:
            Logger.error("Failed to list files", error=str(e))
            return ToolResult(success=False, data=None, error=str(e))

    def _list_grouped(self, dir_path: Path) -> str:
        """List files grouped by directory"""
        dir_files = defaultdict(list)

        for root, _, files in os.walk(dir_path):
            root_path = Path(root)

            # Skip ignored directories
            if self._should_ignore_directory(root_path):
                continue

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

        for dir_path in sorted(dir_files.keys()):
            files = sorted(dir_files[dir_path])
            result += f"{dir_path}: {files}\n"

        return result

    def _list_flat(self, dir_path: Path) -> str:
        """List all files in a flat list"""
        files = []

        for item in dir_path.rglob("*"):
            if item.is_file():
                if self._should_ignore_directory(item.parent):
                    continue
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
        """Check if directory should be ignored"""
        parts = dir_path.parts
        return any(ignored in parts for ignored in self.config.IGNORED_DIRS)

    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored"""
        return any(
            str(file_path).endswith(ext)
            for ext in self.config.IGNORED_EXTENSIONS
        )
```

### Acceptance Criteria
- [ ] `ListFilesTool` inherits from `BaseTool`
- [ ] Supports grouped and flat output formats
- [ ] Respects `IGNORED_DIRS` from config
- [ ] Respects `IGNORED_EXTENSIONS` from config
- [ ] Returns formatted string with file listings
- [ ] Proper error handling for non-existent directories

### Dependencies
TASK 1 (Base tool architecture must exist)

---

## [ ] TASK 8: Configuration and Documentation
**Priority**: P1 | **Complexity**: L1 | **Estimated Files**: 3

### Description
Add configuration values, update requirements, and create documentation.

### Requirements

#### 8.1 Update `requirements.txt`
Add the following dependencies:
```
tree-sitter>=0.21.0
tree-sitter-languages>=1.10.0
```

#### 8.2 Create `tools/__init__.py`
```python
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
from .java_parser import TreeSitterJavaParser, JavaParseResult
from .parser_factory import (
    get_parser,
    CodeParser,
    SmartFileParser,
    TreeSitterJavaParserWrapper,
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
    "TreeSitterJavaParser",

    # Data classes
    "ProjectInfo",
    "JavaParseResult",
    "ProjectAnalysis",
    "FileContent",

    # Factory
    "get_parser",
    "CodeParser",
    "SmartFileParser",
    "TreeSitterJavaParserWrapper",
]
```

#### 8.3 Update `config.py` at project root
```python
"""
Application configuration.
"""

import os
from dotenv import load_dotenv
from tools.config import ToolConfig

# Load environment variables
load_dotenv()

# Tool configuration
tool_config = ToolConfig()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://open.bigmodel.cn/api/coding/paas/v4")

# Model Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "glm-4-plus")
```

#### 8.4 Create Parser Usage Documentation
Create `docs/parser_usage.md`:
```markdown
# Code Parser Usage Guide

## Overview

DevMate AI provides two code parsing strategies:

1. **Smart File Reading** - Fast analysis using adaptive file reading
2. **Deep Analysis (Java)** - Complete AST parsing using Tree-sitter

## Parser Selection

The parser is automatically selected based on:
- Project type (Java vs non-Java)
- User preference (deep analysis checkbox)
- Project confidence score

```
Project Type    | Deep Parse | Parser Used
----------------|------------|-------------
Java/Spring     | Yes        | Tree-sitter Java
Java/Spring     | No         | Smart File Reader
Non-Java        | Yes/No     | Smart File Reader
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

## Tree-sitter Java Parser

### Supported Java Features
- Package and import extraction
- Class, interface, enum parsing
- Method signatures with parameters
- Field declarations
- Nested classes
- Generics support

### Spring Framework Detection
- `@Controller`, `@RestController`
- `@Service`, `@Repository`, `@Component`
- `@Entity`, `@Table`
- `@RequestMapping`, `@GetMapping`, etc.
- `@Autowired` dependency injection

## API Usage

```python
from tools import get_parser, ProjectDetector, ToolConfig

# Detect project type
detector = ProjectDetector(ToolConfig())
result = detector.run(project_path="/path/to/project")
project_info = result.data

# Get parser
parser = get_parser(
    project_info=project_info,
    enable_deep=True  # or False
)

# Parse project
analysis = parser.parse_project("/path/to/project")

# Access results
print(f"Parser: {analysis.parser_type}")
print(f"Files: {analysis.total_files}")
print(f"Lines: {analysis.total_lines}")
```

## Configuration

Edit `tools/config.py` to customize:
- File size thresholds
- Reading strategy percentages
- Ignored directories and files
- Retry settings
```

### Acceptance Criteria
- [ ] `requirements.txt` includes tree-sitter dependencies
- [ ] `tools/__init__.py` exports all public classes
- [ ] `config.py` at root imports and exposes `ToolConfig`
- [ ] `docs/parser_usage.md` created with usage guide
- [ ] All configurations have default values

### Dependencies
All previous tasks

---

---

## [ ] TASK 9: Update generate_docs to Use Parsed Results (Stage 2)
**Priority**: P0 | **Complexity**: L2 | **Estimated Files**: 1

### Description
Update `generate_docs()` to accept `ProjectAnalysis` instead of raw code string. Format parsed results appropriately for LLM consumption.

### Current State
- `generate_docs(template_md, code, instructions)` takes raw code string
- Code is truncated to 15000 characters
- No distinction between parsing strategies

### Requirements

#### 9.1 Understanding AST (Abstract Syntax Tree)

**AST** is a tree representation of code structure. Example:

```java
// Original Java code
package com.example;
import java.util.List;

@RestController
@RequestMapping("/api/users")
public class UserController {
    @Autowired
    private UserService userService;

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
}
```

**Tree-sitter AST** (simplified node structure):
```
program
├── package_declaration
│   └── scoped_identifier: com.example
├── import_declaration
│   └── scoped_identifier: java.util.List
└── class_declaration
    ├── markers: @RestController, @RequestMapping
    ├── name: UserController
    ├── field: userService (type: UserService, @Autowired)
    └── method_declaration
        ├── markers: @GetMapping
        ├── name: getUser
        ├── parameters: [id: Long @PathVariable]
        └── return_type: User
```

**Our Parsed Result** (dataclass format):
```python
JavaParseResult(
    file_path="src/main/java/com/example/UserController.java",
    package="com.example",
    imports=["java.util.List"],
    classes=[
        ClassInfo(
            name="UserController",
            type="class",
            annotations=["RestController", "RequestMapping"],
            methods=[
                MethodInfo(
                    name="getUser",
                    return_type="User",
                    parameters=[{"type": "Long", "name": "id"}],
                    annotations=["GetMapping", "PathVariable"],
                    line_number=12
                )
            ],
            fields=[
                FieldInfo(
                    name="userService",
                    type_name="UserService",
                    annotations=["Autowired"],
                    is_autowired=True
                )
            ]
        )
    ],
    spring_metadata=SpringMetadata(
        controllers=[{"name": "UserController", "methods": ["getUser"]}]
    )
)
```

#### 9.2 Format Functions (`ai/doc_gen_llm.py`)

```python
from pathlib import Path
from typing import Optional, Tuple

def _read_project_docs(project_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Read README.md and CLAUDE.md files from the project.

    Args:
        project_path: Path to the project directory

    Returns:
        Tuple of (readme_content, claude_md_content) - None if file not found
    """
    path = Path(project_path)
    readme_content = None
    claude_md_content = None

    # Search for README.md (case-insensitive)
    for readme_name in ['README.md', 'readme.md', 'README.MD']:
        readme_path = path / readme_name
        if readme_path.exists():
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
                break
            except Exception:
                pass

    # Search for CLAUDE.md (case-insensitive)
    for claude_name in ['CLAUDE.md', 'claude.md', 'CLAUDE.MD']:
        claude_path = path / claude_name
        if claude_path.exists():
            try:
                with open(claude_path, 'r', encoding='utf-8') as f:
                    claude_md_content = f.read()
                break
            except Exception:
                pass

    # Also search in parent directories (up to 3 levels)
    if readme_content is None or claude_md_content is None:
        for i in range(1, 4):
            parent_path = path.parents[min(i, len(path.parents) - 1)]
            if parent_path == path:
                break

            if readme_content is None:
                for readme_name in ['README.md', 'readme.md', 'README.MD']:
                    readme_path = parent_path / readme_name
                    if readme_path.exists():
                        try:
                            with open(readme_path, 'r', encoding='utf-8') as f:
                                readme_content = f.read()
                            break
                        except Exception:
                            pass

            if claude_md_content is None:
                for claude_name in ['CLAUDE.md', 'claude.md', 'CLAUDE.MD']:
                    claude_path = parent_path / claude_name
                    if claude_path.exists():
                        try:
                            with open(claude_path, 'r', encoding='utf-8') as f:
                                claude_md_content = f.read()
                            break
                        except Exception:
                            pass

    return readme_content, claude_md_content


def _format_java_parse_results(parse_results: List[JavaParseResult]) -> str:
    """Format Tree-sitter Java parse results for LLM consumption"""
    output = []
    output.append("# JAVA PROJECT STRUCTURE (Deep Analysis)\n")

    # Group by package
    by_package = {}
    for result in parse_results:
        pkg = result.package or "default"
        if pkg not in by_package:
            by_package[pkg] = []
        by_package[pkg].append(result)

    # Output organized by package
    for pkg, results in sorted(by_package.items()):
        output.append(f"## Package: {pkg}\n")

        for result in results:
            for cls in result.classes:
                # Class signature
                annotations = " ".join(f"@{a}" for a in cls.annotations)
                extends = f" extends {cls.extends}" if cls.extends else ""
                implements = f" implements {', '.join(cls.implements)}" if cls.implements else ""

                output.append(f"### {cls.type}: {annotations} {cls.name}{extends}{implements}")
                output.append(f"**File:** `{result.file_path}:{cls.line_number}`\n")

                # Fields
                if cls.fields:
                    output.append("**Fields:**")
                    for field in cls.fields:
                        field_ann = " ".join(f"@{a}" for a in field.annotations)
                        autowired = " [autowired]" if field.is_autowired else ""
                        output.append(f"  - {field_ann} {field.type_name} {field.name}{autowired}")
                    output.append("")

                # Methods
                if cls.methods:
                    output.append("**Methods:**")
                    for method in cls.methods:
                        method_ann = " ".join(f"@{a}" for a in method.annotations)
                        params = ", ".join(f"{p['type']} {p['name']}" for p in method.parameters)
                        output.append(f"  - {method_ann} {method.return_type} {method.name}({params})")
                        if method.spring_mapping:
                            output.append(f"    [HTTP: {method.spring_mapping['type']}]")
                    output.append("")

    # Spring metadata summary
    output.append("\n## Spring Framework Summary")
    for result in parse_results:
        meta = result.spring_metadata
        if meta.controllers:
            output.append(f"\n**Controllers:** {', '.join(c['name'] for c in meta.controllers)}")
        if meta.services:
            output.append(f"**Services:** {', '.join(s['name'] for s in meta.services)}")
        if meta.repositories:
            output.append(f"**Repositories:** {', '.join(r['name'] for r in meta.repositories)}")
        if meta.entities:
            output.append(f"**Entities:** {', '.join(e['name'] for e in meta.entities)}")

        if meta.request_mappings:
            output.append("\n**API Endpoints:**")
            for http_type, endpoints in meta.request_mappings.items():
                output.append(f"  {http_type}:")
                for ep in endpoints:
                    output.append(f"    - {ep['class']}.{ep['method']}()")

    return "\n".join(output)


def _format_file_contents(file_contents: List[FileContent]) -> str:
    """Format smart file reader results for LLM consumption"""
    output = []
    output.append("# PROJECT FILES (Smart Scan)\n")

    # Group by language
    by_language = {}
    for fc in file_contents:
        lang = fc.language
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(fc)

    for lang, files in sorted(by_language.items()):
        output.append(f"## {lang} Files ({len(files)} files)\n")

        for fc in files[:50]:  # Limit to prevent overflow
            output.append(f"### `{fc.file_path}`")
            output.append(f"**Size:** {fc.file_size // 1024}KB | **Lines:** {fc.line_count}")
            output.append(f"**Strategy:** {fc.reading_strategy}\n")
            output.append("```")
            output.append(fc.content[:2000])  # Truncate very long contents
            output.append("```\n")

    return "\n".join(output)


def generate_docs(
    template_md: str,
    project_analysis: ProjectAnalysis,
    instructions: str = ""
) -> str:
    """
    Generate documentation using parsed project analysis.

    Args:
        template_md: Template structure
        project_analysis: ProjectAnalysis from parser (contains files + metadata + project_path)
        instructions: Additional user instructions

    Returns:
        Generated documentation
    """
    # Read project documentation files for additional context
    # project_analysis.project_path contains the path to the project
    readme_content, claude_md_content = _read_project_docs(project_analysis.project_path)

    # Format code context based on parser type
    if project_analysis.parser_type == "tree_sitter_java":
        code_context = _format_java_parse_results(project_analysis.files)
    else:
        code_context = _format_file_contents(project_analysis.files)

    # Build project documentation section
    project_docs_section = ""
    if readme_content or claude_md_content:
        project_docs_section = "\n## PROJECT DOCUMENTATION\n"
        if readme_content:
            project_docs_section += f"\n### README.md\n{readme_content[:5000]}\n"  # Limit length
        if claude_md_content:
            project_docs_section += f"\n### CLAUDE.md (Project Instructions)\n{claude_md_content[:5000]}\n"  # Limit length
        project_docs_section += "\n"

    # Build prompt
    prompt = f"""
You are a professional technical writer.

Task: Using the provided template structure and codebase analysis, generate comprehensive technical documentation.

TEMPLATE STRUCTURE:
{template_md}

CODEBASE ANALYSIS ({project_analysis.parser_type}):
Parser: {project_analysis.parser_type}
Total Files: {project_analysis.total_files}
Total Lines: {project_analysis.total_lines}
Metadata: {project_analysis.metadata}

{code_context}
{project_docs_section}
ADDITIONAL INSTRUCTIONS:
{instructions}

IMPORTANT FORMATTING RULES:
1. Use Markdown headers (# for H1, ## for H2).
2. Use Markdown tables for lists of components or parameters.
3. Do NOT use code blocks for normal text.
4. Ensure clarity and conciseness in explanations.

PROJECT CONTEXT GUIDANCE:
- If CLAUDE.md is provided above, follow any specific project conventions mentioned
- If README.md is provided, incorporate any architectural overview or setup instructions
- Maintain consistency with the project's existing documentation style

Output ONLY the documentation content.
"""
    return _send_request(prompt)
```

#### 9.3 Backward Compatibility

Keep the old signature working:

```python
def generate_docs_v1(template_md: str, code: str, instructions: str = "") -> str:
    """Legacy version - accepts raw code string"""
    # Keep existing implementation for backward compatibility
    prompt = f"... {code[:15000]} ..."
    return _send_request(prompt)
```

### Acceptance Criteria
- [ ] `_format_java_parse_results()` converts JavaParseResult to readable markdown
- [ ] `_format_file_contents()` converts FileContent to readable markdown
- [ ] `_read_project_docs()` searches for README.md and CLAUDE.md files
- [ ] `_read_project_docs()` searches in project directory and up to 3 parent levels
- [ ] `_read_project_docs()` handles case-insensitive file names
- [ ] `generate_docs()` reads project docs from `project_analysis.project_path`
- [ ] README.md content (if found) is included in the LLM prompt
- [ ] CLAUDE.md content (if found) is included in the LLM prompt
- [ ] Project documentation is limited to 5000 characters each to prevent overflow
- [ ] LLM prompt includes guidance to use project conventions from CLAUDE.md
- [ ] `generate_docs()` signature: `generate_docs(template_md, project_analysis, instructions)`
- [ ] Tree-sitter results show structure (classes, methods, fields) not raw code
- [ ] Spring annotations are clearly marked
- [ ] API endpoints are summarized
- [ ] Smart file reader results show file metadata + content
- [ ] Backward compatible with old `generate_docs(code_string)` signature
- [ ] No more hard 15000 char limit (uses formatted structured data)

### Dependencies
TASK 3, 6 (Java parser and parser factory must exist)

------

## [ ] TASK 10: Implement Agent-Based Code Access (Stage 3 - Low Priority)
**Priority**: P3 | **Complexity**: L3 | **Estimated Files**: 2

### Description
Implement an optional agent mode where LLM can request specific code chunks on-demand, useful for very large projects.

### When to Use This
- Projects with >500 Java files
- When user needs very detailed documentation of specific components
- When structured summary isn't enough

### Requirements

#### 10.1 Tool Definition for Agent

Create `ai/code_tools.py`:
```python
from typing import Optional, List, Dict
from pydantic_ai import Tool
from tools.java_parser import TreeSitterJavaParser, JavaParseResult
from tools.parser_factory import ProjectAnalysis
import config

class CodeAccessTool:
    """Tools for LLM to access parsed code on-demand"""

    def __init__(self, project_analysis: ProjectAnalysis):
        self.analysis = project_analysis
        # Build lookup indexes
        self._class_index = self._build_class_index()
        self._file_index = self._build_file_index()

    def _build_class_index(self) -> Dict[str, JavaParseResult]:
        """Build index by class name"""
        index = {}
        for result in self.analysis.files:
            for cls in result.classes:
                key = f"{result.package}.{cls.name}" if result.package else cls.name
                index[key] = result
        return index

    def _build_file_index(self) -> Dict[str, JavaParseResult]:
        """Build index by file path"""
        return {r.file_path: r for r in self.analysis.files}

    def get_tools(self) -> List[Tool]:
        """Return all available tools for the agent"""
        return [
            Tool(self._list_classes, name="List-Classes"),
            Tool(self._get_class_detail, name="Get-Class-Detail"),
            Tool(self._get_file_detail, name="Get-File-Detail"),
            Tool(self._search_classes, name="Search-Classes"),
        ]

    def _list_classes(self) -> str:
        """List all classes in the project"""
        output = ["## All Classes\n"]

        for result in self.analysis.files:
            for cls in result.classes:
                pkg = result.package or "default"
                output.append(f"- {pkg}.{cls.name} ({cls.type})")
                if cls.is_spring_component:
                    output.append(f"  Spring: {', '.join(cls.annotations)}")

        return "\n".join(output)

    def _get_class_detail(self, class_name: str) -> str:
        """Get detailed information about a specific class"""
        # Search with and without package
        result = self._class_index.get(class_name)
        if not result:
            # Try simple name match
            for key, val in self._class_index.items():
                if key.endswith(f".{class_name}"):
                    result = val
                    break

        if not result:
            return f"Class not found: {class_name}"

        # Format class detail
        output = [f"## Class: {class_name}"]
        output.append(f"**File:** `{result.file_path}`\n")

        for cls in result.classes:
            if cls.name == class_name or f"{result.package}.{cls.name}" == class_name:
                output.append(f"**Type:** {cls.type}")
                output.append(f"**Annotations:** {', '.join(cls.annotations)}")

                if cls.extends:
                    output.append(f"**Extends:** {cls.extends}")
                if cls.implements:
                    output.append(f"**Implements:** {', '.join(cls.implements)}")

                output.append("\n### Fields")
                for field in cls.fields:
                    output.append(f"- {field.type_name} {field.name}")
                    if field.annotations:
                        output.append(f"  Annotations: {', '.join(field.annotations)}")

                output.append("\n### Methods")
                for method in cls.methods:
                    params = ", ".join(f"{p['type']} {p['name']}" for p in method.parameters)
                    output.append(f"- {method.return_type} {method.name}({params})")
                    if method.spring_mapping:
                        output.append(f"  HTTP: {method.spring_mapping['type']}")

        return "\n".join(output)

    def _get_file_detail(self, file_path: str) -> str:
        """Get all classes in a specific file"""
        result = self._file_index.get(file_path)
        if not result:
            return f"File not found: {file_path}"

        output = [f"## File: {file_path}"]
        output.append(f"**Package:** {result.package}")
        output.append(f"**Imports:** {', '.join(result.imports[:10])}")
        output.append(f"**Total Lines:** {result.total_lines}\n")

        for cls in result.classes:
            output.append(f"### {cls.name}")
            output.append(f"Methods: {len(cls.methods)}, Fields: {len(cls.fields)}")

        return "\n".join(output)

    def _search_classes(self, keyword: str) -> str:
        """Search for classes by name or annotation"""
        results = []

        for result in self.analysis.files:
            for cls in result.classes:
                # Search in class name
                if keyword.lower() in cls.name.lower():
                    results.append(f"- {result.package}.{cls.name}")
                    continue

                # Search in annotations
                for ann in cls.annotations:
                    if keyword.lower() in ann.lower():
                        results.append(f"- {result.package}.{cls.name} (@{ann})")
                        break

        if not results:
            return f"No classes found matching: {keyword}"

        return f"## Search Results for '{keyword}'\n" + "\n".join(results)
```

#### 10.2 Agent-Enabled generate_docs

```python
def generate_docs_with_agent(
    template_md: str,
    project_analysis: ProjectAnalysis,
    instructions: str = "",
    use_agent: bool = False
) -> str:
    """
    Generate documentation with optional agent mode.

    Args:
        use_agent: If True, LLM can request specific code chunks
    """
    if not use_agent or project_analysis.total_files < 100:
        # Use standard method for smaller projects
        return generate_docs(template_md, project_analysis, instructions)

    # For large projects, use agent mode
    from pydantic_ai import Agent

    # Create code access tools
    code_tool = CodeAccessTool(project_analysis)
    tools = code_tool.get_tools()

    # Create agent
    agent = Agent(
        name="documentation_agent",
        model=MODEL_NAME,
        tools=tools,
        instructions=f"""
You are a technical documentation expert.

Available tools:
- List-Classes: List all classes in the project
- Get-Class-Detail: Get full details of a specific class
- Get-File-Detail: Get all classes in a file
- Search-Classes: Search by name or annotation

Template:
{template_md}

Use tools to gather information, then write comprehensive documentation.
"""
    )

    # Run agent
    response = agent.run(f"Generate documentation following this template. {instructions}")
    return response
```

### Acceptance Criteria
- [ ] `CodeAccessTool` provides tools for class/file lookup
- [ ] `List-Classes` lists all classes with package and type
- [ ] `Get-Class-Detail` returns full class info (fields, methods, annotations)
- [ ] `Get-File-Detail` returns all classes in a file
- [ ] `Search-Classes` searches by name or annotation
- [ ] `generate_docs_with_agent()` has `use_agent` parameter
- [ ] Agent mode only activates for projects with 100+ files
- [ ] Falls back to standard mode for smaller projects

### Dependencies
TASK 9 (Stage 2 must be implemented first)

---

## Version History
| Date | Change | Author |
|------|--------|--------|
| 2026-02-06 | Initial task creation for parser optimization | Joy |
| 2026-02-06 | Add Stage 2 (formatted results) and Stage 3 (agent mode) | Joy |
| 2026-02-06 | Add automatic README.md and CLAUDE.md reading for project context | Joy |

---

## Summary of Changes for README.md/CLAUDE.md Integration

### What Changed
When generating documentation, the system now automatically:
1. **Searches for README.md and CLAUDE.md files** in the project directory
2. **Searches up to 3 parent directories** if not found in the project root
3. **Handles case-insensitive file names** (README.md, readme.md, README.MD, etc.)
4. **Passes the content to the LLM** as part of the documentation generation prompt
5. **Limits content to 5000 characters each** to prevent prompt overflow

### Benefits
- **Project-specific conventions** from CLAUDE.md are automatically followed
- **Architecture overview** from README.md provides context
- **No manual configuration needed** - files are detected automatically
- **Better documentation quality** - LLM understands project patterns and style

### Implementation Location
- **Function**: `_read_project_docs(project_path: str)` in `ai/doc_gen_llm.py`
- **Called by**: `generate_docs()` function
- **Updated signature**: `generate_docs(template_md, project_analysis, project_path, instructions)`

### Example Prompt Structure
```
TEMPLATE STRUCTURE:
{template_md}

CODEBASE ANALYSIS:
{parsed_code_results}

PROJECT DOCUMENTATION:
### README.md
{readme_content}

### CLAUDE.md (Project Instructions)
{claude_md_content}

ADDITIONAL INSTRUCTIONS:
{user_instructions}

PROJECT CONTEXT GUIDANCE:
- If CLAUDE.md is provided above, follow any specific project conventions mentioned
- If README.md is provided, incorporate any architectural overview
```
