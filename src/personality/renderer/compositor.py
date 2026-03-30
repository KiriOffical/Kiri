"""
Animation Compositor for Kiri Personality Plugin

Manages animation states, transitions, and coordinates between
the window, canvas, and asset system.

SECURITY: This module operates entirely offline with local assets only.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class Compositor:
    """
    Manages animation composition and state transitions

    Responsibilities:
    - Load animation manifests
    - Manage active animation states
    - Handle priority-based state switching
    - Coordinate window positioning with animations
    """

    def __init__(self, assets_dir: str):
        """
        Initialize the compositor

        Args:
            assets_dir: Path to the assets directory
        """
        self._assets_dir = Path(assets_dir)
        self._manifests: Dict[str, Dict[str, Any]] = {}
        self._current_state: Optional[str] = None
        self._current_priority: int = 0
        self._state_history: List[str] = []

        # Load available animation manifests
        self._load_manifests()

        logger.info(f"Compositor initialized with assets from: {assets_dir}")

    def _load_manifests(self):
        """Load all animation manifests from the assets directory"""
        animations_dir = self._assets_dir / "animations"

        if not animations_dir.exists():
            logger.warning(f"Animations directory not found: {animations_dir}")
            return

        import json

        for state_dir in animations_dir.iterdir():
            if not state_dir.is_dir():
                continue

            manifest_path = state_dir / "config.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                        manifest['path'] = str(state_dir)
                        self._manifests[state_dir.name] = manifest
                        logger.debug(f"Loaded manifest for: {state_dir.name}")
                except Exception as e:
                    logger.error(f"Failed to load manifest {manifest_path}: {e}")

    def get_state(self, state_name: str) -> Optional[Dict[str, Any]]:
        """
        Get animation configuration for a state

        Args:
            state_name: Name of the animation state

        Returns:
            Animation configuration dictionary or None if not found
        """
        return self._manifests.get(state_name)

    def get_frame_paths(self, state_name: str) -> List[str]:
        """
        Get list of frame file paths for an animation state

        Args:
            state_name: Name of the animation state

        Returns:
            List of absolute paths to frame files
        """
        manifest = self._manifests.get(state_name)
        if not manifest:
            logger.warning(f"State not found: {state_name}")
            return []

        state_dir = Path(manifest['path'])
        frames = manifest.get('frames', [])

        frame_paths = []
        for frame_file in frames:
            frame_path = state_dir / frame_file
            if frame_path.exists():
                frame_paths.append(str(frame_path))
            else:
                logger.warning(f"Frame not found: {frame_path}")

        return frame_paths

    def set_state(
        self,
        state_name: str,
        priority: int = 50,
        loop: bool = True,
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """
        Set the current animation state

        Args:
            state_name: Name of the animation state
            priority: Priority level (higher overrides lower)
            loop: Whether to loop the animation
            speed: Playback speed multiplier

        Returns:
            State information dictionary
        """
        # Check if new state has higher priority
        if priority < self._current_priority and self._current_state is not None:
            logger.debug(
                f"Ignoring state {state_name} (priority {priority}) "
                f"due to active state {self._current_state} (priority {self._current_priority})"
            )
            return {
                "accepted": False,
                "reason": "lower_priority",
                "active_state": self._current_state
            }

        # Validate state exists
        if state_name not in self._manifests:
            logger.warning(f"Unknown state: {state_name}")
            return {
                "accepted": False,
                "reason": "unknown_state",
                "available_states": list(self._manifests.keys())
            }

        # Update state
        previous_state = self._current_state
        self._current_state = state_name
        self._current_priority = priority

        if previous_state:
            self._state_history.append(previous_state)

        logger.info(f"State changed: {previous_state} -> {state_name} (priority={priority})")

        return {
            "accepted": True,
            "state": state_name,
            "priority": priority,
            "loop": loop,
            "speed": speed,
            "previous_state": previous_state
        }

    def get_current_state(self) -> Optional[str]:
        """Get the current active animation state"""
        return self._current_state

    def clear_state(self):
        """Clear the current state and reset priority"""
        previous = self._current_state
        self._current_state = None
        self._current_priority = 0

        if previous:
            self._state_history.append(previous)

        logger.info(f"State cleared (was: {previous})")

    def get_available_states(self) -> List[str]:
        """Get list of available animation states"""
        return list(self._manifests.keys())

    def get_manifest(self, state_name: str) -> Optional[Dict[str, Any]]:
        """Get the full manifest for a state"""
        return self._manifests.get(state_name)

    @property
    def state_count(self) -> int:
        """Number of loaded animation states"""
        return len(self._manifests)

    @property
    def history(self) -> List[str]:
        """Get state transition history"""
        return self._state_history.copy()
