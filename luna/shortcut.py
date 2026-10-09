"""ทางลัด Luna ใน Start Menu / Desktop: ดับเบิลคลิก = เปิด Luna, ถ้าเปิดอยู่แล้ว = หยุดฟัง/ฟังต่อ"""
import ctypes
import subprocess
import uuid
from pathlib import Path

from PIL import Image

from .autostart import launcher
from .paths import LOG_DIR, ROOT

ICON = LOG_DIR / "luna.ico"
NAME = "Luna.lnk"
DESCRIPTION = "เปิด Luna / หยุดฟัง-ฟังต่อ"
FOLDERID_PROGRAMS = "{A77F5D77-2E2B-44C3-A6A2-ABA601054A51}"  # Start Menu\Programs ของผู้ใช้
FOLDERID_DESKTOP = "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"   # ตามจริง แม้ถูก OneDrive ย้าย


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]


def _known_folder(folder_id):
    guid = _GUID.from_buffer_copy(uuid.UUID(folder_id).bytes_le)
    out = ctypes.c_wchar_p()
    if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)):
        raise OSError(f"หาโฟลเดอร์ {folder_id} ไม่ได้")
    try:
        return Path(out.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(out)


def locations():
    """[Start Menu, Desktop]"""
    return [_known_folder(FOLDERID_PROGRAMS) / NAME, _known_folder(FOLDERID_DESKTOP) / NAME]


def _quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def ps_script(lnk_paths, command, workdir, icon):
    """สคริปต์ PowerShell สร้าง .lnk ผ่าน WScript.Shell (ไม่ต้องพึ่ง pywin32)"""
    lines = ["$sh = New-Object -ComObject WScript.Shell"]
    for lnk in lnk_paths:
        lines += [
            f"$s = $sh.CreateShortcut({_quote(lnk)})",
            f"$s.TargetPath = {_quote(command[0])}",
            f"$s.Arguments = {_quote(subprocess.list2cmdline(command[1:]))}",
            f"$s.WorkingDirectory = {_quote(workdir)}",
            f"$s.IconLocation = {_quote(icon)}",
            f"$s.Description = {_quote(DESCRIPTION)}",
            "$s.Save()",
        ]
    return "\n".join(lines)


def _make_icon():
    ICON.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(ROOT / "assets" / "listening.gif").convert("RGBA")
    img.save(ICON, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])


def is_enabled():
    return locations()[0].exists()


def enable():
    _make_icon()
    script = ps_script(locations(), launcher(), ROOT, ICON)
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                   check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)


def disable():
    for lnk in locations():
        lnk.unlink(missing_ok=True)
