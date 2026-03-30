"""
Configuration System - Phase 1.2

Handles loading, validation, and management of Kiri configuration.
Uses YAML for config files and OS Keychain for secrets.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dataclasses import dataclass, field


@dataclass
class AppConfig:
    """Application-level configuration."""
    name: str = "Kiri"
    version: str = "5.0.0"
    debug: bool = False
    single_instance: bool = True


@dataclass
class FileOrganizationConfig:
    """File organization settings."""
    enabled: bool = True
    monitored_folders: list = field(default_factory=lambda: ["~/Downloads"])
    base_output_folder: str = "~/Documents/Organized"
    categories: Dict[str, Any] = field(default_factory=dict)
    confidence_threshold: float = 0.7
    require_confirmation: bool = True


@dataclass
class EmailConfig:
    """Email/IMAP settings."""
    enabled: bool = False
    read_only: bool = True  # NEVER modify this
    check_interval_minutes: int = 30
    max_age_days: int = 7
    folders_to_check: list = field(default_factory=lambda: ["INBOX"])


@dataclass
class AIConfig:
    """Local AI settings."""
    enabled: bool = True
    provider: str = "ollama"
    model: str = "qwen2.5:3b"
    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 30
    max_tokens: int = 512


@dataclass
class SecurityConfig:
    """Security settings."""
    secret_scanner_enabled: bool = True
    scan_file_size_limit_kb: int = 2
    patterns: list = field(default_factory=list)


@dataclass
class BackupConfig:
    """Git backup settings."""
    enabled: bool = True
    repo_path: str = "~/kiri_backups"
    auto_commit: bool = True
    pre_action_branch: bool = True
    retention_days: int = 30
    gpg_sign: bool = False


@dataclass
class LoggingConfig:
    """Logging settings."""
    behavior_db_path: str = "~/.kiri/behavior.db"
    audit_log_path: str = "~/.kiri/logs/audit.log"
    retention_days: int = 90
    encrypt_behavior_db: bool = True
    log_level: str = "INFO"


@dataclass
class NotificationConfig:
    """Notification settings."""
    enabled: bool = True
    quiet_hours: Dict[str, Any] = field(default_factory=lambda: {"enabled": False})
    critical_alerts_always: bool = True


@dataclass
class BriefingConfig:
    """Daily briefing settings."""
    enabled: bool = True
    output_path: str = "~/kiri_briefing.html"
    schedule: str = "08:00"
    top_emails: int = 5
    include_files_summary: bool = True
    include_tasks: bool = True
    include_security_alerts: bool = True


@dataclass
class KiriConfig:
    """Main configuration container."""
    app: AppConfig = field(default_factory=AppConfig)
    file_organization: FileOrganizationConfig = field(default_factory=FileOrganizationConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    briefing: BriefingConfig = field(default_factory=BriefingConfig)


class ConfigLoader:
    """
    Loads and validates Kiri configuration.
    
    Design Principles:
    - Safe defaults: Missing config uses safe defaults
    - Validation: Checks critical settings
    - No secrets: Credentials must come from OS Keychain
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config loader.
        
        Args:
            config_path: Path to YAML config file. If None, uses default locations.
        """
        self.config_path = config_path or self._find_config_file()
        self.raw_config: Dict[str, Any] = {}
    
    def _find_config_file(self) -> str:
        """Find config file in standard locations."""
        possible_paths = [
            Path("config/config.yaml"),
            Path("config/default.yaml"),
            Path.home() / ".kiri" / "config.yaml",
            Path("/etc/kiri/config.yaml")
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        # Return default even if it doesn't exist
        return "config/config.yaml"
    
    def load(self) -> KiriConfig:
        """
        Load configuration from file.
        
        Returns:
            KiriConfig object with loaded settings
            
        Raises:
            FileNotFoundError: If config file doesn't exist and no default available
            ValidationError: If config has invalid values
        """
        if not Path(self.config_path).exists():
            # Return default config if file doesn't exist
            return KiriConfig()
        
        with open(self.config_path, 'r') as f:
            self.raw_config = yaml.safe_load(f) or {}
        
        return self._parse_config()
    
    def _parse_config(self) -> KiriConfig:
        """Parse raw config dict into KiriConfig object."""
        config = KiriConfig()
        
        # Parse app settings
        if 'app' in self.raw_config:
            app_data = self.raw_config['app']
            config.app = AppConfig(
                name=app_data.get('name', 'Kiri'),
                version=app_data.get('version', '5.0.0'),
                debug=app_data.get('debug', False),
                single_instance=app_data.get('single_instance', True)
            )
        
        # Parse file organization settings
        if 'file_organization' in self.raw_config:
            fo_data = self.raw_config['file_organization']
            config.file_organization = FileOrganizationConfig(
                enabled=fo_data.get('enabled', True),
                monitored_folders=fo_data.get('monitored_folders', ["~/Downloads"]),
                base_output_folder=fo_data.get('base_output_folder', "~/Documents/Organized"),
                categories=fo_data.get('categories', {}),
                confidence_threshold=fo_data.get('confidence_threshold', 0.7),
                require_confirmation=fo_data.get('require_confirmation', True)
            )
        
        # Parse email settings
        if 'email' in self.raw_config:
            email_data = self.raw_config['email']
            config.email = EmailConfig(
                enabled=email_data.get('enabled', False),
                read_only=email_data.get('read_only', True),  # Enforce read-only
                check_interval_minutes=email_data.get('check_interval_minutes', 30),
                max_age_days=email_data.get('max_age_days', 7),
                folders_to_check=email_data.get('folders_to_check', ["INBOX"])
            )
        
        # Parse AI settings
        if 'ai' in self.raw_config:
            ai_data = self.raw_config['ai']
            config.ai = AIConfig(
                enabled=ai_data.get('enabled', True),
                provider=ai_data.get('provider', 'ollama'),
                model=ai_data.get('model', 'qwen2.5:3b'),
                base_url=ai_data.get('base_url', 'http://localhost:11434'),
                timeout_seconds=ai_data.get('timeout_seconds', 30),
                max_tokens=ai_data.get('max_tokens', 512)
            )
        
        # Parse security settings
        if 'security' in self.raw_config:
            sec_data = self.raw_config['security']
            config.security = SecurityConfig(
                secret_scanner_enabled=sec_data.get('secret_scanner_enabled', True),
                scan_file_size_limit_kb=sec_data.get('scan_file_size_limit_kb', 2),
                patterns=sec_data.get('patterns', [])
            )
        
        # Parse backup settings
        if 'backup' in self.raw_config:
            backup_data = self.raw_config['backup']
            config.backup = BackupConfig(
                enabled=backup_data.get('enabled', True),
                repo_path=backup_data.get('repo_path', '~/kiri_backups'),
                auto_commit=backup_data.get('auto_commit', True),
                pre_action_branch=backup_data.get('pre_action_branch', True),
                retention_days=backup_data.get('retention_days', 30),
                gpg_sign=backup_data.get('gpg_sign', False)
            )
        
        # Parse logging settings
        if 'logging' in self.raw_config:
            log_data = self.raw_config['logging']
            config.logging = LoggingConfig(
                behavior_db_path=log_data.get('behavior_db_path', '~/.kiri/behavior.db'),
                audit_log_path=log_data.get('audit_log_path', '~/.kiri/logs/audit.log'),
                retention_days=log_data.get('retention_days', 90),
                encrypt_behavior_db=log_data.get('encrypt_behavior_db', True),
                log_level=log_data.get('log_level', 'INFO')
            )
        
        # Parse notification settings
        if 'notifications' in self.raw_config:
            notif_data = self.raw_config['notifications']
            config.notifications = NotificationConfig(
                enabled=notif_data.get('enabled', True),
                quiet_hours=notif_data.get('quiet_hours', {"enabled": False}),
                critical_alerts_always=notif_data.get('critical_alerts_always', True)
            )
        
        # Parse briefing settings
        if 'briefing' in self.raw_config:
            brief_data = self.raw_config['briefing']
            config.briefing = BriefingConfig(
                enabled=brief_data.get('enabled', True),
                output_path=brief_data.get('output_path', '~/kiri_briefing.html'),
                schedule=brief_data.get('schedule', '08:00'),
                top_emails=brief_data.get('top_emails', 5),
                include_files_summary=brief_data.get('include_files_summary', True),
                include_tasks=brief_data.get('include_tasks', True),
                include_security_alerts=brief_data.get('include_security_alerts', True)
            )
        
        return config
    
    def validate(self, config: KiriConfig) -> list:
        """
        Validate configuration for safety and correctness.
        
        Args:
            config: KiriConfig object to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Critical: Email must be read-only
        if config.email.enabled and not config.email.read_only:
            errors.append("CRITICAL: Email configuration must be read-only")
        
        # Validate AI endpoint
        if config.ai.enabled:
            if not config.ai.base_url.startswith(('http://', 'https://')):
                errors.append("AI base_url must be a valid HTTP(S) URL")
        
        # Validate file paths are expandable
        try:
            Path(config.backup.repo_path).expanduser()
        except Exception as e:
            errors.append(f"Invalid backup repo path: {e}")
        
        # Validate confidence threshold
        if not 0.0 <= config.file_organization.confidence_threshold <= 1.0:
            errors.append("Confidence threshold must be between 0.0 and 1.0")
        
        return errors
    
    def save(self, config: KiriConfig, path: Optional[str] = None):
        """
        Save configuration to file.
        
        Args:
            config: KiriConfig object to save
            path: Output path (uses config_path if None)
            
        Note: Does NOT save secrets - those must go to OS Keychain
        """
        output_path = path or self.config_path
        
        # Convert config to dict
        config_dict = {
            'app': {
                'name': config.app.name,
                'version': config.app.version,
                'debug': config.app.debug,
                'single_instance': config.app.single_instance
            },
            'file_organization': {
                'enabled': config.file_organization.enabled,
                'monitored_folders': config.file_organization.monitored_folders,
                'base_output_folder': config.file_organization.base_output_folder,
                'categories': config.file_organization.categories,
                'confidence_threshold': config.file_organization.confidence_threshold,
                'require_confirmation': config.file_organization.require_confirmation
            },
            'email': {
                'enabled': config.email.enabled,
                'read_only': config.email.read_only,
                'check_interval_minutes': config.email.check_interval_minutes,
                'max_age_days': config.email.max_age_days,
                'folders_to_check': config.email.folders_to_check
            },
            'ai': {
                'enabled': config.ai.enabled,
                'provider': config.ai.provider,
                'model': config.ai.model,
                'base_url': config.ai.base_url,
                'timeout_seconds': config.ai.timeout_seconds,
                'max_tokens': config.ai.max_tokens
            },
            'security': {
                'secret_scanner_enabled': config.security.secret_scanner_enabled,
                'scan_file_size_limit_kb': config.security.scan_file_size_limit_kb,
                'patterns': config.security.patterns
            },
            'backup': {
                'enabled': config.backup.enabled,
                'repo_path': config.backup.repo_path,
                'auto_commit': config.backup.auto_commit,
                'pre_action_branch': config.backup.pre_action_branch,
                'retention_days': config.backup.retention_days,
                'gpg_sign': config.backup.gpg_sign
            },
            'logging': {
                'behavior_db_path': config.logging.behavior_db_path,
                'audit_log_path': config.logging.audit_log_path,
                'retention_days': config.logging.retention_days,
                'encrypt_behavior_db': config.logging.encrypt_behavior_db,
                'log_level': config.logging.log_level
            },
            'notifications': {
                'enabled': config.notifications.enabled,
                'quiet_hours': config.notifications.quiet_hours,
                'critical_alerts_always': config.notifications.critical_alerts_always
            },
            'briefing': {
                'enabled': config.briefing.enabled,
                'output_path': config.briefing.output_path,
                'schedule': config.briefing.schedule,
                'top_emails': config.briefing.top_emails,
                'include_files_summary': config.briefing.include_files_summary,
                'include_tasks': config.briefing.include_tasks,
                'include_security_alerts': config.briefing.include_security_alerts
            }
        }
        
        # Ensure directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write config
        with open(output_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)


