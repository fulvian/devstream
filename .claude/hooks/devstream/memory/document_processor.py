#!/usr/bin/env python3
"""
DevStream Memory Bootstrap - Document Processor
Context7-compliant document processing using LangChain patterns.

This module provides intelligent document loading, chunking, and processing
capabilities for project memory initialization using best practices from
LangChain, ChromaDB, and modern RAG systems.

Key Features:
- Multi-format document loaders (Python, Markdown, Text, etc.)
- Intelligent chunking with overlap for context preservation
- Metadata extraction and enrichment
- Batch processing for performance optimization
- Source-based deduplication support
Context7 Pattern: Lazy loading + batch processing + metadata enrichment
"""

import os
import ast
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator, Tuple, Iterable, Set
from dataclasses import dataclass, field
import logging
import time
import json
from datetime import datetime

# Context7 Pattern: Graceful dependency handling
try:
    from langchain_core.documents import Document
    from langchain_text_splitters import (
        RecursiveCharacterTextSplitter,
        Language,
        PythonCodeTextSplitter
    )
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Context7 Fallback: Define minimal Document class
    LANGCHAIN_AVAILABLE = False
    logging.warning("LangChain not available, using fallback document processing")

    @dataclass
    class Document:
        page_content: str
        metadata: Dict[str, Any] = field(default_factory=dict)


DEFAULT_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB

DEFAULT_CODE_EXTENSIONS: Set[str] = {
    '.py', '.pyi', '.ts', '.tsx', '.js', '.jsx', '.go', '.rs', '.java', '.rb'
}
DEFAULT_DOC_EXTENSIONS: Set[str] = {
    '.md', '.rst', '.txt'
}
DEFAULT_CONFIG_EXTENSIONS: Set[str] = {
    '.json', '.toml', '.yml', '.yaml', '.cfg', '.ini', '.env', '.properties'
}
DEFAULT_ALLOWED_EXTENSIONS: Set[str] = (
    DEFAULT_CODE_EXTENSIONS
    | DEFAULT_DOC_EXTENSIONS
    | DEFAULT_CONFIG_EXTENSIONS
)

DEFAULT_PRIORITY_DIRECTORIES: Tuple[str, ...] = (
    'src',
    'app',
    'backend',
    'frontend',
    'docs',
    'config',
    'include',
    'lib',
    'services',
    'packages',
)

DEFAULT_HIGH_VALUE_FILES: Tuple[str, ...] = (
    'README.md',
    'README.rst',
    'CONTRIBUTING.md',
    'CHANGELOG.md',
    'pyproject.toml',
    'package.json',
)

DEFAULT_EXCLUDE_DIRS: Set[str] = {
    '.git',
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    '.tox',
    '.venv',
    'venv',
    '.devstream',
    '.reporting',
    'reporting',
    'node_modules',
    'dist',
    'build',
    'htmlcov',
    'registrazioni',
    '.DS_Store',
    '.accountabilly',
    'site-packages',
}

DEFAULT_EXCLUDE_PATTERNS: Tuple[str, ...] = (
    '*.min.js',
    '*.bundle.js',
    '*.lock',
    '*.log',
    '*.tmp',
    '*.cache',
    '*.png',
    '*.jpg',
    '*.jpeg',
    '*.gif',
    '*.pdf',
)


@dataclass
class ProcessedDocument:
    """Enhanced document with processing metadata."""
    content: str
    metadata: Dict[str, Any]
    source_path: str
    content_type: str
    chunk_count: int = 0
    processing_time: float = 0.0
    checksum: str = ""


