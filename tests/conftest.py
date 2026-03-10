# tests/conftest.py
"""pytest configuration and fixtures for the test suite.

This file ensures the project root is on ``sys.path`` so that imports like
``from webapp.main import app`` work regardless of which directory pytest
changes to during collection.
"""
import os
import sys

# Add the repository root to sys.path to make packages importable.
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)
