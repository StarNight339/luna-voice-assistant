"""เปิด Luna ตอนเข้า Windows ผ่าน HKCU\\...\\Run (ไม่ต้องใช้สิทธิ์ admin)"""
import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = "Luna"


def launcher(prefix=None, base_prefix=None):
    """[exe, *args] สำหรับเปิด Luna แบบไม่มีหน้าต่าง console

    pythonw.exe (และ gui-scripts) ใน venv ที่ uv สร้างเป็นโปรแกรม console -> Windows เปิด terminal ขึ้นมา
    จึงเรียก pythonw.exe ของ Python หลัก (GUI จริง) แล้วให้มันโหลด site-packages ของ venv เอง
    ตั้ง sys.prefix เป็น venv ด้วย เพราะ asr.py หา DLL ของ CUDA จาก sys.prefix"""
    venv, base = Path(prefix or sys.prefix), Path(base_prefix or sys.base_prefix)
    pythonw = str(base / "pythonw.exe")
    if venv == base:  # ไม่ได้อยู่ใน venv
        return [pythonw, "-m", "luna"]
    boot = (f"import site,sys;sys.prefix=sys.exec_prefix={str(venv)!r};"
            f"site.addsitedir({str(venv / 'Lib' / 'site-packages')!r});"
            "sys.argv[0]='luna';from luna.__main__ import main;main()")
    return [pythonw, "-c", boot]


def startup_command(prefix=None, base_prefix=None):
    """คำสั่งที่ Windows จะรันตอน login (รันได้จาก working directory ใดก็ได้)"""
    return subprocess.list2cmdline(launcher(prefix, base_prefix))


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
