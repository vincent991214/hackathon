"""
EJB RAG Builder Module - Interface-Centric Storage

This module creates "Super-Context" chunks for ChromaDB storage.
Each chunk contains Interface + Implementation Bean + Related DTOs for complete context.
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass

from utils.ejb_parser import EJBInterfaceInfo, EJBParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SuperContext:
    """Data class representing a Super-Context chunk."""
    interface_name: str
    interface_code: str
    bean_code: Optional[str]
    dto_codes: Dict[str, str]
    entity_codes: Dict[str, str]
    metadata: Dict[str, Any]


class EJBRAGBuilder:
    """
    RAG Builder for EJB projects.

    Creates interface-centric "Super-Context" chunks that combine:
    - Interface Definition
    - Implementation Bean
    - Related DTOs
    - Related Entities

    This context is stored in ChromaDB for retrieval during AI generation.
    """

    def __init__(self, project_path: str, symbol_table: Dict[str, str], interfaces: List[EJBInterfaceInfo]):
        """
        Initialize the RAG Builder.

        Args:
            project_path: Root directory of the EJB project
            symbol_table: Mapping of class names to file paths
            interfaces: List of discovered EJB interfaces
        """
        self.project_path = Path(project_path)
        self.symbol_table = symbol_table
        self.interfaces = interfaces
        self.super_contexts: List[SuperContext] = []

    def build_all_super_contexts(self) -> List[SuperContext]:
        """
        Build Super-Context for all discovered interfaces.

        Returns:
            List of SuperContext objects
        """
        logger.info(f"Building Super-Contexts for {len(self.interfaces)} interfaces")

        for interface_info in self.interfaces:
            try:
                super_context = self._build_super_context(interface_info)
                if super_context:
                    self.super_contexts.append(super_context)
            except Exception as e:
                logger.warning(f"Failed to build Super-Context for {interface_info.interface_name}: {e}")

        logger.info(f"Built {len(self.super_contexts)} Super-Contexts")
        return self.super_contexts

    def _build_super_context(self, interface_info: EJBInterfaceInfo) -> Optional[SuperContext]:
        """
        Build a single Super-Context for an interface.

        Args:
            interface_info: The EJB interface information

        Returns:
            SuperContext object or None if building failed
        """
        # Read interface code
        interface_code = self._read_file_content(interface_info.file_path)
        if not interface_code:
            return None

        # Read bean code if available
        bean_code = None
        if interface_info.bean_class and interface_info.bean_class in self.symbol_table:
            bean_path = self.symbol_table[interface_info.bean_class]
            bean_code = self._read_file_content(bean_path)

        # Read related DTOs
        dto_codes = {}
        for dto_name in interface_info.related_dtos:
            if dto_name in self.symbol_table:
                dto_path = self.symbol_table[dto_name]
                dto_code = self._read_file_content(dto_path)
                if dto_code:
                    dto_codes[dto_name] = dto_code

        # Read related entities
        entity_codes = {}
        for entity_name in interface_info.related_entities:
            if entity_name in self.symbol_table:
                entity_path = self.symbol_table[entity_name]
                entity_code = self._read_file_content(entity_path)
                if entity_code:
                    entity_codes[entity_name] = entity_code

        # Create metadata (ChromaDB only accepts primitive types: str, int, float, bool, None)
        # Note: methods list is stored in SuperContext.metadata but excluded from ChromaDB
        chromadb_metadata = {
            "interface_name": interface_info.interface_name,
            "package": interface_info.package,
            "interface_type": interface_info.interface_type,
            "bean_class": interface_info.bean_class or "",
            "has_bean": bean_code is not None,
            "dto_count": len(dto_codes),
            "entity_count": len(entity_codes),
            "method_count": len(interface_info.methods)
        }

        # Full metadata includes methods list for internal use
        full_metadata = chromadb_metadata.copy()
        full_metadata["methods"] = [m['name'] for m in interface_info.methods]

        return SuperContext(
            interface_name=interface_info.interface_name,
            interface_code=interface_code,
            bean_code=bean_code,
            dto_codes=dto_codes,
            entity_codes=entity_codes,
            metadata=full_metadata
        )

    def _read_file_content(self, file_path: str) -> Optional[str]:
        """
        Read the content of a file.

        Args:
            file_path: Path to the file

        Returns:
            File content as string or None if reading failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None

    def format_super_context(self, super_context: SuperContext) -> str:
        """
        Format a Super-Context as a structured string for AI consumption.

        Args:
            super_context: The SuperContext to format

        Returns:
            Formatted string containing all code sections
        """
        sections = []

        # Interface Definition
        sections.append("// --- Interface Definition ---")
        sections.append(f"// File: {super_context.interface_name}")
        sections.append(super_context.interface_code)
        sections.append("")

        # Implementation Bean
        if super_context.bean_code:
            sections.append("// --- Implementation Bean ---")
            if super_context.metadata.get("bean_class"):
                sections.append(f"// Class: {super_context.metadata['bean_class']}")
            sections.append(super_context.bean_code)
            sections.append("")

        # Related DTOs
        if super_context.dto_codes:
            sections.append("// --- Related DTOs ---")
            for dto_name, dto_code in super_context.dto_codes.items():
                sections.append(f"// DTO: {dto_name}")
                sections.append(dto_code)
                sections.append("")

        # Related Entities
        if super_context.entity_codes:
            sections.append("// --- Related Entities ---")
            for entity_name, entity_code in super_context.entity_codes.items():
                sections.append(f"// Entity: {entity_name}")
                sections.append(entity_code)
                sections.append("")

        return "\n".join(sections)

    def save_super_contexts_to_file(self, output_dir: str):
        """
        Save all Super-Contexts to individual files.

        Args:
            output_dir: Directory where files will be saved
        """
        os.makedirs(output_dir, exist_ok=True)

        for super_context in self.super_contexts:
            filename = f"{super_context.interface_name}_context.txt"
            filepath = os.path.join(output_dir, filename)

            formatted_context = self.format_super_context(super_context)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted_context)

        logger.info(f"Saved {len(self.super_contexts)} Super-Context files to {output_dir}")


