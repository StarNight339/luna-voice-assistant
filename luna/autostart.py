"""เปิด Luna ตอนเข้า Windows ผ่าน HKCU\\...\\Run (ไม่ต้องใช้สิทธิ์ admin)"""
import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = "Luna"


def startup_command(python=None):
    """คำสั่งที่ Windows จะรันตอน login: pythonw (ไม่มีหน้าต่าง console) -m luna
    (`uv sync` ติดตั้ง package luna ลง venv แล้ว จึงรันได้จาก working directory ใดก็ได้)"""
    exe = Path(python or sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    if pythonw.exists() or python is not None:
        exe = pythonw
    return subprocess.list2cmdline([str(exe), "-m", "luna"])


def is_enabled():
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE)
            return True
    except FileNotFoundError:
        return False


def enable():
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, VALUE, 0, winreg.REG_SZ, startup_command())


def disable():
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE)
    except FileNotFoundError:
        pass
