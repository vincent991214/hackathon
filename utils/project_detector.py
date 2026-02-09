"""
Project Type Detector

Detects project types, build tools, and frameworks.
Supports Java (Maven/Gradle), Python, JavaScript/TypeScript, and more.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set
from ..tools.base import BaseTool, ToolResult
from ..tools.config import ToolConfig


@dataclass
class ProjectInfo:
    """Information about a detected project."""
    project_path: str
    is_java_project: bool = False
    is_python_project: bool = False
    is_js_project: bool = False
    build_tool: str = ""  # maven, gradle, npm, pip, etc.
    frameworks: List[str] = field(default_factory=list)  # spring, django, react, etc.
    java_version: Optional[str] = None
    confidence: float = 0.0  # 0.0 to 1.0
    supports_deep_parse: bool = False

    # File counts
    java_file_count: int = 0
    python_file_count: int = 0
    js_file_count: int = 0


class ProjectDetector(BaseTool):
    """Detects project type and characteristics."""

    # Java build indicators
    JAVA_BUILD_FILES = {
        'pom.xml': 'maven',
        'build.gradle': 'gradle',
        'build.gradle.kts': 'gradle',
        'settings.gradle': 'gradle',
        'settings.gradle.kts': 'gradle',
        'gradle.properties': 'gradle',
        'ivy.xml': 'ivy',
        'build.xml': 'ant',
    }

    # Java framework indicators
    JAVA_FRAMEWORKS = {
        'spring': [
            'spring-core', 'spring-boot', 'spring-framework',
            '@SpringBootApplication', '@Controller', '@RestController',
            '@Service', '@Repository', '@Component', '@Entity'
        ],
        'jakarta-ee': ['@Inject', '@EJB', '@Stateless', '@Stateful'],
        'micronaut': ['io.micronaut'],
        'quarkus': ['io.quarkus'],
    }

    # Python indicators
    PYTHON_BUILD_FILES = {
        'requirements.txt': 'pip',
        'setup.py': 'setuptools',
        'pyproject.toml': 'poetry',
        'Pipfile': 'pipenv',
        'environment.yml': 'conda',
        'setup.cfg': 'setuptools',
    }

    PYTHON_FRAMEWORKS = {
        'django': ['django', 'DJANGO_SETTINGS_MODULE'],
        'flask': ['flask', 'Flask'],
        'fastapi': ['fastapi', 'FastAPI'],
        'pytest': ['pytest'],
    }

    # JavaScript/TypeScript indicators
    JS_BUILD_FILES = {
        'package.json': 'npm',
        'yarn.lock': 'yarn',
        'pnpm-lock.yaml': 'pnpm',
    }

    JS_FRAMEWORKS = {
        'react': ['react', 'React'],
        'vue': ['vue', 'Vue'],
        'angular': ['@angular/core'],
        'express': ['express'],
        'next': ['next', 'Next.js'],
    }

    def run(self, project_path: str, deep_scan: bool = False) -> ToolResult:
        """
        Detect project type and characteristics.

        Args:
            project_path: Path to the project directory
            deep_scan: Whether to perform deep scanning (slower but more accurate)

        Returns:
            ToolResult with ProjectInfo
        """
        try:
            path = Path(project_path)
            if not path.exists():
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Path not found: {project_path}"
                )

            info = ProjectInfo(project_path=project_path)

            # Detect build tool
            build_tool = self._detect_build_tool(path)
            info.build_tool = build_tool

            # Count files by type
            self._count_files(path, info)

            # Detect Java project
            if info.java_file_count > 0 or build_tool in ['maven', 'gradle', 'ant', 'ivy']:
                info.is_java_project = True
                info.supports_deep_parse = True
                info.confidence = min(1.0, 0.3 + (info.java_file_count * 0.01))

                # Detect Java version
                info.java_version = self._detect_java_version(path)

                # Detect frameworks
                if deep_scan:
                    info.frameworks = self._detect_java_frameworks(path)
                else:
                    # Quick framework detection from build files
                    info.frameworks = self._detect_java_frameworks_quick(path)

            # Detect Python project
            if info.python_file_count > 0 or build_tool in ['pip', 'setuptools', 'poetry', 'pipenv', 'conda']:
                info.is_python_project = True
                info.confidence = min(1.0, 0.3 + (info.python_file_count * 0.01))

                if deep_scan:
                    info.frameworks = self._detect_python_frameworks(path)

            # Detect JavaScript/TypeScript project
            if info.js_file_count > 0 or build_tool in ['npm', 'yarn', 'pnpm']:
                info.is_js_project = True
                info.confidence = min(1.0, 0.3 + (info.js_file_count * 0.01))

                if deep_scan:
                    info.frameworks = self._detect_js_frameworks(path)

            return ToolResult(success=True, data=info)

        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def _detect_build_tool(self, path: Path) -> str:
        """Detect build tool from config files."""
        # Check Java build tools
        for file_name, tool in self.JAVA_BUILD_FILES.items():
            if (path / file_name).exists():
                return tool

        # Check Python build tools
        for file_name, tool in self.PYTHON_BUILD_FILES.items():
            if (path / file_name).exists():
                return tool

        # Check JS build tools
        for file_name, tool in self.JS_BUILD_FILES.items():
            if (path / file_name).exists():
                return tool

        return ""

    def _count_files(self, path: Path, info: ProjectInfo):
        """Count source files by type."""
        for item in path.rglob('*'):
            if item.is_file():
                # Skip ignored directories
                if any(ignored in str(item) for ignored in self.config.IGNORED_DIRS):
                    continue

                suffix = item.suffix.lower()
                if suffix == '.java':
                    info.java_file_count += 1
                elif suffix in ['.py', '.pyw']:
                    info.python_file_count += 1
                elif suffix in ['.js', '.jsx', '.ts', '.tsx', '.mjs']:
                    info.js_file_count += 1

    def _detect_java_version(self, path: Path) -> Optional[str]:
        """Detect Java version from build files."""
        # Check pom.xml for Maven
        pom_xml = path / 'pom.xml'
        if pom_xml.exists():
            try:
                content = pom_xml.read_text(encoding='utf-8', errors='ignore')
                # Look for java.version or maven.compiler.source
                import re
                match = re.search(r'<java\.version>(\d+)</java\.version>', content)
                if match:
                    return match.group(1)
                match = re.search(r'<maven\.compiler\.source>(\d+)</maven\.compiler\.source>', content)
                if match:
                    return match.group(1)
            except Exception:
                pass

        # Check build.gradle for Gradle
        for gradle_file in ['build.gradle', 'build.gradle.kts']:
            gradle_path = path / gradle_file
            if gradle_path.exists():
                try:
                    content = gradle_path.read_text(encoding='utf-8', errors='ignore')
                    import re
                    match = re.search(r'sourceCompatibility\s*=\s*[\'"]?(\d+)[\'"]?', content)
                    if match:
                        return match.group(1)
                    match = re.search(r'toolChain\.languageVersion\s*=\s*JavaLanguageVersion\.of\((\d+)\)', content)
                    if match:
                        return match.group(1)
                except Exception:
                    pass

        return None

    def _detect_java_frameworks_quick(self, path: Path) -> List[str]:
        """Quick framework detection from build files."""
        frameworks = []
        pom_xml = path / 'pom.xml'
        if pom_xml.exists():
            try:
                content = pom_xml.read_text(encoding='utf-8', errors='ignore').lower()
                if 'spring-' in content:
                    frameworks.append('spring')
                if 'jakarta.' in content or 'javax.' in content:
                    frameworks.append('jakarta-ee')
            except Exception:
                pass

        # Check Gradle files
        for gradle_file in ['build.gradle', 'build.gradle.kts']:
            gradle_path = path / gradle_file
            if gradle_path.exists():
                try:
                    content = gradle_path.read_text(encoding='utf-8', errors='ignore').lower()
                    if 'spring' in content:
                        if 'spring' not in frameworks:
                            frameworks.append('spring')
                except Exception:
                    pass

        return frameworks

    def _detect_java_frameworks(self, path: Path) -> List[str]:
        """Deep framework detection by scanning Java files."""
        frameworks = set()
        frameworks.update(self._detect_java_frameworks_quick(path))

        # Scan Java files for framework annotations
        for java_file in path.rglob('*.java'):
            if any(ignored in str(java_file) for ignored in self.config.IGNORED_DIRS):
                continue

            try:
                content = java_file.read_text(encoding='utf-8', errors='ignore').lower()
                for framework, indicators in self.JAVA_FRAMEWORKS.items():
                    if any(indicator.lower() in content for indicator in indicators):
                        frameworks.add(framework)
            except Exception:
                pass

        return list(frameworks)

    def _detect_python_frameworks(self, path: Path) -> List[str]:
        """Detect Python frameworks."""
        frameworks = set()

        # Check requirements.txt
        req_file = path / 'requirements.txt'
        if req_file.exists():
            try:
                content = req_file.read_text(encoding='utf-8', errors='ignore').lower()
                for framework, indicators in self.PYTHON_FRAMEWORKS.items():
                    if any(indicator.lower() in content for indicator in indicators):
                        frameworks.add(framework)
            except Exception:
                pass

        # Scan Python files
        for py_file in path.rglob('*.py'):
            if any(ignored in str(py_file) for ignored in self.config.IGNORED_DIRS):
                continue

            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore').lower()
                for framework, indicators in self.PYTHON_FRAMEWORKS.items():
                    if any(indicator.lower() in content for indicator in indicators):
                        frameworks.add(framework)
            except Exception:
                pass

        return list(frameworks)

    def _detect_js_frameworks(self, path: Path) -> List[str]:
        """Detect JavaScript/TypeScript frameworks."""
        frameworks = set()

        # Check package.json
        package_json = path / 'package.json'
        if package_json.exists():
            try:
                content = package_json.read_text(encoding='utf-8', errors='ignore').lower()
                for framework, indicators in self.JS_FRAMEWORKS.items():
                    if any(indicator.lower() in content for indicator in indicators):
                        frameworks.add(framework)
            except Exception:
                pass

        return list(frameworks)
