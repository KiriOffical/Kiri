"""
JSON Schema Validation for Kiri Personality Plugin Protocol

This module provides validation functions for incoming JSON-RPC requests
to ensure they conform to the expected schema.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path


class ValidationError(Exception):
    """Raised when request validation fails"""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


# Valid animation states (predefined set, no generative AI)
VALID_STATES = {
    "idle",
    "thinking",
    "speaking",
    "listening",
    "tip_available",
    "alert",
    "happy",
    "confused",
    "sleeping",
    "loading"
}

# Valid RPC methods
VALID_METHODS = {
    "set_state",
    "set_position",
    "set_opacity",
    "play_sound",
    "stop_animation",
    "shutdown"
}


def validate_request(request: Dict[str, Any]) -> bool:
    """
    Validate an incoming JSON-RPC request against the schema

    Args:
        request: Parsed JSON-RPC request object

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    # Validate JSON-RPC version
    if request.get('jsonrpc') != '2.0':
        raise ValidationError("Invalid JSON-RPC version", "jsonrpc")

    # Validate method
    method = request.get('method')
    if not method or method not in VALID_METHODS:
        raise ValidationError(f"Invalid or missing method: {method}", "method")

    # Validate ID exists
    if 'id' not in request:
        raise ValidationError("Missing request ID", "id")

    # Validate params based on method
    params = request.get('params', {})
    _validate_params(method, params)

    return True


def _validate_params(method: str, params: Dict[str, Any]):
    """Validate method-specific parameters"""

    if method == 'set_state':
        _validate_set_state_params(params)
    elif method == 'set_position':
        _validate_set_position_params(params)
    elif method == 'set_opacity':
        _validate_set_opacity_params(params)
    elif method == 'play_sound':
        _validate_play_sound_params(params)
    elif method == 'stop_animation':
        _validate_stop_animation_params(params)
    elif method == 'shutdown':
        _validate_shutdown_params(params)


def _validate_set_state_params(params: Dict[str, Any]):
    """Validate set_state method parameters"""
    if 'state' not in params:
        raise ValidationError("Missing required parameter: state", "params.state")

    state = params['state']
    if state not in VALID_STATES:
        raise ValidationError(
            f"Invalid state: {state}. Must be one of: {VALID_STATES}",
            "params.state"
        )

    # Validate optional parameters
    if 'priority' in params:
        priority = params['priority']
        if not isinstance(priority, int) or priority < 0 or priority > 100:
            raise ValidationError(
                "Priority must be integer between 0 and 100",
                "params.priority"
            )

    if 'loop' in params:
        if not isinstance(params['loop'], bool):
            raise ValidationError("Loop must be boolean", "params.loop")

    if 'speed' in params:
        speed = params['speed']
        if not isinstance(speed, (int, float)) or speed < 0.1 or speed > 5.0:
            raise ValidationError(
                "Speed must be number between 0.1 and 5.0",
                "params.speed"
            )


def _validate_set_position_params(params: Dict[str, Any]):
    """Validate set_position method parameters"""
    if 'target' not in params:
        raise ValidationError("Missing required parameter: target", "params.target")

    target = params['target']
    if not isinstance(target, dict):
        raise ValidationError("Target must be an object", "params.target")

    if 'x' not in target or 'y' not in target:
        raise ValidationError(
            "Target must contain x and y coordinates",
            "params.target"
        )

    x = target['x']
    y = target['y']

    if not isinstance(x, (int, float)) or x < 0.0 or x > 1.0:
        raise ValidationError(
            "Target x must be number between 0.0 and 1.0",
            "params.target.x"
        )

    if not isinstance(y, (int, float)) or y < 0.0 or y > 1.0:
        raise ValidationError(
            "Target y must be number between 0.0 and 1.0",
            "params.target.y"
        )

    # Validate optional offsets
    if 'offset_x' in params:
        if not isinstance(params['offset_x'], int):
            raise ValidationError("offset_x must be integer", "params.offset_x")

    if 'offset_y' in params:
        if not isinstance(params['offset_y'], int):
            raise ValidationError("offset_y must be integer", "params.offset_y")

    if 'animation_duration_ms' in params:
        duration = params['animation_duration_ms']
        if not isinstance(duration, int) or duration < 0 or duration > 5000:
            raise ValidationError(
                "animation_duration_ms must be integer between 0 and 5000",
                "params.animation_duration_ms"
            )


def _validate_set_opacity_params(params: Dict[str, Any]):
    """Validate set_opacity method parameters"""
    if 'opacity' not in params:
        raise ValidationError("Missing required parameter: opacity", "params.opacity")

    opacity = params['opacity']
    if not isinstance(opacity, (int, float)) or opacity < 0.0 or opacity > 1.0:
        raise ValidationError(
            "Opacity must be number between 0.0 and 1.0",
            "params.opacity"
        )

    if 'transition_ms' in params:
        transition = params['transition_ms']
        if not isinstance(transition, int) or transition < 0 or transition > 2000:
            raise ValidationError(
                "transition_ms must be integer between 0 and 2000",
                "params.transition_ms"
            )


def _validate_play_sound_params(params: Dict[str, Any]):
    """Validate play_sound method parameters"""
    if 'sound_id' not in params:
        raise ValidationError("Missing required parameter: sound_id", "params.sound_id")

    if not isinstance(params['sound_id'], str):
        raise ValidationError("sound_id must be string", "params.sound_id")

    if 'volume' in params:
        volume = params['volume']
        if not isinstance(volume, (int, float)) or volume < 0.0 or volume > 1.0:
            raise ValidationError(
                "Volume must be number between 0.0 and 1.0",
                "params.volume"
            )


def _validate_stop_animation_params(params: Dict[str, Any]):
    """Validate stop_animation method parameters"""
    if 'fade_out' in params:
        if not isinstance(params['fade_out'], bool):
            raise ValidationError("fade_out must be boolean", "params.fade_out")


def _validate_shutdown_params(params: Dict[str, Any]):
    """Validate shutdown method parameters"""
    if 'save_state' in params:
        if not isinstance(params['save_state'], bool):
            raise ValidationError("save_state must be boolean", "params.save_state")


def load_schema_file(schema_path: str) -> Dict[str, Any]:
    """
    Load the JSON schema file for reference

    Args:
        schema_path: Path to schema.json file

    Returns:
        Parsed schema dictionary
    """
    path = Path(schema_path)
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
