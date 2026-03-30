"""Renderer module for Kiri Personality Plugin."""

# Lazy imports to avoid tkinter dependency on import
def __getattr__(name):
    if name == 'AvatarWindow':
        from .window import AvatarWindow
        return AvatarWindow
    if name == 'AnimationCanvas':
        from .canvas import AnimationCanvas
        return AnimationCanvas
    if name == 'Compositor':
        from .compositor import Compositor
        return Compositor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['AvatarWindow', 'AnimationCanvas', 'Compositor']
