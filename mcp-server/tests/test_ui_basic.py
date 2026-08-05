"""Basic UI tests"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui import create_header, ComponentType

def test_create_header():
    header = create_header("Test")
    assert header.type == ComponentType.HEADER
    assert header.props["title"] == "Test"
    print("Test passed!")

if __name__ == "__main__":
    test_create_header()
