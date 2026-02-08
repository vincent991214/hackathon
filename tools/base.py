"""
Base classes for code parsing tools.

This module provides the abstract base class and result format
for all parsing tools in the DevMate AI system.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Standard result format for all tools."""
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Optional[dict] = None


class BaseTool(ABC):
    """Abstract base class for all parsing tools."""

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def run(self, **kwargs) -> ToolResult:
        """Execute the tool's primary function."""
        pass
