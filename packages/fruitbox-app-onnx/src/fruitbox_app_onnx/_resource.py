import os
import sys


def resource_path(rel: str) -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, rel)
    direct = os.path.join(os.getcwd(), rel)
    if os.path.exists(direct):
        return direct
    return os.path.join(os.getcwd(), "web_assets", rel)