class DocumentProcessor:
    """
    Context7-compliant document processor for memory bootstrap.

    Implements LangChain patterns for:
    - Multi-format document loading
    - Intelligent chunking with overlap
    - Metadata extraction and enrichment
    - Batch processing for performance
    - Source-based deduplication
    """

    def __init__(self, project_root: str, batch_size: int = 50, config: Optional[Dict[str, Any]] = None):
        """
        Initialize document processor.

        Args:
            project_root: Root path of the project to process
            batch_size: Number of documents to process in each batch
        """
        self.project_root = Path(project_root).resolve()
        self.batch_size = batch_size
        self.config = config or {}

        # Resolve configuration with sensible defaults
        self.max_file_size_bytes = int(
            self.config.get("max_file_size_bytes", DEFAULT_MAX_FILE_SIZE_BYTES)
        )

        def _normalize_ext(values: Iterable[str], default: Set[str]) -> Set[str]:
            result: Set[str] = set(default)
            for ext in values:
                if not ext:
                    continue
                ext = ext if ext.startswith(".") else f".{ext}"
                result.add(ext.lower())
            return result

        self.code_extensions = _normalize_ext(
            self.config.get("code_extensions", []),
            DEFAULT_CODE_EXTENSIONS,
        )
        self.doc_extensions = _normalize_ext(
            self.config.get("doc_extensions", []),
            DEFAULT_DOC_EXTENSIONS,
        )
        self.config_extensions = _normalize_ext(
            self.config.get("config_extensions", []),
            DEFAULT_CONFIG_EXTENSIONS,
        )
        self.allowed_extensions = (
            self.code_extensions | self.doc_extensions | self.config_extensions
        )

        self.exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
        for value in self.config.get("exclude_dirs", []):
            if value:
                self.exclude_dirs.add(value)

        self.exclude_patterns = set(DEFAULT_EXCLUDE_PATTERNS)
        for value in self.config.get("exclude_patterns", []):
            if value:
                self.exclude_patterns.add(value)

        self.include_directories: Tuple[str, ...] = tuple(
            self.config.get("include_directories", DEFAULT_PRIORITY_DIRECTORIES)
        )
        self.include_patterns: List[str] = list(self.config.get("include_patterns", []))
        self.priority_files = set(DEFAULT_HIGH_VALUE_FILES)
        for value in self.config.get("priority_files", []):
            if value:
                self.priority_files.add(value)
        self.include_hidden = bool(self.config.get("include_hidden", False))

        # Context7 Pattern: Language-specific splitters
        if LANGCHAIN_AVAILABLE:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )

            self.code_splitter = PythonCodeTextSplitter(
                chunk_size=800,
                chunk_overlap=100,
                length_function=len
            )
            self.text_chunker = self.text_splitter.split_text
            self.code_chunker = self.code_splitter.split_text
        else:
            # Fallback splitter
            self.text_splitter = self._fallback_text_chunks
            self.text_chunker = self._fallback_text_chunks
            self.code_chunker = self._fallback_code_chunks
            self.code_splitter = None

        # Supported file types and their processors
        self.file_processors = {
            '.py': self._process_python_file,
            '.md': self._process_markdown_file,
            '.rst': self._process_rst_file,
            '.txt': self._process_text_file,
            '.yml': self._process_yaml_file,
            '.yaml': self._process_yaml_file,
            '.json': self._process_json_file,
            '.toml': self._process_toml_file,
            '.cfg': self._process_config_file,
            '.ini': self._process_config_file,
        }
        for ext in sorted(self.code_extensions):
            if ext not in self.file_processors:
                self.file_processors[ext] = self._process_text_file
        for ext in sorted(self.doc_extensions | self.config_extensions):
            if ext not in self.file_processors:
                self.file_processors[ext] = self._process_text_file

        # Content type mapping
        self.content_type_mapping: Dict[str, str] = {}
        for ext in self.code_extensions:
            self.content_type_mapping[ext] = 'code'
        for ext in self.doc_extensions:
            self.content_type_mapping[ext] = 'documentation'
        for ext in self.config_extensions:
            self.content_type_mapping[ext] = 'configuration'
        # Generic fallback
        self.content_type_mapping.setdefault('.txt', 'text')

        self.logger = logging.getLogger(__name__)

    def _chunk_with_overlap(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[str]:
        """Generic chunker used by fallback implementations."""
        if not text:
            return []

        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(text_len, start + chunk_size)

            if end < text_len:
                # Prefer to split at whitespace boundary
                boundary = text.rfind("\n\n", start, end)
                if boundary == -1:
                    boundary = text.rfind("\n", start, end)
                if boundary == -1:
                    boundary = text.rfind(" ", start, end)
                if boundary != -1 and boundary > start:
                    end = boundary

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end == text_len:
                break

            start = max(0, end - chunk_overlap)

        return chunks

    def _fallback_text_chunks(self, text: str) -> List[str]:
        """Fallback chunking for documentation/text files."""
        return self._chunk_with_overlap(text, chunk_size=1000, chunk_overlap=200)

    def _fallback_code_chunks(self, text: str) -> List[str]:
        """Fallback chunking for code when LangChain is unavailable."""
        if not text:
            return []

        pattern = re.compile(r'(?=^\\s*(def|class|async\\s+def)\\s)', re.MULTILINE)
        positions = [match.start() for match in pattern.finditer(text)]

        if not positions:
            return self._chunk_with_overlap(text, chunk_size=800, chunk_overlap=120)

        positions.append(len(text))
        chunks: List[str] = []

        for idx in range(len(positions) - 1):
            start = positions[idx]
            end = positions[idx + 1]
            chunk = text[start:end].strip()
            if chunk:
                chunks.extend(self._chunk_with_overlap(chunk, 800, 120))

        return chunks or self._chunk_with_overlap(text, 800, 120)

    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA-256 checksum for content deduplication."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract rich metadata from file path and content.

        Context7 Pattern: Multi-dimensional metadata for better search.
        """
        # Context7 Pattern: Safe relative path calculation
        file_path_abs = file_path.resolve()
        project_root_abs = self.project_root.resolve()

        try:
            relative_path = file_path_abs.relative_to(project_root_abs)
        except ValueError:
            # File is outside project root, skip processing
            raise ValueError(f"File {file_path} is outside project root {project_root_abs}")

        stats = file_path.stat() if file_path.exists() else None
        size_bytes = stats.st_size if stats else 0
        modified_time = stats.st_mtime if stats else 0.0

        metadata: Dict[str, Any] = {
            'source': str(relative_path),
            'relative_path': str(relative_path),
            'absolute_path': str(file_path),
            'filename': file_path.name,
            'extension': file_path.suffix.lower(),
            'directory': str(relative_path.parent),
            'size_bytes': size_bytes,
            'modified_time': modified_time,
            'modified_time_iso': datetime.fromtimestamp(modified_time).isoformat() if stats else None,
            'project_root': str(self.project_root),
            'priority_file': file_path.name in self.priority_files,
            'top_level_dir': relative_path.parts[0] if relative_path.parts else '',
        }

        lower_parts = [part.lower() for part in relative_path.parts]
        category = 'general'
        if any(part in ('docs', 'documentation') for part in lower_parts):
            category = 'documentation'
        elif any(part in ('test', 'tests') for part in lower_parts):
            category = 'test'
        elif any(part in ('config', 'configs', 'settings') for part in lower_parts):
            category = 'configuration'
        elif file_path.suffix.lower() in self.code_extensions:
            category = 'code'

        metadata['category'] = category
        return metadata

    def _process_python_file(self, file_path: Path) -> ProcessedDocument:
        """
        Process Python file with AST analysis.

        Context7 Pattern: Structural analysis for code understanding.
        """
        start_time = time.time()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST for structural information
            try:
                tree = ast.parse(content)

                # Extract structural information
                functions = []
                classes = []
                imports = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        functions.append({
                            'name': node.name,
                            'line_start': node.lineno,
                            'line_end': getattr(node, 'end_lineno', node.lineno),
                            'args': [arg.arg for arg in node.args.args]
                        })
                    elif isinstance(node, ast.ClassDef):
                        classes.append({
                            'name': node.name,
                            'line_start': node.lineno,
                            'line_end': getattr(node, 'end_lineno', node.lineno),
                            'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                        })
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            imports.extend([alias.name for alias in node.names])
                        else:
                            imports.append(f"from {node.module}" if node.module else "from .")

                # Enhanced metadata with AST information
                metadata = self._extract_metadata(file_path)
                metadata.update({
                    'language': 'python',
                    'functions': functions,
                    'classes': classes,
                    'imports': imports,
                    'complexity_score': len(functions) + len(classes) * 2,
                    'content_type': 'code'
                })

            except SyntaxError:
                # Fallback for files with syntax errors
                metadata = self._extract_metadata(file_path)
                metadata.update({
                    'language': 'python',
                    'syntax_error': True,
                    'content_type': 'code'
                })

            # Calculate checksum
            checksum = self._calculate_checksum(content)

            processing_time = time.time() - start_time

            return ProcessedDocument(
                content=content,
                metadata=metadata,
                source_path=str(file_path),
                content_type='code',
                processing_time=processing_time,
                checksum=checksum
            )

        except Exception as e:
            self.logger.error(f"Error processing Python file {file_path}: {e}")
            raise

    def _process_markdown_file(self, file_path: Path) -> ProcessedDocument:
        """
        Process Markdown file with structure extraction.

        Context7 Pattern: Document structure analysis for better chunking.
        """
        start_time = time.time()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract markdown structure
            lines = content.split('\n')
            headers = []
            sections = []
            current_section = None

            for line_num, line in enumerate(lines, 1):
                if line.startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    title = line.lstrip('# ').strip()

                    header_info = {
                        'level': level,
                        'title': title,
                        'line': line_num
                    }
                    headers.append(header_info)

                    # Track sections
                    if current_section:
                        current_section['end_line'] = line_num - 1
                        sections.append(current_section)

                    current_section = {
                        'title': title,
                        'level': level,
                        'start_line': line_num,
                        'content': ''
                    }
                elif current_section:
                    current_section['content'] += line + '\n'

            # Add final section
            if current_section:
                sections.append(current_section)

            # Enhanced metadata
            metadata = self._extract_metadata(file_path)
            metadata.update({
                'format': 'markdown',
                'headers': headers,
                'sections': sections,
                'header_count': len(headers),
                'content_type': 'documentation'
            })

            checksum = self._calculate_checksum(content)
            processing_time = time.time() - start_time

            return ProcessedDocument(
                content=content,
                metadata=metadata,
                source_path=str(file_path),
                content_type='documentation',
                processing_time=processing_time,
                checksum=checksum
            )

        except Exception as e:
            self.logger.error(f"Error processing Markdown file {file_path}: {e}")
            raise

    def _process_text_file(self, file_path: Path) -> ProcessedDocument:
        """Process plain text file."""
        start_time = time.time()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            metadata = self._extract_metadata(file_path)
            file_ext = file_path.suffix.lower()
            content_type = self.content_type_mapping.get(file_ext, metadata.get('category', 'text'))
            metadata.update({
                'format': 'text',
                'content_type': content_type,
                'category': metadata.get('category', content_type),
            })

            checksum = self._calculate_checksum(content)
            processing_time = time.time() - start_time

            return ProcessedDocument(
                content=content,
                metadata=metadata,
                source_path=str(file_path),
                content_type=content_type,
                processing_time=processing_time,
                checksum=checksum
            )

        except Exception as e:
            self.logger.error(f"Error processing text file {file_path}: {e}")
            raise

    def _process_rst_file(self, file_path: Path) -> ProcessedDocument:
        """Process reStructuredText file."""
        # Similar to markdown but with RST-specific parsing
        return self._process_markdown_file(file_path)

    def _process_yaml_file(self, file_path: Path) -> ProcessedDocument:
        """Process YAML configuration file."""
        return self._process_text_file(file_path)

    def _process_json_file(self, file_path: Path) -> ProcessedDocument:
        """Process JSON configuration file."""
        return self._process_text_file(file_path)

    def _process_toml_file(self, file_path: Path) -> ProcessedDocument:
        """Process TOML configuration file."""
        return self._process_text_file(file_path)

    def _process_config_file(self, file_path: Path) -> ProcessedDocument:
        """Process generic configuration file."""
        return self._process_text_file(file_path)

    def discover_documents(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        Discover documents in project directory.

        Context7 Pattern: Intelligent file discovery with scoped search roots.
        """
        combined_exclude_patterns = set(self.exclude_patterns)
        if exclude_patterns:
            combined_exclude_patterns.update(exclude_patterns)

        additional_include_patterns = list(include_patterns or [])
        additional_include_patterns.extend(self.include_patterns)

        candidate_paths: Set[Path] = set()

        search_roots = [
            self.project_root / directory
            for directory in self.include_directories
            if directory and (self.project_root / directory).exists()
        ]
        if not search_roots:
            search_roots = [self.project_root]

        for root in search_roots:
            for path in root.rglob('*'):
                if not path.is_file():
                    continue
                if self._should_exclude_file(path, combined_exclude_patterns):
                    continue
                if not self._is_allowed_extension(path):
                    continue
                if not self._within_size_limit(path):
                    continue
                candidate_paths.add(path.resolve())

        # Additional include patterns (explicit glob matches)
        for pattern in additional_include_patterns:
            for path in self.project_root.glob(pattern):
                if not path.is_file():
                    continue
                if self._should_exclude_file(path, combined_exclude_patterns):
                    continue
                if not self._is_allowed_extension(path):
                    continue
                if not self._within_size_limit(path):
                    continue
                candidate_paths.add(path.resolve())

        # Always include explicitly prioritized files if present
        for filename in self.priority_files:
            candidate = self.project_root / filename
            if (
                candidate.exists()
                and candidate.is_file()
                and not self._should_exclude_file(candidate, combined_exclude_patterns)
            ):
                candidate_paths.add(candidate.resolve())

        discovered_files = sorted(
            candidate_paths,
            key=lambda path: path.stat().st_mtime if path.exists() else 0,
            reverse=True,
        )

        self.logger.info(
            "Discovered %d candidate files (roots=%s)",
            len(discovered_files),
            ','.join(str(root.resolve().relative_to(self.project_root)) for root in search_roots if root != self.project_root),
        )
        return discovered_files

    def _is_allowed_extension(self, file_path: Path) -> bool:
        """Check whether the file extension is allowed for processing."""
        return file_path.suffix.lower() in self.allowed_extensions

    def _within_size_limit(self, file_path: Path) -> bool:
        """Ensure file size does not exceed configured limit."""
        try:
            return file_path.stat().st_size <= self.max_file_size_bytes
        except OSError:
            return False

    def _should_exclude_file(self, file_path: Path, exclude_patterns: Iterable[str]) -> bool:
        """
        Check if file should be excluded using multiple strategies.

        Context7 Pattern: Robust exclusion with path part inspection + pattern matching.
        """
        # Context7 Pattern: Safe relative path calculation for exclusion check
        file_path_abs = file_path.resolve()
        project_root_abs = self.project_root.resolve()

        try:
            relative_path = file_path_abs.relative_to(project_root_abs)
        except ValueError:
            return True

        parts = relative_path.parts
        if not self.include_hidden:
            if any(part.startswith('.') and part not in ('.', '..') for part in parts):
                return True

        for part in parts:
            if part in self.exclude_dirs:
                return True
            if part.endswith('.egg-info') or part.endswith('.dist-info'):
                return True

        if file_path.suffix.lower() in {'.pyc', '.pyo', '.pyd', '.so', '.dylib', '.swp', '.swo'}:
            return True

        relative_str = str(relative_path)
        for pattern in exclude_patterns:
            if not pattern:
                continue
            try:
                if relative_path.match(pattern):
                    return True
            except Exception:
                needle = pattern.strip('*').strip('/')
                if needle and needle in relative_str:
                    return True

        return False

    def process_document(self, file_path: Path) -> ProcessedDocument:
        """
        Process a single document.

        Context7 Pattern: Type-specific processing with metadata enrichment.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_ext = file_path.suffix.lower()
        processor = self.file_processors.get(file_ext)

        if not processor:
            raise ValueError(f"Unsupported file type: {file_ext}")

        return processor(file_path)

    def process_documents_batch(self, file_paths: List[Path]) -> List[ProcessedDocument]:
        """
        Process a batch of documents.

        Context7 Pattern: Batch processing for performance optimization.
        """
        processed_docs = []

        for file_path in file_paths:
            try:
                doc = self.process_document(file_path)
                processed_docs.append(doc)
            except Exception as e:
                self.logger.warning(f"Failed to process {file_path}: {e}")
                continue

        return processed_docs

    def chunk_document(self, processed_doc: ProcessedDocument) -> List[Document]:
        """
        Split processed document into chunks.

        Context7 Pattern: Intelligent chunking with metadata preservation.
        """
        content_type = processed_doc.content_type

        if content_type == 'code':
            chunks = self.code_chunker(processed_doc.content)
        else:
            chunks = self.text_chunker(processed_doc.content)

        if not chunks:
            chunks = [processed_doc.content]

        documents: List[Document] = []
        total = len(chunks)

        for index, chunk in enumerate(chunks):
            chunk_metadata = processed_doc.metadata.copy()
            chunk_metadata.update({
                'chunk_id': f"{processed_doc.source_path}:{index}",
                'chunk_index': index,
                'total_chunks': total,
                'chunk_size': len(chunk),
                'document_checksum': processed_doc.checksum,
                'chunk_content_type': content_type,
            })

            if LANGCHAIN_AVAILABLE:
                documents.append(Document(page_content=chunk, metadata=chunk_metadata))
            else:
                documents.append(Document(chunk, chunk_metadata))

        processed_doc.chunk_count = total
        return documents

    def lazy_process_documents(self, file_paths: List[Path]) -> Iterator[List[Document]]:
        """
        Lazily process documents in batches.

        Context7 Pattern: Memory-efficient lazy processing.
        """
        batch = []

        for file_path in file_paths:
            try:
                # Process single document
                processed_doc = self.process_document(file_path)

                # Chunk the document
                chunked_docs = self.chunk_document(processed_doc)
                batch.extend(chunked_docs)

                # Yield batch when it reaches the target size
                if len(batch) >= self.batch_size:
                    yield batch
                    batch = []

            except Exception as e:
                self.logger.warning(f"Failed to process {file_path}: {e}")
                continue

        # Yield remaining documents
        if batch:
            yield batch

    def get_processing_stats(self, processed_docs: List[ProcessedDocument]) -> Dict[str, Any]:
        """
        Get processing statistics.

        Context7 Pattern: Analytics for monitoring and optimization.
        """
        if not processed_docs:
            return {}

        total_files = len(processed_docs)
        total_chunks = sum(doc.chunk_count for doc in processed_docs)
        total_processing_time = sum(doc.processing_time for doc in processed_docs)

        # Content type distribution
        content_types = {}
        for doc in processed_docs:
            content_type = doc.content_type
            content_types[content_type] = content_types.get(content_type, 0) + 1

        # File type distribution
        file_types = {}
        for doc in processed_docs:
            ext = Path(doc.source_path).suffix
            file_types[ext] = file_types.get(ext, 0) + 1

        return {
            'total_files': total_files,
            'total_chunks': total_chunks,
            'total_processing_time': total_processing_time,
            'avg_processing_time': total_processing_time / total_files,
            'content_types': content_types,
            'file_types': file_types,
            'avg_chunks_per_file': total_chunks / total_files if total_files > 0 else 0
        }


# Context7 Pattern: Convenience function for quick usage
def create_document_processor(
    project_root: str,
    batch_size: int = 50,
    config: Optional[Dict[str, Any]] = None,
) -> DocumentProcessor:
    """
    Create a document processor instance.

    Args:
        project_root: Root path of the project
        batch_size: Batch processing size

    Returns:
        DocumentProcessor instance
    """
    return DocumentProcessor(project_root, batch_size, config)


# Context7 Pattern: Command-line interface for testing
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="DevStream Document Processor")
    parser.add_argument("project_root", help="Project root directory")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch processing size")
    parser.add_argument("--stats", action="store_true", help="Show processing statistics")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    processor = create_document_processor(args.project_root, args.batch_size)

    # Discover documents
    files = processor.discover_documents()
    print(f"Found {len(files)} files to process")

    if args.stats:
        # Process and show statistics
        processed_docs = processor.process_documents_batch(files)
        stats = processor.get_processing_stats(processed_docs)

        print("\n=== Processing Statistics ===")
        print(f"Total files: {stats['total_files']}")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Processing time: {stats['total_processing_time']:.2f}s")
        print(f"Avg time per file: {stats['avg_processing_time']:.2f}s")
        print(f"Avg chunks per file: {stats['avg_chunks_per_file']:.1f}")

        print("\nContent Types:")
        for content_type, count in stats['content_types'].items():
            print(f"  {content_type}: {count}")

        print("\nFile Types:")
        for file_type, count in stats['file_types'].items():
            print(f"  {file_type}: {count}")
