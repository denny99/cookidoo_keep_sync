"""Pytest config: macht das Custom-Component-Package importierbar ohne HA-Setup."""
import sys
from pathlib import Path

_COMPONENT_DIR = (
    Path(__file__).parent.parent / "custom_components" / "cookidoo_keep_sync"
)
sys.path.insert(0, str(_COMPONENT_DIR))
