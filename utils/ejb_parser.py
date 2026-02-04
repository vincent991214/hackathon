"""
EJB Parser Module - Static Analysis Layer for Enterprise Java Beans

This module provides tree-sitter-based parsing for EJB (Enterprise Java Beans) projects.
It identifies EJB interfaces, beans, and related DTOs/Entities using syntax analysis.
"""

import os
import json
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EJBInterfaceInfo:
    """Data class representing a discovered EJB interface."""
    id: str
    interface_name: str
    bean_class: Optional[str]
    file_path: str
    package: str
    annotations: List[str]
    interface_type: str  # "Remote", "Local", or "Unknown"
    methods: List[Dict[str, str]]
    related_dtos: List[str]
    related_entities: List[str]


class EJBParser:
    """
    Parser for EJB (Enterprise Java Beans) projects.

    This class analyzes Java source code to identify:
    - EJB Interfaces (annotated with @Remote, @Local, or following naming conventions)
    - Implementation Beans
    - Related DTOs and Entities
    """

    # EJB annotation patterns
    EJB_ANNOTATIONS = {
        'Remote', 'Local', 'Stateless', 'Stateful',
        'Singleton', 'MessageDriven', 'EJB', 'EJBs'
    }

    # EJB naming convention patterns
    INTERFACE_PATTERNS = [
        r'.*Remote$',      # E.g., UserServiceRemote
        r'.*Local$',       # E.g., UserServiceLocal
        r'.*Service$',     # E.g., UserService
        r'.*DAO$',         # E.g., UserDAO
        r'.*Repository$',  # E.g., UserRepository
    ]

    def __init__(self, project_path: str):
        """
        Initialize the EJB Parser.

        Args:
            project_path: Root directory of the Java/EJB project
        """
        self.project_path = Path(project_path)
        self.symbol_table: Dict[str, str] = {}  # {ClassName: FilePath}
        self.interfaces: List[EJBInterfaceInfo] = []
        self.all_imports: Dict[str, Set[str]] = {}  # {FilePath: Set of imported classes}

    def parse(self) -> Tuple[Dict[str, str], List[EJBInterfaceInfo]]:
        """
        Main parsing method. Analyzes all Java files in the project.

        Returns:
            Tuple of (symbol_table, list of EJBInterfaceInfo)
        """
        logger.info(f"Starting EJB analysis for: {self.project_path}")

        # Step 1: Build symbol table
        self._build_symbol_table()

        # Step 2: Analyze imports
        self._analyze_imports()

        # Step 3: Identify EJB interfaces
        self._identify_interfaces()

        # Step 4: Link beans to interfaces
        self._link_beans_to_interfaces()

        # Step 5: Find related DTOs and entities
        self._find_related_classes()

        logger.info(f"Found {len(self.interfaces)} EJB interfaces")
        return self.symbol_table, self.interfaces

    def _build_symbol_table(self):
        """
        Walk through all .java files and build a symbol table mapping
        class names to their file paths.
        """
        java_files = list(self.project_path.rglob("*.java"))

        for java_file in java_files:
            try:
                with open(java_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Extract package name
                package_match = re.search(r'package\s+([\w.]+)\s*;', content)
                package = package_match.group(1) if package_match else ''

                # Extract all class/interface/enum declarations
                # Pattern for: public class/interface/enum ClassName
                class_pattern = r'(?:public\s+)?(?:abstract\s+)?(?:final\s+)?(class|interface|enum)\s+(\w+)'
                matches = re.findall(class_pattern, content)

                for type_decl, class_name in matches:
                    full_name = f"{package}.{class_name}" if package else class_name
                    simple_name = class_name
                    self.symbol_table[simple_name] = str(java_file)
                    self.symbol_table[full_name] = str(java_file)

            except Exception as e:
                logger.warning(f"Failed to parse {java_file}: {e}")

        logger.info(f"Built symbol table with {len(self.symbol_table)} entries")

    def _analyze_imports(self):
        """
        Analyze import statements in all Java files to understand dependencies.
        """
        for class_name, file_path in self.symbol_table.items():
            # Avoid duplicates by using simple names only
            if '.' in class_name:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Extract imports
                import_pattern = r'import\s+([\w.*]+)\s*;'
                imports = set(re.findall(import_pattern, content))
                self.all_imports[file_path] = imports

            except Exception as e:
                logger.warning(f"Failed to analyze imports in {file_path}: {e}")

    def _identify_interfaces(self):
        """
        Identify EJB interfaces using annotations and naming conventions.
        """
        seen_interfaces = set()

        for class_name, file_path in list(self.symbol_table.items()):
            # Process only simple names to avoid duplicates
            if '.' in class_name:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Check if it's an interface
                if not re.search(r'\binterface\s+' + re.escape(class_name) + r'\b', content):
                    continue

                # Extract package
                package_match = re.search(r'package\s+([\w.]+)\s*;', content)
                package = package_match.group(1) if package_match else ''

                # Extract annotations on the interface
                annotations = self._extract_annotations(content, class_name)

                # Determine interface type
                interface_type = "Unknown"
                if '@Remote' in annotations or any('Remote' in ann for ann in annotations):
                    interface_type = "Remote"
                elif '@Local' in annotations or any('Local' in ann for ann in annotations):
                    interface_type = "Local"
                else:
                    # Check naming conventions
                    for pattern in self.INTERFACE_PATTERNS:
                        if re.search(pattern, class_name):
                            if 'Remote' in class_name:
                                interface_type = "Remote"
                            elif 'Local' in class_name:
                                interface_type = "Local"
                            else:
                                interface_type = "Business"
                            break

                # Only include if it has EJB characteristics
                is_ejb = (
                    any(ann for ann in annotations if self._is_ejb_annotation(ann)) or
                    any(re.search(pattern, class_name) for pattern in self.INTERFACE_PATTERNS)
                )

                if is_ejb and class_name not in seen_interfaces:
                    # Extract methods
                    methods = self._extract_methods(content)

                    interface_info = EJBInterfaceInfo(
                        id=f"{package}.{class_name}" if package else class_name,
                        interface_name=class_name,
                        bean_class=None,  # Will be linked later
                        file_path=file_path,
                        package=package,
                        annotations=annotations,
                        interface_type=interface_type,
                        methods=methods,
                        related_dtos=[],
                        related_entities=[]
                    )
                    self.interfaces.append(interface_info)
                    seen_interfaces.add(class_name)

            except Exception as e:
                logger.warning(f"Failed to identify interface {class_name}: {e}")

    def _extract_annotations(self, content: str, class_name: str) -> List[str]:
        """Extract annotations for a class/interface."""
        # Find the class/interface declaration line
        pattern = rf'(?:@[^\n]+\s+)*\binterface\s+{re.escape(class_name)}\b'
        match = re.search(pattern, content)

        if match:
            declaration = match.group(0)
            # Extract all annotations
            annotations = re.findall(r'@(\w+(?:\(\))?[^@\n]*)', declaration)
            return [f"@{ann.strip()}" for ann in annotations]

        return []

    def _is_ejb_annotation(self, annotation: str) -> bool:
        """Check if an annotation is EJB-related."""
        ann_upper = annotation.upper()
        return any(ejb_ann.upper() in ann_upper for ejb_ann in self.EJB_ANNOTATIONS)

    def _extract_methods(self, content: str) -> List[Dict[str, str]]:
        """
        Extract method signatures from an interface.

        Returns list of dicts with 'return_type', 'name', 'parameters'
        """
        methods = []

        # Pattern for method declarations
        # This regex captures: return_type method_name(parameters) throws...
        method_pattern = r'(?:\b(\w+(?:<[^>]+>)?(?:\[\])?)\s+)?(\w+)\s*\(([^)]*)\)(?:\s+throws\s+[^{;]+)?[;{]'

        for match in re.finditer(method_pattern, content):
            return_type = match.group(1) or 'void'
            method_name = match.group(2)
            parameters = match.group(3).strip()

            # Skip if it's not a valid method (e.g., 'class', 'interface', 'if')
            if method_name in ['class', 'interface', 'if', 'while', 'for', 'catch']:
                continue

            methods.append({
                'return_type': return_type,
                'name': method_name,
                'parameters': parameters
            })

        return methods

    def _link_beans_to_interfaces(self):
        """
        For each interface, find its implementation bean class.
        Uses naming conventions and implements clauses.
        """
        for interface_info in self.interfaces:
            interface_name = interface_info.interface_name

            # Strategy 1: Check for naming convention: InterfaceNameBean, InterfaceNameImpl
            bean_candidates = [
                f"{interface_name}Bean",
                f"{interface_name}Impl",
                f"{interface_name}EJB",
                interface_name.replace("Remote", "Bean"),
                interface_name.replace("Local", "Bean"),
                interface_name.replace("Service", "ServiceImpl"),
                interface_name.replace("DAO", "DAOImpl"),
            ]

            for candidate in bean_candidates:
                if candidate in self.symbol_table:
                    interface_info.bean_class = candidate
                    break

            # Strategy 2: Check implements clause in potential bean files
            if not interface_info.bean_class:
                for class_name, file_path in self.symbol_table.items():
                    if '.' in class_name:
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                        # Check if this class implements the interface
                        implements_pattern = rf'implements\s+[^{{]*\b{re.escape(interface_name)}\b'
                        if re.search(implements_pattern, content):
                            interface_info.bean_class = class_name
                            break

                    except Exception:
                        continue

    def _find_related_classes(self):
        """
        Find DTOs and Entities related to each interface by analyzing
        method signatures and imports.
        """
        dto_keywords = ['DTO', 'Dto', 'Data', 'Value', 'VO', 'Model']
        entity_keywords = ['Entity', 'Persistable', 'Table', 'JPA', 'Entity']

        for interface_info in self.interfaces:
            # Get the interface file content
            interface_content = self._get_file_content(interface_info.file_path)

            # Check imports for DTOs and entities
            imports = self.all_imports.get(interface_info.file_path, set())

            for imp in imports:
                simple_name = imp.split('.')[-1]

                # Check if it's a DTO
                if any(kw in simple_name for kw in dto_keywords):
                    if simple_name not in interface_info.related_dtos:
                        interface_info.related_dtos.append(simple_name)

                # Check if it's an Entity
                if any(kw in simple_name for kw in entity_keywords):
                    if simple_name not in interface_info.related_entities:
                        interface_info.related_entities.append(simple_name)

            # Check method return types and parameters
            for method in interface_info.methods:
                # Check return type
                return_type = method['return_type']
                if return_type and return_type != 'void':
                    simple_return = return_type.split('.')[-1].replace('<', '').replace('>', '')
                    if any(kw in simple_return for kw in dto_keywords):
                        if simple_return not in interface_info.related_dtos:
                            interface_info.related_dtos.append(simple_return)

                # Check parameters
                params = method.get('parameters', '')
                for param_type in self._parse_parameter_types(params):
                    simple_param = param_type.split('.')[-1].replace('<', '').replace('>', '')
                    if any(kw in simple_param for kw in dto_keywords):
                        if simple_param not in interface_info.related_dtos:
                            interface_info.related_dtos.append(simple_param)

    def _parse_parameter_types(self, parameters: str) -> List[str]:
        """Extract parameter types from a parameter string."""
        if not parameters or parameters.strip() == '':
            return []

        types = []
        # Split by comma and extract type from each parameter
        for param in parameters.split(','):
            param = param.strip()
            if not param:
                continue

            # Extract type (everything before the last space or before the parameter name)
            parts = param.split()
            if len(parts) >= 2:
                types.append(parts[0])

        return types

    def _get_file_content(self, file_path: str) -> str:
        """Read and return the content of a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return ""

    def generate_json_manifest(self) -> str:
        """
        Generate a JSON manifest of all discovered EJB interfaces.

        Returns:
            JSON string containing the manifest
        """
        manifest_data = {
            "project_path": str(self.project_path),
            "total_interfaces": len(self.interfaces),
            "interfaces": [asdict(interface) for interface in self.interfaces]
        }

        return json.dumps(manifest_data, indent=2, ensure_ascii=False)

    def save_json_manifest(self, output_path: str):
        """
        Save the JSON manifest to a file.

        Args:
            output_path: Path where the JSON file will be saved
        """
        manifest_content = self.generate_json_manifest()

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(manifest_content)

        logger.info(f"JSON manifest saved to: {output_path}")


def validate_ejb_project(project_path: str) -> Tuple[bool, str]:
    """
    Validate if the uploaded project is an EJB project.

    Checks for:
    - Presence of Java files
    - EJB annotations (@Remote, @Local, etc.)
    - EJB deployment descriptors (ejb-jar.xml)
    - Common EJB naming patterns

    Args:
        project_path: Path to the project directory

    Returns:
        Tuple of (is_valid, message)
    """
    path = Path(project_path)

    if not path.exists():
        return False, "Project path does not exist"

    # Check for Java files
    java_files = list(path.rglob("*.java"))
    if not java_files:
        return False, "No Java files found in the project"

    # Check for EJB indicators
    has_ejb_annotations = False
    has_ejb_xml = False
    has_ejb_naming = False

    # Check for ejb-jar.xml
    xml_files = list(path.rglob("ejb-jar.xml"))
    if xml_files:
        has_ejb_xml = True

    # Check Java files for EJB patterns
    interface_count = 0
    for java_file in java_files[:100]:  # Limit to first 100 files for performance
        try:
            with open(java_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Check for EJB annotations
            ejb_annotations = ['@Remote', '@Local', '@Stateless', '@Stateful', '@Singleton']
            if any(ann in content for ann in ejb_annotations):
                has_ejb_annotations = True

            # Check for EJB naming patterns
            if re.search(r'\binterface\s+\w+(?:Remote|Local|Service|DAO)\b', content):
                has_ejb_naming = True
                interface_count += 1

        except Exception:
            continue

    # Determine if it's an EJB project
    is_ejb = has_ejb_xml or has_ejb_annotations or (has_ejb_naming and interface_count >= 2)

    if not is_ejb:
        return False, (
            "This does not appear to be an EJB project. "
            "EJB projects should contain @Remote/@Local annotations, "
            "ejb-jar.xml configuration, or follow EJB naming conventions."
        )

    return True, f"Valid EJB project detected with {interface_count} interfaces"


def extract_from_zip(zip_path: str, extract_to: str) -> str:
    """
    Extract a ZIP file and return the extraction path.

    Args:
        zip_path: Path to the ZIP file
        extract_to: Directory where contents will be extracted

    Returns:
        Path to the extracted directory
    """
    import zipfile

    os.makedirs(extract_to, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    # Find the root directory (usually the first folder)
    extracted_items = os.listdir(extract_to)
    if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_to, extracted_items[0])):
        return os.path.join(extract_to, extracted_items[0])

    return extract_to