class ChromaDBManager:
    """
    Manager for ChromaDB operations.

    Handles storing and retrieving Super-Contexts using ChromaDB.
    """

    def __init__(self, collection_name: str = "ejb_interfaces", persist_directory: str = "./chroma_db"):
        """
        Initialize the ChromaDB manager.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory for persistent storage
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.collection = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize ChromaDB client and get/create collection."""
        try:
            import chromadb
            from chromadb.config import Settings

            # Create persistent client
            self.client = chromadb.PersistentClient(path=self.persist_directory)

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "EJB Interface Super-Contexts"}
            )

            logger.info(f"ChromaDB initialized: collection '{self.collection_name}'")

        except ImportError:
            logger.warning("chromadb not installed. Install with: pip install chromadb")
            self.collection = None
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.collection = None

    def add_super_contexts(self, super_contexts: List[SuperContext]):
        """
        Add Super-Contexts to ChromaDB.

        Args:
            super_contexts: List of SuperContext objects to add
        """
        if not self.collection:
            logger.error("ChromaDB collection not initialized")
            return

        if not super_contexts:
            logger.warning("No Super-Contexts to add")
            return

        ids = []
        documents = []
        metadatas = []

        for sc in super_contexts:
            # Create a unique ID
            doc_id = f"{sc.interface_name}_{hash(sc.interface_code)}"

            # Format the Super-Context as the document
            formatted_doc = self._format_for_chroma(sc)

            # Filter metadata to only include ChromaDB-compatible types
            # (str, int, float, bool, None) - exclude lists and dicts
            chroma_metadata = {}
            for key, value in sc.metadata.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    chroma_metadata[key] = value
                # Skip lists, dicts, and other complex types

            ids.append(doc_id)
            documents.append(formatted_doc)
            metadatas.append(chroma_metadata)

        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Added {len(super_contexts)} Super-Contexts to ChromaDB")
        except Exception as e:
            logger.error(f"Failed to add to ChromaDB: {e}")

    def _format_for_chroma(self, super_context: SuperContext) -> str:
        """
        Format a Super-Context for ChromaDB storage.

        Similar to format_super_context but optimized for retrieval.
        """
        sections = []

        # Summary section for better matching
        sections.append(f"INTERFACE: {super_context.interface_name}")
        sections.append(f"PACKAGE: {super_context.metadata.get('package', 'N/A')}")
        sections.append(f"TYPE: {super_context.metadata.get('interface_type', 'N/A')}")

        if super_context.metadata.get('methods'):
            sections.append(f"METHODS: {', '.join(super_context.metadata['methods'])}")

        sections.append("")

        # Full code
        sections.append(self._format_full_code(super_context))

        return "\n".join(sections)

    def _format_full_code(self, super_context: SuperContext) -> str:
        """Format the full code section."""
        sections = []

        sections.append("// --- Interface Definition ---")
        sections.append(super_context.interface_code)
        sections.append("")

        if super_context.bean_code:
            sections.append("// --- Implementation Bean ---")
            sections.append(super_context.bean_code)
            sections.append("")

        if super_context.dto_codes:
            sections.append("// --- Related DTOs ---")
            for dto_name, dto_code in super_context.dto_codes.items():
                sections.append(f"// DTO: {dto_name}")
                sections.append(dto_code)

        if super_context.entity_codes:
            sections.append("// --- Related Entities ---")
            for entity_name, entity_code in super_context.entity_codes.items():
                sections.append(f"// Entity: {entity_name}")
                sections.append(entity_code)

        return "\n".join(sections)

    def query_by_interface_name(self, interface_name: str, n_results: int = 1) -> List[Dict[str, Any]]:
        """
        Query ChromaDB by interface name.

        Args:
            interface_name: Name of the interface to find
            n_results: Maximum number of results to return

        Returns:
            List of matching documents with metadata
        """
        if not self.collection:
            logger.error("ChromaDB collection not initialized")
            return []

        try:
            results = self.collection.query(
                query_texts=[f"INTERFACE: {interface_name}"],
                n_results=n_results
            )

            if not results or not results.get('documents'):
                logger.warning(f"No results found for interface: {interface_name}")
                return []

            formatted_results = []
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'document': doc,
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                    'distance': results['distances'][0][i] if results.get('distances') else None
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            return []

    def query_by_method(self, method_name: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Query ChromaDB by method name.

        Args:
            method_name: Name of the method to find
            n_results: Maximum number of results to return

        Returns:
            List of matching documents with metadata
        """
        if not self.collection:
            logger.error("ChromaDB collection not initialized")
            return []

        try:
            results = self.collection.query(
                query_texts=[f"METHOD: {method_name}"],
                n_results=n_results
            )

            if not results or not results.get('documents'):
                return []

            formatted_results = []
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'document': doc,
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                    'distance': results['distances'][0][i] if results.get('distances') else None
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            return []

    def get_all_interface_names(self) -> List[str]:
        """
        Get all interface names stored in ChromaDB.

        Returns:
            List of interface names
        """
        if not self.collection:
            return []

        try:
            results = self.collection.get()
            interface_names = []

            if results and results.get('metadatas'):
                for metadata in results['metadatas']:
                    interface_name = metadata.get('interface_name')
                    if interface_name and interface_name not in interface_names:
                        interface_names.append(interface_name)

            return sorted(interface_names)

        except Exception as e:
            logger.error(f"Failed to get interface names: {e}")
            return []

    def clear_collection(self):
        """Clear all data from the collection."""
        if not self.collection:
            return

        try:
            # Delete and recreate the collection
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "EJB Interface Super-Contexts"}
            )
            logger.info(f"Cleared collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")


def build_and_store_rag(project_path: str, symbol_table: Dict[str, str],
                         interfaces: List[EJBInterfaceInfo]) -> ChromaDBManager:
    """
    Complete pipeline: Build Super-Contexts and store in ChromaDB.

    Args:
        project_path: Path to the EJB project
        symbol_table: Mapping of class names to file paths
        interfaces: List of discovered EJB interfaces

    Returns:
        ChromaDBManager instance with stored data
    """
    # Build Super-Contexts
    rag_builder = EJBRAGBuilder(project_path, symbol_table, interfaces)
    super_contexts = rag_builder.build_all_super_contexts()

    # Save to files (backup)
    output_dir = os.path.join(project_path, ".ejb_contexts")
    rag_builder.save_super_contexts_to_file(output_dir)

    # Store in ChromaDB
    chroma_manager = ChromaDBManager()
    chroma_manager.clear_collection()  # Clear old data
    chroma_manager.add_super_contexts(super_contexts)

    logger.info(f"RAG pipeline complete: {len(super_contexts)} interfaces stored")

    return chroma_manager
