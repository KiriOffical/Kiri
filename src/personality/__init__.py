"""Kiri Personality Plugin - A local-first avatar plugin for Kiri Assistant."""

__version__ = "5.0.0"

# Lazy imports to avoid tkinter dependency on import
def __getattr__(name):
    if name == 'PersonalityPlugin':
        from .main import PersonalityPlugin
        return PersonalityPlugin
    if name == 'main':
        from .main import main
        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['PersonalityPlugin', 'main']
