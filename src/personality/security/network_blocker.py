"""
Network Security Blocker for Kiri Personality Plugin

CRITICAL SECURITY MODULE: This module ensures that NO network connections
can be made by the plugin. All outbound traffic is blocked at the code level.

This satisfies the "Local-First" constraint: Zero network calls permitted.
"""

import socket
import logging
from typing import Optional
from functools import wraps

logger = logging.getLogger(__name__)


class NetworkSecurityError(Exception):
    """Raised when a network operation is attempted"""
    pass


class NetworkBlocker:
    """
    Blocks all network operations at the code level

    SECURITY: This class monkey-patches socket creation to prevent
    any network connections from being established.

    WARNING: Do not disable this in production!
    """

    _instance: Optional['NetworkBlocker'] = None
    _blocked = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._original_socket = None
        self._original_connect = None

    def enable_blocking(self):
        """
        Enable network blocking

        SECURITY: This should be called immediately on plugin startup
        to ensure no network calls can be made.
        """
        if NetworkBlocker._blocked:
            logger.debug("Network blocking already enabled")
            return

        logger.warning("ENABLING NETWORK BLOCK - All network calls will be blocked")

        # Store original socket class
        self._original_socket = socket.socket

        # Replace socket constructor with blocked version
        socket.socket = self._blocked_socket_constructor

        NetworkBlocker._blocked = True

        logger.info("Network blocking enabled successfully")

    def disable_blocking(self):
        """
        Disable network blocking

        WARNING: Only use for testing! Never call in production.
        """
        if not NetworkBlocker._blocked:
            return

        logger.warning("DISABLING NETWORK BLOCK - This should never happen in production!")

        # Restore original socket
        if self._original_socket:
            socket.socket = self._original_socket

        NetworkBlocker._blocked = False

    def _blocked_socket_constructor(self, *args, **kwargs):
        """
        Blocked socket constructor

        Raises NetworkSecurityError when any code attempts to create a socket
        """
        raise NetworkSecurityError(
            "NETWORK ACCESS BLOCKED: Kiri Personality Plugin is local-first. "
            "Network connections are prohibited for security and privacy."
        )

    @staticmethod
    def is_blocked() -> bool:
        """Check if network blocking is active"""
        return NetworkBlocker._blocked

    def get_status(self) -> dict:
        """Get network security status"""
        return {
            "blocked": NetworkBlocker._blocked,
            "socket_patched": self._original_socket is not None,
            "security_level": "maximum" if NetworkBlocker._blocked else "none"
        }


def block_network_calls(func):
    """
    Decorator to explicitly mark functions that should never make network calls

    This is a documentation/audit helper that logs warnings if network
    blocking is not enabled when the function runs.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not NetworkBlocker.is_blocked():
            logger.critical(
                f"SECURITY WARNING: Function {func.__name__} called without "
                "network blocking enabled!"
            )
        return func(*args, **kwargs)
    return wrapper


# Auto-enable blocking when module is imported
# SECURITY: This ensures blocking is active as early as possible
_blocker = NetworkBlocker()
_blocker.enable_blocking()

logger.info("Network blocker module loaded - all network calls will be blocked")
