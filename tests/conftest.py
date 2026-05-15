# conftest.py — shared pytest configuration
import sys, os

# Always insert src/ so test modules can import without installing the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
