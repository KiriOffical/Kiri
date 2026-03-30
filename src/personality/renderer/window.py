"""
Avatar Window Management for Kiri Personality Plugin

Creates and manages a borderless, always-on-top window for the avatar.
Uses tkinter (native Python UI) for minimal resource usage.

SECURITY: This module creates no network connections. Window rendering
is entirely local with no external dependencies.
"""

import tkinter as tk
from typing import Optional, Tuple, Callable
import logging

logger = logging.getLogger(__name__)


class AvatarWindow:
    """
    Borderless window for displaying the Kiri avatar

    Features:
    - Always on top
    - Transparent background
    - Movable to screen coordinates
    - Opacity control
    - Minimal CPU/RAM usage
    """

    def __init__(
        self,
        width: int = 200,
        height: int = 200,
        opacity: float = 1.0,
        position: Optional[Tuple[int, int]] = None
    ):
        """
        Initialize the avatar window

        Args:
            width: Window width in pixels
            height: Window height in pixels
            opacity: Initial opacity (0.0 to 1.0)
            position: Initial (x, y) screen coordinates, or None for center
        """
        self._width = width
        self._height = height
        self._opacity = max(0.0, min(1.0, opacity))
        self._position = position

        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._is_closing = False

        # SECURITY: No network initialization here
        # All rendering is purely local

        logger.info(f"Initialized AvatarWindow: {width}x{height}, opacity={opacity}")

    def create(self):
        """Create the window and canvas"""
        if self._root is not None:
            logger.warning("Window already created")
            return

        # Create root window
        self._root = tk.Tk()
        self._root.title("Kiri")

        # Remove window decorations (borderless)
        self._root.overrideredirect(True)

        # Set always on top
        self._root.attributes('-topmost', True)

        # Set initial opacity
        self._set_opacity_internal(self._opacity)

        # Set window size and position
        self._center_window() if self._position is None else self._move_to(*self._position)

        # Create transparent canvas
        self._canvas = tk.Canvas(
            self._root,
            width=self._width,
            height=self._height,
            bg='white',
            highlightthickness=0
        )
        self._canvas.pack()

        # Make white background transparent
        self._canvas.configure(bg='white')
        self._root.wm_attributes('-transparentcolor', 'white')

        # Handle window close
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        logger.info("Avatar window created successfully")

    def _center_window(self):
        """Center the window on the screen"""
        if not self._root:
            return

        screen_width = self._root.winfo_screenwidth()
        screen_height = self._root.winfo_screenheight()

        x = (screen_width - self._width) // 2
        y = (screen_height - self._height) // 2

        self._root.geometry(f"{self._width}x{self._height}+{x}+{y}")

    def move_to_position(self, x: int, y: int, animate: bool = False, duration_ms: int = 300):
        """
        Move window to screen coordinates

        Args:
            x: Screen X coordinate
            y: Screen Y coordinate
            animate: Whether to animate the movement
            duration_ms: Animation duration in milliseconds
        """
        if not self._root:
            logger.warning("Cannot move window: not created")
            return

        if animate:
            # Simple animation could be implemented here
            # For now, just move directly to keep it lightweight
            pass

        self._root.geometry(f"+{x}+{y}")
        logger.debug(f"Window moved to ({x}, {y})")

    def move_to_normalized(self, norm_x: float, norm_y: float, offset_x: int = 0, offset_y: int = 0):
        """
        Move window using normalized coordinates (0.0 to 1.0)

        Args:
            norm_x: Normalized X (0.0 = left, 1.0 = right)
            norm_y: Normalized Y (0.0 = top, 1.0 = bottom)
            offset_x: Pixel offset from calculated position
            offset_y: Pixel offset from calculated position
        """
        if not self._root:
            return

        screen_width = self._root.winfo_screenwidth()
        screen_height = self._root.winfo_screenheight()

        # Calculate pixel position
        x = int(norm_x * screen_width) + offset_x - (self._width // 2)
        y = int(norm_y * screen_height) + offset_y - (self._height // 2)

        self.move_to_position(x, y)

    def set_opacity(self, opacity: float, transition_ms: int = 200):
        """
        Set window opacity

        Args:
            opacity: Opacity level (0.0 to 1.0)
            transition_ms: Fade transition duration
        """
        self._opacity = max(0.0, min(1.0, opacity))

        if self._root:
            self._set_opacity_internal(self._opacity)
            logger.debug(f"Opacity set to {self._opacity}")

    def _set_opacity_internal(self, opacity: float):
        """Internal method to set opacity on the window"""
        if not self._root:
            return

        # Tkinter opacity (alpha) ranges from 0.0 to 1.0
        self._root.attributes('-alpha', opacity)

    def get_canvas(self) -> Optional[tk.Canvas]:
        """Get the canvas widget for drawing"""
        return self._canvas

    def update(self):
        """Process pending events (call this in the main loop)"""
        if self._root:
            self._root.update_idletasks()
            try:
                self._root.update()
            except tk.TclError:
                # Window was closed
                pass

    def is_closing(self) -> bool:
        """Check if the window is being closed"""
        return self._is_closing

    def _on_close(self):
        """Handle window close event"""
        logger.info("Window close requested")
        self._is_closing = True

    def destroy(self):
        """Destroy the window"""
        if self._root:
            logger.info("Destroying avatar window")
            try:
                self._root.destroy()
            except tk.TclError:
                pass
            self._root = None
            self._canvas = None

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def opacity(self) -> float:
        return self._opacity
