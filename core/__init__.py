"""Core infrastructure package."""

from .governor import Governor
from .api_manager import APIManager
from .project_state import ProjectState, get_state
from .english_engine import EnglishEngine

# Urdu engine is optional - for future expansion to Urdu-speaking audiences
# from .urdu_engine import UrduEngine

__all__ = [
    'Governor',
    'APIManager',
    'ProjectState',
    'get_state',
    'EnglishEngine'
]
