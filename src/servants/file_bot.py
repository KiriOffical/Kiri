"""
File Bot - Extension-based classification rules for Kiri Assistant.

Deterministic file classification using extension matching, content signatures,
and keyword patterns. All processing happens locally with no external calls.

Design Pillars:
- Local-First: All classification happens locally
- Security Gate: Files scanned for secrets before classification  
- Transparency: Rules are explicit and configurable
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class Category(Enum):
    """File categories for organization."""
    DOCUMENTS = "Documents"
    IMAGES = "Images"
    AUDIO = "Audio"
    VIDEO = "Video"
    CODE = "Code"
    ARCHIVES = "Archives"
    DATA = "Data"
    EXECUTABLES = "Executables"
    FONTS = "Fonts"
    WEB = "Web"
    CAD = "CAD"
    DISK = "Disk Images"
    OTHER = "Other"
    UNKNOWN = "Unknown"


@dataclass
class ClassificationResult:
    """Result of file classification."""
    category: Category
    confidence: float
    rule_matched: str
    extension: str
    content_signature: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.category.value} (confidence: {self.confidence:.2f}, rule: {self.rule_matched})"


# Extension rules: {category: [extensions]}
EXTENSION_RULES: Dict[Category, List[str]] = {
    Category.DOCUMENTS: [
        '.pdf', '.doc', '.docx', '.odt', '.rtf', '.tex', '.txt', '.md', '.rst',
        '.xls', '.xlsx', '.ods', '.csv', '.tsv', '.ppt', '.pptx', '.odp',
        '.epub', '.mobi', '.azw', '.djvu', '.xps'
    ],
    Category.IMAGES: [
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico',
        '.tiff', '.heic', '.raw', '.psd', '.ai', '.eps'
    ],
    Category.AUDIO: ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.alac'],
    Category.VIDEO: [
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.mpeg', '.3gp'
    ],
    Category.CODE: [
        '.py', '.js', '.ts', '.html', '.css', '.java', '.cpp', '.c', '.h',
        '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.sh', '.bash',
        '.sql', '.yaml', '.yml', '.json', '.xml', '.toml', '.ini', '.vue',
        '.dart', '.sol', '.ipynb', '.jl', '.env'
    ],
    Category.ARCHIVES: [
        '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar', '.tgz', '.iso'
    ],
    Category.DATA: [
        '.db', '.sqlite', '.parquet', '.avro', '.pickle', '.npy', '.mat', '.geojson'
    ],
    Category.EXECUTABLES: [
        '.exe', '.dll', '.so', '.bin', '.app', '.msi', '.deb', '.rpm', '.apk'
    ],
    Category.FONTS: ['.ttf', '.otf', '.woff', '.woff2', '.eot'],
    Category.WEB: ['.htm', '.xhtml', '.asp', '.aspx', '.jsp', '.php'],
    Category.CAD: ['.dwg', '.dxf', '.stp', '.stl', '.obj', '.fbx', '.blend'],
    Category.DISK: ['.iso', '.img', '.dmg', '.vhd', '.vmdk', '.qcow2'],
}

# Content signatures: {category: [(offset, pattern)]}
CONTENT_SIGNATURES: Dict[Category, List[Tuple[int, bytes]]] = {
    Category.DOCUMENTS: [(0, b'%PDF-')],
    Category.IMAGES: [
        (0, b'\xff\xd8\xff'),  # JPEG
        (0, b'\x89PNG\r\n\x1a\n'),  # PNG
        (0, b'GIF8'),  # GIF
        (0, b'BM'),  # BMP
    ],
    Category.ARCHIVES: [
        (0, b'PK\x03\x04'),  # ZIP
        (0, b'\x1f\x8b'),  # GZIP
        (0, b'BZh'),  # BZIP2
        (0, b'\xfd7zXZ\x00'),  # XZ
        (0, b'7z\xbc\xaf\x27\x1c'),  # 7Z
    ],
    Category.EXECUTABLES: [
        (0, b'MZ'),  # DOS/Windows
        (0, b'\x7fELF'),  # ELF
    ],
    Category.AUDIO: [
        (0, b'ID3'),  # MP3
        (0, b'OggS'),  # OGG
        (0, b'fLaC'),  # FLAC
    ],
    Category.VIDEO: [
        (0, b'\x1aE\xdf\xa3'),  # MKV
        (0, b'ftyp'),  # MP4/MOV
    ],
    Category.CODE: [(0, b'#!')],  # Shebang
    Category.DATA: [
        (0, b'SQLite format 3'),
        (0, b'\x89HDF'),
    ],
}

# Keyword patterns for ambiguous files
KEYWORD_PATTERNS: Dict[Category, List[re.Pattern]] = {
    Category.CODE: [
        re.compile(r'\b(def|class|import|function|var|let|const)\b', re.I),
        re.compile(r'#include\s*<', re.I),
    ],
    Category.DOCUMENTS: [
        re.compile(r'^\s*(abstract|conclusion|references)', re.I | re.M),
    ],
    Category.WEB: [
        re.compile(r'<html', re.I),
        re.compile(r'<script', re.I),
    ],
    Category.DATA: [
        re.compile(r'^\s*(SELECT|INSERT|UPDATE|DELETE)\s', re.I | re.M),
    ],
}


class FileBot:
    """Deterministic file classifier using rules and content analysis."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize with optional custom configuration."""
        self.config = config or {}
        
        # Build extension lookup table
        self._ext_to_category: Dict[str, Category] = {}
        for cat, exts in EXTENSION_RULES.items():
            for ext in exts:
                self._ext_to_category[ext.lower()] = cat
        
        # Load custom rules if provided
        if 'custom_extensions' in self.config:
            self._load_custom_rules(self.config['custom_extensions'])
    
    def _load_custom_rules(self, rules: Dict[str, List[str]]):
        """Load custom extension rules from config."""
        for cat_name, exts in rules.items():
            try:
                cat = Category[cat_name.upper()]
                for ext in exts:
                    self._ext_to_category[ext.lower()] = cat
            except KeyError:
                continue
    
    def classify_file(self, file_path: str) -> ClassificationResult:
        """
        Classify a file using extension → signature → keyword fallback chain.
        
        Args:
            file_path: Path to file
            
        Returns:
            ClassificationResult with category and confidence score
        """
        path = Path(file_path)
        
        if not path.exists():
            return ClassificationResult(
                category=Category.UNKNOWN, confidence=0.0,
                rule_matched="file_not_found", extension=""
            )
        
        ext = path.suffix.lower()
        
        # Priority 1: Extension match (highest confidence)
        if ext in self._ext_to_category:
            return ClassificationResult(
                category=self._ext_to_category[ext],
                confidence=0.9,
                rule_matched=f"extension:{ext}",
                extension=ext
            )
        
        # Priority 2: Content signature match
        sig_result = self._check_signatures(path)
        if sig_result:
            category, pattern_hex = sig_result
            return ClassificationResult(
                category=category,
                confidence=0.8,
                rule_matched=f"signature:{pattern_hex}",
                extension=ext,
                content_signature=pattern_hex
            )
        
        # Priority 3: Keyword pattern match
        kw_result = self._check_keywords(path)
        if kw_result:
            category, pattern = kw_result
            return ClassificationResult(
                category=category,
                confidence=0.6,
                rule_matched=f"keyword:{pattern}",
                extension=ext
            )
        
        # Default: Unknown
        return ClassificationResult(
            category=Category.UNKNOWN,
            confidence=0.0,
            rule_matched="no_match",
            extension=ext
        )
    
    def _check_signatures(self, path: Path) -> Optional[Tuple[Category, str]]:
        """Check file header against known magic bytes."""
        try:
            with open(path, 'rb') as f:
                header = f.read(512)
            
            if len(header) < 4:
                return None
            
            for category, signatures in CONTENT_SIGNATURES.items():
                for offset, pattern in signatures:
                    end = offset + len(pattern)
                    if end <= len(header) and header[offset:end] == pattern:
                        return (category, pattern.hex())
            
            return None
        except (IOError, PermissionError):
            return None
    
    def _check_keywords(self, path: Path) -> Optional[Tuple[Category, str]]:
        """Check file content against keyword patterns."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024)
            
            for category, patterns in KEYWORD_PATTERNS.items():
                for pattern in patterns:
                    if pattern.search(content):
                        return (category, pattern.pattern)
            
            return None
        except (IOError, PermissionError, UnicodeDecodeError):
            return None
    
    @staticmethod
    def get_category_folder(category: Category) -> str:
        """Get folder name for a category."""
        return category.value
    
    @staticmethod
    def get_all_categories() -> List[Category]:
        """Return all available categories."""
        return list(Category)
    
    def get_extensions_for_category(self, category: Category) -> List[str]:
        """Get all extensions for a specific category."""
        return EXTENSION_RULES.get(category, [])