# Keychain integration for secrets
class KeychainManager:
    """
    Manages secrets in OS Keychain.
    
    Design Principles:
    - Never store secrets in config files
    - Use OS-native keychain (libsecret, Keychain, Windows Credential Manager)
    - Service name prefixed to avoid conflicts
    """
    
    SERVICE_NAME = "kiri"
    
    def __init__(self):
        try:
            import keyring
            self.keyring = keyring
            self.available = True
        except ImportError:
            self.keyring = None
            self.available = False
    
    def set_password(self, service: str, username: str, password: str) -> bool:
        """
        Store password in keychain.
        
        Args:
            service: Service identifier (e.g., 'email', 'api')
            username: Username/account identifier
            password: Password/token to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            return False
        
        try:
            full_service = f"{self.SERVICE_NAME}_{service}"
            self.keyring.set_password(full_service, username, password)
            return True
        except Exception:
            return False
    
    def get_password(self, service: str, username: str) -> Optional[str]:
        """
        Retrieve password from keychain.
        
        Args:
            service: Service identifier
            username: Username/account identifier
            
        Returns:
            Password if found, None otherwise
        """
        if not self.available:
            return None
        
        try:
            full_service = f"{self.SERVICE_NAME}_{service}"
            return self.keyring.get_password(full_service, username)
        except Exception:
            return None
    
    def delete_password(self, service: str, username: str) -> bool:
        """
        Delete password from keychain.
        
        Args:
            service: Service identifier
            username: Username/account identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            return False
        
        try:
            full_service = f"{self.SERVICE_NAME}_{service}"
            self.keyring.delete_password(full_service, username)
            return True
        except Exception:
            return False


# Convenience functions
def load_config(config_path: Optional[str] = None) -> KiriConfig:
    """Load configuration from file."""
    loader = ConfigLoader(config_path)
    config = loader.load()
    
    # Validate
    errors = loader.validate(config)
    if errors:
        for error in errors:
            print(f"Config Warning: {error}")
    
    return config


def save_config(config: KiriConfig, path: Optional[str] = None):
    """Save configuration to file."""
    loader = ConfigLoader()
    loader.save(config, path)
