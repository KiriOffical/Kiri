"""
File Watcher Module - Phase 2.2

Monitors directories for file system events:
- File creation
- File modification
- File movement
- File deletion

Features:
- Debouncing to prevent duplicate events
- Configurable monitored folders
- Integration with Secret Scanner
"""

import time
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib


class FileEventType(Enum):
    """Types of file system events."""
    CREATED = "created"
    MODIFIED = "modified"
    MOVED = "moved"
    DELETED = "deleted"


@dataclass
class FileEvent:
    """Represents a file system event."""
    event_type: FileEventType
    file_path: str
    timestamp: float
    previous_path: Optional[str] = None  # For move events
    file_hash: Optional[str] = None  # SHA256 hash for deduplication
    
    def __post_init__(self):
        if self.file_hash is None and Path(self.file_path).exists():
            self.file_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> Optional[str]:
        """Calculate SHA256 hash of file content."""
        try:
            hasher = hashlib.sha256()
            with open(self.file_path, 'rb') as f:
                # Read first 1MB for hashing
                chunk = f.read(1024 * 1024)
                hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None


@dataclass
class WatchedFolder:
    """Configuration for a watched folder."""
    path: str
    recursive: bool = True
    patterns: List[str] = field(default_factory=lambda: ["*"])  # Glob patterns
    ignore_patterns: List[str] = field(default_factory=lambda: [".*", "*.tmp", "*.swp"])


class FileWatcher:
    """
    Monitors folders for file system changes.
    
    Design Principles:
    - Efficient: Uses system notifications when available
    - Debounced: Prevents duplicate events for same file
    - Configurable: Supports multiple folders with different settings
    """
    
    def __init__(
        self,
        folders: Optional[List[WatchedFolder]] = None,
        debounce_seconds: float = 1.0,
        on_event: Optional[Callable[[FileEvent], None]] = None
    ):
        """
        Initialize file watcher.
        
        Args:
            folders: List of folders to watch
            debounce_seconds: Time to wait before firing event (prevents duplicates)
            on_event: Callback function for file events
        """
        self.folders = folders or []
        self.debounce_seconds = debounce_seconds
        self.on_event = on_event
        
        # Debounce tracking
        self._pending_events: Dict[str, FileEvent] = {}
        self._event_timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()
        
        # Tracking seen files to detect moves
        self._known_hashes: Dict[str, str] = {}  # hash -> path
        
        # Watcher state
        self._running = False
        self._watch_threads: List[threading.Thread] = []
        
        # Use watchdog if available, fallback to polling
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            self._use_watchdog = True
            self._Observer = Observer
            self._FileSystemEventHandler = FileSystemEventHandler
        except ImportError:
            self._use_watchdog = False
    
    def add_folder(
        self,
        path: str,
        recursive: bool = True,
        patterns: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None
    ):
        """Add a folder to watch."""
        folder = WatchedFolder(
            path=path,
            recursive=recursive,
            patterns=patterns or ["*"],
            ignore_patterns=ignore_patterns or [".*", "*.tmp", "*.swp"]
        )
        self.folders.append(folder)
    
    def remove_folder(self, path: str) -> bool:
        """Remove a folder from watching."""
        original_count = len(self.folders)
        self.folders = [f for f in self.folders if f.path != path]
        return len(self.folders) < original_count
    
    def start(self):
        """Start watching all configured folders."""
        if self._running:
            return
        
        self._running = True
        
        if self._use_watchdog:
            self._start_watchdog()
        else:
            self._start_polling()
    
    def stop(self):
        """Stop watching folders."""
        self._running = False
        
        # Cancel pending timers
        with self._lock:
            for timer in self._event_timers.values():
                timer.cancel()
            self._event_timers.clear()
        
        # Wait for threads to finish
        for thread in self._watch_threads:
            thread.join(timeout=2.0)
        self._watch_threads.clear()
    
    def _start_watchdog(self):
        """Start watchdog-based file monitoring."""
        observer = self._Observer()
        handler = WatchdogEventHandler(self)
        
        for folder in self.folders:
            folder_path = Path(folder.path).expanduser()
            if not folder_path.exists():
                print(f"Warning: Folder does not exist: {folder_path}")
                continue
            
            observer.schedule(handler, str(folder_path), recursive=folder.recursive)
            print(f"Watching folder: {folder_path} (recursive={folder.recursive})")
        
        observer.start()
        self._watch_threads.append(observer)
    
    def _start_polling(self):
        """Start polling-based file monitoring (fallback)."""
        def poll_thread():
            last_state = {}
            
            while self._running:
                current_state = {}
                
                for folder in self.folders:
                    folder_path = Path(folder.path).expanduser()
                    if not folder_path.exists():
                        continue
                    
                    # Scan files
                    if folder.recursive:
                        files = list(folder_path.rglob("*"))
                    else:
                        files = list(folder_path.glob("*"))
                    
                    for file_path in files:
                        if file_path.is_file():
                            # Check ignore patterns
                            if any(file_path.match(pat) for pat in folder.ignore_patterns):
                                continue
                            
                            # Check include patterns
                            if not any(file_path.match(pat) for pat in folder.patterns):
                                continue
                            
                            try:
                                mtime = file_path.stat().st_mtime
                                current_state[str(file_path)] = mtime
                                
                                # Detect new files
                                if str(file_path) not in last_state:
                                    self._handle_event(FileEvent(
                                        event_type=FileEventType.CREATED,
                                        file_path=str(file_path),
                                        timestamp=time.time()
                                    ))
                                elif last_state[str(file_path)] != mtime:
                                    self._handle_event(FileEvent(
                                        event_type=FileEventType.MODIFIED,
                                        file_path=str(file_path),
                                        timestamp=time.time()
                                    ))
                            except Exception:
                                pass
                
                # Detect deletions
                for path in last_state:
                    if path not in current_state:
                        self._handle_event(FileEvent(
                            event_type=FileEventType.DELETED,
                            file_path=path,
                            timestamp=time.time()
                        ))
                
                last_state = current_state
                time.sleep(1.0)  # Poll every second
        
        thread = threading.Thread(target=poll_thread, daemon=True)
        thread.start()
        self._watch_threads.append(thread)
    
    def _handle_event(self, event: FileEvent):
        """Handle a file event with debouncing."""
        with self._lock:
            file_key = event.file_path
            
            # Cancel existing timer for this file
            if file_key in self._event_timers:
                self._event_timers[file_key].cancel()
            
            # Store/update pending event
            self._pending_events[file_key] = event
            
            # Set new timer
            timer = threading.Timer(
                self.debounce_seconds,
                self._fire_event,
                args=[file_key]
            )
            self._event_timers[file_key] = timer
            timer.start()
    
    def _fire_event(self, file_key: str):
        """Fire a debounced event."""
        with self._lock:
            if file_key not in self._pending_events:
                return
            
            event = self._pending_events.pop(file_key)
            self._event_timers.pop(file_key, None)
        
        # Call the event handler
        if self.on_event:
            try:
                self.on_event(event)
            except Exception as e:
                print(f"Error in event handler: {e}")


