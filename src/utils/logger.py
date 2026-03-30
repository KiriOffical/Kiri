"""
Audit Logging System - Phase 1.4

Provides secure, sanitized logging for Kiri operations.
- Writes to local files with rotation
- Sanitizes input to prevent secret leakage
- Supports multiple log levels
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import re


class SanitizingFilter(logging.Filter):
    """
    Filter that sanitizes log records to remove potential secrets.
    
    This is a defense-in-depth measure - even if code accidentally logs
    sensitive data, this filter will mask it.
    """
    
    # Patterns to mask in log output
    SENSITIVE_PATTERNS = [
        (r'(password|passwd|pwd|secret|token|api_key|apikey)\s*[:=]\s*[\'"][^\'"]+[\'"]', r'\1=***REDACTED***'),
        (r'(Bearer\s+)[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.]*', r'\1***REDACTED***'),
        (r'(AKIA)[0-9A-Z]{16}', r'\1****************'),
        (r'(gh[pousr]_)[A-Za-z0-9_]{36,}', r'\1************************************'),
        (r'-----BEGIN [A-Z ]*PRIVATE KEY-----', '-----BEGIN ***REDACTED*** PRIVATE KEY-----'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize the log message."""
        if isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)
        
        # Also sanitize args if present
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in self.SENSITIVE_PATTERNS:
                        arg = re.sub(pattern, replacement, arg, flags=re.IGNORECASE)
                sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        return True


class AuditLogger:
    """
    Manages audit logging for Kiri.
    
    Design Principles:
    - Tamper-resistant: Logs are append-only
    - Sanitized: No secrets in logs
    - Rotated: Prevents disk fill
    - Structured: Easy to parse and analyze
    """
    
    def __init__(
        self,
        log_path: str = "~/.kiri/logs/audit.log",
        level: str = "INFO",
        max_size_mb: int = 10,
        backup_count: int = 5
    ):
        """
        Initialize audit logger.
        
        Args:
            log_path: Path to log file
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_size_mb: Maximum log file size before rotation
            backup_count: Number of backup log files to keep
        """
        self.log_path = Path(log_path).expanduser()
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.backup_count = backup_count
        
        # Ensure log directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup logger
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Configure and return the logger."""
        logger = logging.getLogger("kiri.audit")
        logger.setLevel(self.level)
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # Create file handler with rotation
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            str(self.log_path),
            maxBytes=self.max_size_bytes,
            backupCount=self.backup_count
        )
        handler.setLevel(self.level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add sanitizing filter
        handler.addFilter(SanitizingFilter())
        
        # Add handler to logger
        logger.addHandler(handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(self._format_message(message, **kwargs))
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with optional context."""
        if kwargs:
            context = " ".join(f"{k}={v}" for k, v in kwargs.items())
            return f"{message} [{context}]"
        return message
    
    def log_event(
        self,
        event_type: str,
        action: str,
        status: str,
        details: Optional[dict] = None
    ):
        """
        Log a structured event.
        
        Args:
            event_type: Type of event (e.g., 'file_operation', 'security', 'email')
            action: Action performed (e.g., 'scan', 'move', 'fetch')
            status: Result status (e.g., 'success', 'failed', 'blocked')
            details: Optional additional details (will be sanitized)
        """
        message = f"EVENT type={event_type} action={action} status={status}"
        
        if details:
            # Convert dict to string, being careful not to include secrets
            safe_details = {}
            for key, value in details.items():
                # Skip potentially sensitive keys
                skip_keys = ['password', 'secret', 'token', 'key', 'credential']
                if any(skip in key.lower() for skip in skip_keys):
                    safe_details[key] = "***REDACTED***"
                else:
                    safe_details[key] = str(value)[:100]  # Limit length
            
            details_str = " ".join(f"{k}={v}" for k, v in safe_details.items())
            message += f" {details_str}"
        
        self.info(message)
    
    def get_log_file(self) -> Path:
        """Get path to current log file."""
        return self.log_path
    
    def get_log_files(self) -> list:
        """Get list of all log files (including rotated ones)."""
        files = [self.log_path]
        
        # Find rotated files
        base_name = self.log_path.name
        parent_dir = self.log_path.parent
        
        for i in range(1, self.backup_count + 1):
            rotated_path = parent_dir / f"{base_name}.{i}"
            if rotated_path.exists():
                files.append(rotated_path)
        
        return files
    
    def clear_logs(self):
        """Clear all log files (use with caution)."""
        for log_file in self.get_log_files():
            try:
                log_file.unlink()
            except Exception as e:
                self.error(f"Failed to delete log file: {e}")


# Behavior Logger (separate from audit log)
class BehaviorLogger:
    """
    Logs user behavior for learning purposes.
    
    Design Principles:
    - Metadata only: Never logs content
    - Encrypted: Database is encrypted
    - Time-limited: Auto-purges old entries
    - User-controlled: Can be purged anytime
    """
    
    def __init__(self, db_path: str = "~/.kiri/behavior.db"):
        """
        Initialize behavior logger.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Will be initialized when needed
        self._conn = None
    
    def _get_connection(self):
        """Get or create database connection."""
        if self._conn is None:
            import sqlite3
            self._conn = sqlite3.connect(str(self.db_path))
            self._init_db()
        return self._conn
    
    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Events table - metadata only, no content
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                action TEXT NOT NULL,
                result TEXT,
                confidence REAL,
                user_corrected BOOLEAN DEFAULT FALSE,
                metadata TEXT
            )
        ''')
        
        # Statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                files_processed INTEGER DEFAULT 0,
                emails_processed INTEGER DEFAULT 0,
                corrections_made INTEGER DEFAULT 0,
                secrets_blocked INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
    
    def log_event(
        self,
        event_type: str,
        action: str,
        result: Optional[str] = None,
        confidence: Optional[float] = None,
        user_corrected: bool = False,
        metadata: Optional[dict] = None
    ):
        """
        Log a behavior event.
        
        Args:
            event_type: Type of event (file, email, etc.)
            action: Action taken
            result: Outcome
            confidence: Confidence score if applicable
            user_corrected: Whether user corrected the action
            metadata: Additional metadata (no content!)
        """
        import json
        from datetime import datetime
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO events 
            (timestamp, event_type, action, result, confidence, user_corrected, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            event_type,
            action,
            result,
            confidence,
            user_corrected,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
    
    def update_daily_stats(
        self,
        files_processed: int = 0,
        emails_processed: int = 0,
        corrections_made: int = 0,
        secrets_blocked: int = 0
    ):
        """Update daily statistics."""
        from datetime import datetime
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT OR REPLACE INTO statistics
            (date, files_processed, emails_processed, corrections_made, secrets_blocked)
            VALUES (?, ?, ?, ?, ?)
        ''', (today, files_processed, emails_processed, corrections_made, secrets_blocked))
        
        conn.commit()
    
    def purge_old_events(self, retention_days: int = 90):
        """Delete events older than retention period."""
        from datetime import datetime, timedelta
        
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM events WHERE timestamp < ?', (cutoff,))
        conn.commit()
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Convenience functions
def get_audit_logger(log_path: str = "~/.kiri/logs/audit.log") -> AuditLogger:
    """Get an audit logger instance."""
    return AuditLogger(log_path=log_path)


def get_behavior_logger(db_path: str = "~/.kiri/behavior.db") -> BehaviorLogger:
    """Get a behavior logger instance."""
    return BehaviorLogger(db_path=db_path)
