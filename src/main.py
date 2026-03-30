"""
Kiri v5.0.0 - Main Entry Point

Your Personal AI Assistant. Local. Open. Yours.

This is the main application entry point that orchestrates:
- Configuration loading
- Secret Scanner (Security Gate)
- File Watcher
- Audit Logging
- Future: Email Bot, Version Bot, Manager Agent
"""

import sys
import signal
import time
from pathlib import Path
from typing import Optional

# Add src to path for imports when running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import ConfigLoader, KiriConfig, KeychainManager
from utils.logger import AuditLogger, BehaviorLogger, get_audit_logger
from security.secret_scanner import SecretScanner, scan_file_for_secrets, ScanStatus
from servants.file_watcher import FileWatcher, FileEvent, FileEventType, create_watcher


class KiriAssistant:
    """
    Main Kiri Assistant application.
    
    Orchestrates all components:
    1. Loads configuration
    2. Initializes security components
    3. Starts file watcher
    4. Processes events through security gate
    5. Logs all operations
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Kiri Assistant.
        
        Args:
            config_path: Optional path to configuration file
        """
        print("🌸 Initializing Kiri v5.0.0...")
        
        # Load configuration
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load()
        
        # Validate configuration
        errors = self.config_loader.validate(self.config)
        if errors:
            print("⚠️  Configuration warnings:")
            for error in errors:
                print(f"   - {error}")
        
        # Initialize loggers
        self.audit_logger = get_audit_logger(
            log_path=self.config.logging.audit_log_path
        )
        self.behavior_logger = None  # Lazy initialization
        
        # Initialize security scanner
        self.secret_scanner = SecretScanner()
        
        # Initialize file watcher
        self.file_watcher = self._setup_file_watcher()
        
        # Application state
        self._running = False
        
        # Log startup
        self.audit_logger.info("Kiri Assistant starting", version=self.config.app.version)
        self.audit_logger.log_event(
            event_type="system",
            action="startup",
            status="success",
            details={"version": self.config.app.version}
        )
    
    def _setup_file_watcher(self) -> FileWatcher:
        """Configure and return file watcher."""
        watcher = FileWatcher(
            debounce_seconds=1.0,
            on_event=self._handle_file_event
        )
        
        # Add monitored folders from config
        for folder_path in self.config.file_organization.monitored_folders:
            watcher.add_folder(
                path=folder_path,
                recursive=True,
                ignore_patterns=[".*", "*.tmp", "*.swp", "*.part"]
            )
        
        return watcher
    
    def _get_behavior_logger(self) -> BehaviorLogger:
        """Get or create behavior logger."""
        if self.behavior_logger is None:
            from utils.logger import get_behavior_logger
            self.behavior_logger = get_behavior_logger(
                db_path=self.config.logging.behavior_db_path
            )
        return self.behavior_logger
    
    def _handle_file_event(self, event: FileEvent):
        """
        Process a file event through the security pipeline.
        
        Pipeline:
        1. Event received
        2. Security Gate (Secret Scanner)
        3. Classification (File Bot)
        4. Action (Move/Organize)
        5. Logging
        """
        if not self._running:
            return
        
        file_path = event.file_path
        event_type = event.event_type.value
        
        self.audit_logger.debug(f"File event detected", 
                               event_type=event_type, 
                               file_path=file_path)
        
        # Handle different event types
        if event_type == FileEventType.DELETED.value:
            self.audit_logger.log_event(
                event_type="file_operation",
                action="delete",
                status="detected",
                details={"file_path": file_path}
            )
            return
        
        # Check if file exists
        if not Path(file_path).exists():
            self.audit_logger.warning(f"File no longer exists", file_path=file_path)
            return
        
        # SECURITY GATE: Scan for secrets
        if self.config.security.secret_scanner_enabled:
            self.audit_logger.debug(f"Running secret scan", file_path=file_path)
            
            scan_result = scan_file_for_secrets(
                file_path, 
                max_size_kb=self.config.security.scan_file_size_limit_kb
            )
            
            if scan_result.status == ScanStatus.UNSAFE:
                # BLOCK: Secrets detected
                self.audit_logger.log_event(
                    event_type="security",
                    action="scan",
                    status="blocked",
                    details={
                        "file_path": file_path,
                        "secrets_found": len(scan_result.matches),
                        "highest_severity": scan_result.matches[0].severity if scan_result.matches else "unknown"
                    }
                )
                
                print(f"🚫 SECURITY ALERT: Secrets detected in {file_path}")
                for match in scan_result.matches[:3]:  # Show top 3
                    print(f"   - {match.pattern_name} (severity: {match.severity})")
                
                # TODO: Notify user, block further processing
                return
            
            elif scan_result.status == ScanStatus.SAFE:
                self.audit_logger.log_event(
                    event_type="security",
                    action="scan",
                    status="passed",
                    details={"file_path": file_path}
                )
        
        # FILE ORGANIZATION: Process safe files
        if self.config.file_organization.enabled:
            self._process_file_organization(event)
    
    def _process_file_organization(self, event: FileEvent):
        """
        Organize file based on rules and AI classification.
        
        TODO: Implement full file organization pipeline:
        1. Extension-based classification
        2. Content signature analysis
        3. AI-powered ambiguity resolution
        4. Git backup (Phase 2.1)
        5. Move file
        """
        file_path = Path(event.file_path)
        
        self.audit_logger.debug(f"Processing file organization", 
                               file_path=str(file_path),
                               extension=file_path.suffix)
        
        # Placeholder: Just log for now
        # Full implementation in Phase 2
        print(f"📁 File detected: {file_path.name} ({file_path.suffix or 'no extension'})")
        
        # Log behavior for learning
        behavior_logger = self._get_behavior_logger()
        behavior_logger.log_event(
            event_type="file",
            action="detected",
            result="pending_classification",
            metadata={
                "extension": file_path.suffix,
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }
        )
    
    def start(self):
        """Start Kiri Assistant."""
        if self._running:
            self.audit_logger.warning("Attempted to start while already running")
            return
        
        print("\n✅ Kiri Assistant initialized successfully")
        print(f"   Version: {self.config.app.version}")
        print(f"   Debug mode: {self.config.app.debug}")
        print(f"   Monitored folders: {len(self.config.file_organization.monitored_folders)}")
        print(f"   Secret Scanner: {'Enabled' if self.config.security.secret_scanner_enabled else 'Disabled'}")
        print(f"   File Organization: {'Enabled' if self.config.file_organization.enabled else 'Disabled'}")
        print(f"   Email Monitoring: {'Enabled' if self.config.email.enabled else 'Disabled'}")
        
        print("\n👀 Starting file watcher...")
        self._running = True
        self.file_watcher.start()
        
        print("\n✨ Kiri is now watching your folders.")
        print("   Press Ctrl+C to stop.\n")
        
        self.audit_logger.log_event(
            event_type="system",
            action="start",
            status="success"
        )
    
    def stop(self):
        """Stop Kiri Assistant gracefully."""
        if not self._running:
            return
        
        print("\n🛑 Stopping Kiri Assistant...")
        
        self._running = False
        self.file_watcher.stop()
        
        # Close loggers
        if self.behavior_logger:
            self.behavior_logger.close()
        
        self.audit_logger.log_event(
            event_type="system",
            action="shutdown",
            status="success"
        )
        self.audit_logger.info("Kiri Assistant stopped")
        
        print("✅ Kiri stopped gracefully")
    
    def run(self):
        """Run Kiri Assistant main loop."""
        self.start()
        
        # Keep running until interrupted
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


