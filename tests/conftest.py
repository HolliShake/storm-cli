import sys
import os

# Ensure the workspace root is on sys.path so `from src.xxx` works
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)
sys.path.insert(0, os.path.join(workspace_root, 'src'))