class WatchdogEventHandler:
    """Handler for watchdog file system events."""
    
    def __init__(self, watcher: FileWatcher):
        self.watcher = watcher
        self._handler = watcher._FileSystemEventHandler()
        
        # Override event methods
        self._handler.on_created = self.on_created
        self._handler.on_modified = self.on_modified
        self._handler.on_moved = self.on_moved
        self._handler.on_deleted = self.on_deleted
    
    def on_created(self, event):
        """Handle file creation."""
        if event.is_directory:
            return
        
        self.watcher._handle_event(FileEvent(
            event_type=FileEventType.CREATED,
            file_path=event.src_path,
            timestamp=time.time()
        ))
    
    def on_modified(self, event):
        """Handle file modification."""
        if event.is_directory:
            return
        
        self.watcher._handle_event(FileEvent(
            event_type=FileEventType.MODIFIED,
            file_path=event.src_path,
            timestamp=time.time()
        ))
    
    def on_moved(self, event):
        """Handle file movement."""
        if event.is_directory:
            return
        
        self.watcher._handle_event(FileEvent(
            event_type=FileEventType.MOVED,
            file_path=event.dest_path,
            timestamp=time.time(),
            previous_path=event.src_path
        ))
    
    def on_deleted(self, event):
        """Handle file deletion."""
        if event.is_directory:
            return
        
        self.watcher._handle_event(FileEvent(
            event_type=FileEventType.DELETED,
            file_path=event.src_path,
            timestamp=time.time()
        ))


# Convenience function
def create_watcher(
    folders: List[str],
    callback: Callable[[FileEvent], None],
    recursive: bool = True,
    debounce_seconds: float = 1.0
) -> FileWatcher:
    """Create and configure a file watcher."""
    watched_folders = [
        WatchedFolder(path=f, recursive=recursive)
        for f in folders
    ]
    
    watcher = FileWatcher(
        folders=watched_folders,
        debounce_seconds=debounce_seconds,
        on_event=callback
    )
    
    return watcher
