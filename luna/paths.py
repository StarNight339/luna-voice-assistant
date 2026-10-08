"""ตำแหน่งไฟล์ของโปรเจกต์: path ใน config ทั้งหมดอิงจาก ROOT"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.yaml"
CONFIG_EXAMPLE = ROOT / "config.example.yaml"
LOG_DIR = Path(os.environ.get("LOCALAPPDATA", ROOT)) / "Luna"
LOG_FILE = LOG_DIR / "luna.log"


def resolve(path):
    """path สัมพัทธ์ใน config -> path เต็มใต้ ROOT (รองรับ %APPDATA% ฯลฯ)"""
    p = Path(os.path.expandvars(str(path)))
    return p if p.is_absolute() else ROOT / p


def ensure_config():
    """ใช้ config.yaml ของผู้ใช้ ถ้ายังไม่มีให้คัดลอกจาก config.example.yaml"""
    if not CONFIG.exists():
        shutil.copyfile(CONFIG_EXAMPLE, CONFIG)
    return CONFIG
