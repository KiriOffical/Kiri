"""
Kiri Personality Plugin - Main Entry Point

This is the main plugin executable that:
1. Initializes security (network blocking)
2. Sets up the renderer window
3. Listens for commands from Kiri Core via STDIN/STDOUT
4. Renders animations based on received state events

SECURITY: Network access is blocked immediately on startup.
No external connections are permitted.
"""

import sys
import json
import signal
from pathlib import Path
from typing import Dict, Any, Optional

# Import plugin modules
from src.personality.interface.protocol import JSONRPCProtocol, RequestHandler
from src.personality.interface.schema import validate_request, ValidationError
from src.personality.renderer.window import AvatarWindow
from src.personality.renderer.canvas import AnimationCanvas
from src.personality.renderer.compositor import Compositor
from src.personality.utils.logger import setup_logging
from src.personality.security.network_blocker import NetworkBlocker

# SECURITY: Network blocker is auto-enabled when imported
# This ensures no network calls can be made from any module

import logging
logger = logging.getLogger(__name__)


class PersonalityPlugin:
    """
    Main plugin class that coordinates all subsystems
    
    Receives state events from Kiri Core and renders appropriate animations.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the personality plugin
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        
        # Setup logging
        setup_logging(
            log_level=self.config.get("log_level", "INFO"),
            log_file=self.config.get("log_file")
        )
        
        logger.info("Initializing Kiri Personality Plugin v5.0.0")
        
        # Verify security is enabled
        if not NetworkBlocker.is_blocked():
            logger.critical("SECURITY FAILURE: Network blocking not enabled!")
            raise RuntimeError("Network blocking must be enabled")
        
        logger.info(f"Security status: {NetworkBlocker().get_status()}")
        
        # Initialize subsystems
        assets_dir = Path(__file__).parent / "assets"
        self.compositor = Compositor(str(assets_dir))
        
        self.window = AvatarWindow(
            width=self.config.get("window_width", 200),
            height=self.config.get("window_height", 200),
            opacity=self.config.get("opacity", 1.0)
        )
        
        self.animation_canvas: Optional[AnimationCanvas] = None
        
        # Setup request handlers
        self.handler = RequestHandler()
        self._register_handlers()
        
        # Protocol layer
        self.protocol = JSONRPCProtocol(self.handler)
        
        # State
        self._running = False
        
        logger.info("Plugin initialization complete")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file"""
        path = Path(config_path)
        
        if not path.exists():
            # Return defaults if config doesn't exist
            return {
                "enabled": True,
                "opacity": 1.0,
                "sound_enabled": True,
                "window_width": 200,
                "window_height": 200,
                "log_level": "INFO"
            }
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _register_handlers(self):
        """Register JSON-RPC method handlers"""
        self.handler.register("set_state", self._handle_set_state)
        self.handler.register("set_position", self._handle_set_position)
        self.handler.register("set_opacity", self._handle_set_opacity)
        self.handler.register("play_sound", self._handle_play_sound)
        self.handler.register("stop_animation", self._handle_stop_animation)
        self.handler.register("shutdown", self._handle_shutdown)
    
    def _handle_set_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set_state command from Core"""
        state = params.get("state")
        priority = params.get("priority", 50)
        loop = params.get("loop", True)
        speed = params.get("speed", 1.0)
        
        logger.info(f"Setting state: {state} (priority={priority})")
        
        # Update compositor state
        result = self.compositor.set_state(state, priority, loop, speed)
        
        if not result["accepted"]:
            return {
                "status": "rejected",
                "reason": result.get("reason")
            }
        
        # Load and play animation
        frame_paths = self.compositor.get_frame_paths(state)
        
        if frame_paths and self.animation_canvas:
            self.animation_canvas.load_frames(frame_paths)
            self.animation_canvas.play(loop=loop, speed=speed)
        
        return {
            "status": "rendered",
            "state": state,
            "frame_id": f"{state}_frame_001"
        }
    
    def _handle_set_position(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set_position command from Core"""
        target = params.get("target", {})
        offset_x = params.get("offset_x", 0)
        offset_y = params.get("offset_y", 0)
        
        norm_x = target.get("x", 0.5)
        norm_y = target.get("y", 0.5)
        
        logger.info(f"Moving to position: ({norm_x}, {norm_y})")
        
        self.window.move_to_normalized(norm_x, norm_y, offset_x, offset_y)
        
        return {
            "status": "moving",
            "position": {"x": norm_x, "y": norm_y}
        }
    
    def _handle_set_opacity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set_opacity command from Core"""
        opacity = params.get("opacity", 1.0)
        transition_ms = params.get("transition_ms", 200)
        
        logger.info(f"Setting opacity: {opacity}")
        
        self.window.set_opacity(opacity, transition_ms)
        
        return {
            "status": "success",
            "opacity": opacity
        }
    
    def _handle_play_sound(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle play_sound command from Core"""
        sound_id = params.get("sound_id")
        volume = params.get("volume", 0.5)
        
        if not self.config.get("sound_enabled", True):
            return {
                "status": "disabled",
                "reason": "Sound is disabled in configuration"
            }
        
        logger.info(f"Playing sound: {sound_id} (volume={volume})")
        
        # Sound implementation would go here
        # For now, just acknowledge
        
        return {
            "status": "playing",
            "sound_id": sound_id
        }
    
    def _handle_stop_animation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stop_animation command from Core"""
        fade_out = params.get("fade_out", False)
        
        logger.info("Stopping animation")
        
        if self.animation_canvas:
            self.animation_canvas.stop(fade_out=fade_out)
        
        self.compositor.clear_state()
        
        return {
            "status": "success"
        }
    
    def _handle_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shutdown command from Core"""
        save_state = params.get("save_state", True)
        
        logger.info(f"Shutdown requested (save_state={save_state})")
        
        self._running = False
        
        return {
            "status": "shutting_down"
        }
    
    def run(self):
        """Run the plugin main loop"""
        logger.info("Starting plugin main loop")
        
        # Create window
        self.window.create()
        
        # Initialize animation canvas
        canvas_widget = self.window.get_canvas()
        if canvas_widget:
            self.animation_canvas = AnimationCanvas(canvas_widget)
        
        # Set default idle state
        idle_frames = self.compositor.get_frame_paths("idle")
        if idle_frames and self.animation_canvas:
            self.animation_canvas.load_frames(idle_frames)
            self.animation_canvas.play(loop=True)
        
        self._running = True
        
        # Start protocol listener in background
        self.protocol.start(blocking=False)
        
        # Main event loop
        try:
            while self._running and not self.window.is_closing():
                # Process window events
                self.window.update()
                
                # Small sleep to reduce CPU usage
                import time
                time.sleep(0.016)  # ~60fps cap
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of the plugin"""
        logger.info("Shutting down plugin")
        
        self._running = False
        
        # Stop protocol
        self.protocol.stop()
        
        # Destroy window
        if self.window:
            self.window.destroy()
        
        logger.info("Plugin shutdown complete")


def main():
    """Main entry point"""
    # Get config path from command line or use default
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    
    try:
        plugin = PersonalityPlugin(config_path)
        plugin.run()
    except Exception as e:
        logger.error(f"Plugin error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
