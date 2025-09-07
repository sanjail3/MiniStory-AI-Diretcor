"""
Scene Description Generation Module

This module handles scene description generation and reference image attachment:
- Scene description generation with LLM
- Character reference image attachment
- Location reference image attachment
- Combined reference attachment workflow
"""

from .scene_describer import SceneDescriber

__all__ = ['SceneDescriber']

