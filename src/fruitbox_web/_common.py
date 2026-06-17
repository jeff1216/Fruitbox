import os

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ONNX_PATH     = os.path.join(_PROJECT_ROOT, "web_assets", "fruitbox_policy.onnx")