def setup_signal_handlers(app: KiriAssistant):
    """Setup graceful shutdown handlers."""
    def signal_handler(signum, frame):
        print("\n⚠️  Received interrupt signal")
        app.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Kiri v5.0.0 - Your Personal AI Assistant. Local. Open. Yours."
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file",
        default=None
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version and exit"
    )
    parser.add_argument(
        "--test-scan",
        type=str,
        help="Test secret scanner on a file and exit"
    )
    
    args = parser.parse_args()
    
    # Show version
    if args.version:
        print("Kiri v5.0.0")
        print("Local. Open. Yours.")
        sys.exit(0)
    
    # Test scan mode
    if args.test_scan:
        print(f"Scanning {args.test_scan} for secrets...")
        result = scan_file_for_secrets(args.test_scan)
        
        if result.status == ScanStatus.UNSAFE:
            print(f"\n🚫 UNAFE: Found {len(result.matches)} potential secret(s)")
            for match in result.matches:
                print(f"   - {match.pattern_name}: {match.match_value} (line {match.line_number})")
            sys.exit(1)
        else:
            print(f"\n✅ SAFE: No secrets detected")
            sys.exit(0)
    
    # Create and run assistant
    app = KiriAssistant(config_path=args.config)
    setup_signal_handlers(app)
    app.run()


if __name__ == "__main__":
    main()
