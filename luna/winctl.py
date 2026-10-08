"""ควบคุม Windows ระดับล่างด้วย ctypes: กดคีย์/คีย์ผสม, พิมพ์ข้อความ, สถานะเครื่อง, ระดับเสียง"""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

VK = {
    # มีเดีย
    "mute": 0xAD, "volume_down": 0xAE, "volume_up": 0xAF,
    "next": 0xB0, "prev": 0xB1, "stop": 0xB2, "play_pause": 0xB3,
    # modifier
    "ctrl": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B,
    # ทั่วไป
    "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "space": 0x20, "backspace": 0x08, "delete": 0x2E,
    "printscreen": 0x2C, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    **{f"f{i}": 0x6F + i for i in range(1, 13)},
}
# คีย์ที่ต้องส่ง KEYEVENTF_EXTENDEDKEY ไม่งั้นบางแอปตีความเป็นปุ่มบน numpad
EXTENDED = {"mute", "volume_down", "volume_up", "next", "prev", "stop", "play_pause", "win", "delete",
            "printscreen", "home", "end", "pageup", "pagedown", "left", "up", "right", "down"}

KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x1, 0x2, 0x4


def _vk(name):
    name = name.lower()
    if name in VK:
        return VK[name]
    if len(name) == 1 and name.isalnum():
        return ord(name.upper())
    raise ValueError(f"ไม่รู้จักปุ่ม: {name}")


def _key(name, up=False):
    flags = (KEYEVENTF_EXTENDEDKEY if name.lower() in EXTENDED else 0) | (KEYEVENTF_KEYUP if up else 0)
    user32.keybd_event(_vk(name), 0, flags, 0)


def press_key(name, repeat=1):
    for _ in range(int(repeat)):
        _key(name)
        _key(name, up=True)


def hotkey(*keys):
    """กดคีย์ผสม เช่น hotkey('win', 'd') — กดตามลำดับ ปล่อยย้อนกลับ"""
    for k in keys:
        _key(k)
    for k in reversed(keys):
        _key(k, up=True)


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _MOUSEINPUT(ctypes.Structure):  # ไม่ได้ใช้ แต่ต้องอยู่ใน union ให้ขนาด INPUT ถูกต้องบน 64-bit
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


def type_text(text):
    """พิมพ์ข้อความ (ไทย/อังกฤษ/อีโมจิ) ลงหน้าต่างที่ focus อยู่ ไม่ขึ้นกับภาษาคีย์บอร์ดที่เลือกไว้"""
    data = text.encode("utf-16-le")
    units = [int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2)]
    inputs = []
    for u in units:
        if u == 0x0A:  # ขึ้นบรรทัดใหม่ = Enter
            inputs += [_INPUT(type=1, ki=_KEYBDINPUT(wVk=VK["enter"])),
                       _INPUT(type=1, ki=_KEYBDINPUT(wVk=VK["enter"], dwFlags=KEYEVENTF_KEYUP))]
            continue
        inputs += [_INPUT(type=1, ki=_KEYBDINPUT(wScan=u, dwFlags=KEYEVENTF_UNICODE)),
                   _INPUT(type=1, ki=_KEYBDINPUT(wScan=u, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))]
    arr = (_INPUT * len(inputs))(*inputs)
    sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(_INPUT))
    if sent != len(inputs):
        raise OSError(f"SendInput ส่งได้ {sent}/{len(inputs)} (หน้าต่างที่ focus อาจรันแบบ admin)")


def _filetime(ft):
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


def cpu_percent(interval=0.5):
    def times():
        idle, kern, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
        kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
        return _filetime(idle), _filetime(kern) + _filetime(user)  # kernel time รวม idle ไว้แล้ว

    i0, t0 = times()
    time.sleep(interval)
    i1, t1 = times()
    return 0.0 if t1 == t0 else 100.0 * (1 - (i1 - i0) / (t1 - t0))


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


class _SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                ("BatteryLifeTime", wintypes.DWORD), ("BatteryFullLifeTime", wintypes.DWORD)]


def system_status():
    """'CPU 12% · RAM 58% (9.1/15.7 GB) · แบต 80% (ชาร์จอยู่)'"""
    parts = [f"CPU {cpu_percent():.0f}%"]

    mem = _MEMORYSTATUSEX(dwLength=ctypes.sizeof(_MEMORYSTATUSEX))
    if kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
        used = (mem.ullTotalPhys - mem.ullAvailPhys) / 1024 ** 3
        parts.append(f"RAM {mem.dwMemoryLoad}% ({used:.1f}/{mem.ullTotalPhys / 1024 ** 3:.1f} GB)")

    power = _SYSTEM_POWER_STATUS()
    if kernel32.GetSystemPowerStatus(ctypes.byref(power)) and power.BatteryFlag != 128 \
            and power.BatteryLifePercent != 255:  # 128 = ไม่มีแบต, 255 = ไม่ทราบ
        plugged = "ชาร์จอยู่" if power.ACLineStatus == 1 else "ใช้แบต"
        parts.append(f"แบต {power.BatteryLifePercent}% ({plugged})")
    return " · ".join(parts)


def set_volume(percent):
    """ตั้งระดับเสียงด้วยปุ่ม volume (Windows ขยับทีละ 2%): ลดลงสุดก่อน แล้วเพิ่มขึ้นตามที่ต้องการ"""
    percent = max(0, min(100, int(percent)))
    press_key("volume_down", 50)
    press_key("volume_up", round(percent / 2))
    return percent
