"""
Animation Canvas for Kiri Personality Plugin

Handles rendering of SVG/PNG animation frames on the canvas.
Supports frame-by-frame animation playback with configurable speed.

SECURITY: All assets are loaded from local filesystem only.
No external resources or network calls are permitted.
"""

import tkinter as tk
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AnimationCanvas:
    """
    Canvas widget for displaying animation frames

    Features:
    - Load SVG/PNG frames from local assets
    - Frame-by-frame animation
    - Configurable playback speed
    - Minimal memory footprint
    """

    def __init__(self, canvas: tk.Canvas):
        """
        Initialize the animation canvas

        Args:
            canvas: Tkinter canvas widget to draw on
        """
        self._canvas = canvas
        self._current_frame_id: Optional[int] = None
        self._frames: List[Any] = []  # PhotoImage objects
        self._frame_index = 0
        self._is_playing = False
        self._speed = 1.0  # Playback speed multiplier
        self._loop = True
        self._frame_duration_ms = 100  # Base duration per frame

        # Asset cache to avoid reloading
        self._asset_cache: Dict[str, Any] = {}

        logger.debug("AnimationCanvas initialized")

    def load_frames(self, frame_paths: List[str]):
        """
        Load animation frames from file paths

        Args:
            frame_paths: List of paths to image files (PNG format preferred)
        """
        self._frames.clear()
        self._frame_index = 0

        for path in frame_paths:
            try:
                # Check if already cached
                if path in self._asset_cache:
                    photo = self._asset_cache[path]
                else:
                    # Load and cache the image
                    photo = tk.PhotoImage(file=path)
                    self._asset_cache[path] = photo

                self._frames.append(photo)
                logger.debug(f"Loaded frame: {path}")

            except Exception as e:
                logger.error(f"Failed to load frame {path}: {e}")
                # Create a placeholder frame
                self._create_placeholder_frame()

        logger.info(f"Loaded {len(self._frames)} frames")

    def _create_placeholder_frame(self, width: int = 100, height: int = 100):
        """Create a simple placeholder frame when asset loading fails"""
        # Create a simple colored rectangle as placeholder
        photo = tk.PhotoImage(width=width, height=height)
        self._frames.append(photo)

    def play(self, loop: bool = True, speed: float = 1.0):
        """
        Start animation playback

        Args:
            loop: Whether to loop the animation
            speed: Playback speed multiplier (1.0 = normal speed)
        """
        if not self._frames:
            logger.warning("No frames loaded, cannot play animation")
            return

        self._loop = loop
        self._speed = max(0.1, min(5.0, speed))
        self._is_playing = True
        self._frame_index = 0

        logger.debug(f"Playing animation: loop={loop}, speed={speed}")

        self._render_current_frame()
        self._schedule_next_frame()

    def stop(self, fade_out: bool = False):
        """
        Stop animation playback

        Args:
            fade_out: Whether to fade out before stopping
        """
        self._is_playing = False

        if fade_out:
            # Simple fade out could be implemented here
            pass

        if self._current_frame_id:
            self._canvas.delete(self._current_frame_id)
            self._current_frame_id = None

        logger.debug("Animation stopped")

    def clear(self):
        """Clear all frames and stop playback"""
        self.stop()
        self._frames.clear()
        self._asset_cache.clear()
        logger.debug("Animation canvas cleared")

    def _render_current_frame(self):
        """Render the current frame on the canvas"""
        if not self._frames or self._frame_index >= len(self._frames):
            return

        # Clear previous frame
        if self._current_frame_id:
            self._canvas.delete(self._current_frame_id)

        # Get current frame
        photo = self._frames[self._frame_index]

        # Center the image on canvas
        canvas_width = self._canvas.winfo_reqwidth()
        canvas_height = self._canvas.winfo_reqheight()

        x = canvas_width // 2
        y = canvas_height // 2

        # Render the image centered
        self._current_frame_id = self._canvas.create_image(
            x, y,
            anchor=tk.CENTER,
            image=photo
        )

    def _schedule_next_frame(self):
        """Schedule the next frame to be rendered"""
        if not self._is_playing or not self._frames:
            return

        # Calculate frame duration based on speed
        adjusted_duration = int(self._frame_duration_ms / self._speed)

        # Schedule next frame
        self._canvas.after(adjusted_duration, self._advance_frame)

    def _advance_frame(self):
        """Advance to the next frame"""
        if not self._is_playing:
            return

        self._frame_index += 1

        # Check if we've reached the end
        if self._frame_index >= len(self._frames):
            if self._loop:
                self._frame_index = 0
            else:
                self._is_playing = False
                return

        self._render_current_frame()
        self._schedule_next_frame()

    def set_frame_duration(self, duration_ms: int):
        """
        Set the base duration for each frame

        Args:
            duration_ms: Duration in milliseconds
        """
        self._frame_duration_ms = max(16, duration_ms)  # Minimum ~60fps
        logger.debug(f"Frame duration set to {duration_ms}ms")

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def current_frame_index(self) -> int:
        return self._frame_index

    @property
    def total_frames(self) -> int:
        return len(self._frames)
