"""
Secret Scanner Module - Phase 1.3

Scans files and content for sensitive information including:
- API Keys (AWS, GitHub, Google, etc.)
- Private Keys (RSA, EC, DSA)
- Credentials (Passwords, Tokens)
- PII (Credit Cards, SSN, Phone Numbers)
"""

import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ScanStatus(Enum):
    SAFE = "safe"
    UNSAFE = "unsafe"
    ERROR = "error"


@dataclass
class SecretMatch:
    """Represents a detected secret pattern."""
    pattern_name: str
    match_value: str  # Masked for safety
    line_number: int
    column: int
    severity: str  # high, medium, low


@dataclass
class ScanResult:
    """Result of a secret scan."""
    status: ScanStatus
    file_path: Optional[str]
    matches: List[SecretMatch]
    message: str
    scanned_bytes: int = 0


class SecretScanner:
    """
    Scans content for sensitive patterns.
    
    Design Principles:
    - Fast: Only scans first 2KB by default
    - Safe: Masks detected secrets in logs
    - Configurable: Pattern library can be extended
    """
    
    def __init__(self, patterns: Optional[List[Dict]] = None):
        """
        Initialize scanner with pattern library.
        
        Args:
            patterns: List of pattern dicts with 'name' and 'pattern' keys
                     If None, uses default pattern set
        """
        self.patterns = patterns or self._get_default_patterns()
        self.compiled_patterns = self._compile_patterns()
    
    def _get_default_patterns(self) -> List[Dict]:
        """Return default secret detection patterns."""
        return [
            {
                "name": "AWS Access Key",
                "pattern": r"AKIA[0-9A-Z]{16}",
                "severity": "high"
            },
            {
                "name": "AWS Secret Key",
                "pattern": r"[A-Za-z0-9/+=]{40}",
                "severity": "high",
                "context": r"(?i)(aws_secret|secret_access_key)\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"
            },
            {
                "name": "GitHub Token",
                "pattern": r"gh[pousr]_[A-Za-z0-9_]{36,}",
                "severity": "high"
            },
            {
                "name": "GitHub Personal Access Token",
                "pattern": r"github_pat_[A-Za-z0-9_]{22,}",
                "severity": "high"
            },
            {
                "name": "Google API Key",
                "pattern": r"AIza[0-9A-Za-z_-]{35}",
                "severity": "high"
            },
            {
                "name": "Private Key Header",
                "pattern": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
                "severity": "critical"
            },
            {
                "name": "Generic API Key",
                "pattern": r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9]{20,}['\"]",
                "severity": "medium"
            },
            {
                "name": "Password Field",
                "pattern": r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
                "severity": "high"
            },
            {
                "name": "Bearer Token",
                "pattern": r"(?i)bearer\s+[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.]*",
                "severity": "high"
            },
            {
                "name": "JWT Token",
                "pattern": r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*",
                "severity": "high"
            },
            {
                "name": "Credit Card Number",
                "pattern": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
                "severity": "critical"
            },
            {
                "name": "SSN",
                "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
                "severity": "critical"
            },
            {
                "name": "Phone Number",
                "pattern": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
                "severity": "medium"
            },
            {
                "name": "Email Address",
                "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "severity": "low"
            }
        ]
    
    def _compile_patterns(self) -> List[tuple]:
        """Compile regex patterns for efficiency."""
        compiled = []
        for pattern_def in self.patterns:
            try:
                regex = re.compile(pattern_def["pattern"])
                compiled.append((
                    pattern_def["name"],
                    regex,
                    pattern_def.get("severity", "medium")
                ))
            except re.error as e:
                print(f"Warning: Invalid regex pattern '{pattern_def['name']}': {e}")
        return compiled
    
    def scan_content(self, content: str, source: str = "unknown") -> ScanResult:
        """
        Scan text content for secrets.
        
        Args:
            content: Text content to scan
            source: Source identifier (file path, email ID, etc.)
            
        Returns:
            ScanResult with status and any matches found
        """
        matches = []
        lines = content.split('\n')
        
        for pattern_name, regex, severity in self.compiled_patterns:
            for line_num, line in enumerate(lines, 1):
                for match in regex.finditer(line):
                    # Mask the matched value for safety
                    matched_text = match.group(0)
                    masked = self._mask_secret(matched_text)
                    
                    matches.append(SecretMatch(
                        pattern_name=pattern_name,
                        match_value=masked,
                        line_number=line_num,
                        column=match.start(),
                        severity=severity
                    ))
        
        # Sort by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        matches.sort(key=lambda m: severity_order.get(m.severity, 4))
        
        if matches:
            return ScanResult(
                status=ScanStatus.UNSAFE,
                file_path=source,
                matches=matches,
                message=f"Found {len(matches)} potential secret(s)",
                scanned_bytes=len(content.encode('utf-8'))
            )
        else:
            return ScanResult(
                status=ScanStatus.SAFE,
                file_path=source,
                matches=[],
                message="No secrets detected",
                scanned_bytes=len(content.encode('utf-8'))
            )
    
    def scan_file(self, file_path: str, max_size_kb: int = 2) -> ScanResult:
        """
        Scan a file for secrets.
        
        Args:
            file_path: Path to file to scan
            max_size_kb: Maximum kilobytes to read from file start
            
        Returns:
            ScanResult with status and any matches found
        """
        path = Path(file_path)
        
        if not path.exists():
            return ScanResult(
                status=ScanStatus.ERROR,
                file_path=str(file_path),
                matches=[],
                message="File does not exist"
            )
        
        if not path.is_file():
            return ScanResult(
                status=ScanStatus.ERROR,
                file_path=str(file_path),
                matches=[],
                message="Path is not a file"
            )
        
        try:
            # Read only first N KB for speed
            max_bytes = max_size_kb * 1024
            with open(path, 'rb') as f:
                raw_content = f.read(max_bytes)
            
            # Try to decode as text
            try:
                content = raw_content.decode('utf-8', errors='ignore')
            except Exception:
                content = raw_content.decode('latin-1', errors='ignore')
            
            return self.scan_content(content, source=str(file_path))
            
        except PermissionError:
            return ScanResult(
                status=ScanStatus.ERROR,
                file_path=str(file_path),
                matches=[],
                message="Permission denied"
            )
        except Exception as e:
            return ScanResult(
                status=ScanStatus.ERROR,
                file_path=str(file_path),
                matches=[],
                message=f"Error reading file: {str(e)}"
            )
    
    def _mask_secret(self, secret: str) -> str:
        """
        Mask a secret value for safe logging/display.
        
        Shows first 4 and last 4 characters, masks middle.
        """
        if len(secret) <= 8:
            return "*" * len(secret)
        
        visible_start = 4
        visible_end = 4
        mask_length = len(secret) - visible_start - visible_end
        
        return secret[:visible_start] + "*" * mask_length + secret[-visible_end:]
    
    def add_pattern(self, name: str, pattern: str, severity: str = "medium"):
        """
        Add a custom pattern to the scanner.
        
        Args:
            name: Human-readable name for the pattern
            pattern: Regex pattern string
            severity: critical, high, medium, or low
        """
        try:
            compiled = re.compile(pattern)
            self.patterns.append({
                "name": name,
                "pattern": pattern,
                "severity": severity
            })
            self.compiled_patterns.append((name, compiled, severity))
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
    
    def remove_pattern(self, name: str) -> bool:
        """
        Remove a pattern by name.
        
        Args:
            name: Name of pattern to remove
            
        Returns:
            True if pattern was found and removed, False otherwise
        """
        # Remove from patterns list
        original_count = len(self.patterns)
        self.patterns = [p for p in self.patterns if p["name"] != name]
        
        # Rebuild compiled patterns
        self.compiled_patterns = self._compile_patterns()
        
        return len(self.patterns) < original_count


# Convenience function for quick scanning
def scan_for_secrets(content: str, source: str = "unknown") -> ScanResult:
    """Quick scan content for secrets using default patterns."""
    scanner = SecretScanner()
    return scanner.scan_content(content, source)


def scan_file_for_secrets(file_path: str, max_size_kb: int = 2) -> ScanResult:
    """Quick scan file for secrets using default patterns."""
    scanner = SecretScanner()
    return scanner.scan_file(file_path, max_size_kb)
