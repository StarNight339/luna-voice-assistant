import ctypes

import pytest

from luna import autostart, winctl


def test_input_struct_matches_win32_size():
    # SendInput ปฏิเสธทั้งชุดถ้าขนาด INPUT ผิด (40 byte บน 64-bit, 28 บน 32-bit)
    assert ctypes.sizeof(winctl._INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)


def test_vk_lookup():
    assert winctl._vk("win") == 0x5B
    assert winctl._vk("D") == ord("D")
    assert winctl._vk("f4") == 0x73
    with pytest.raises(ValueError):
        winctl._vk("ไม่มีปุ่มนี้")


def test_system_status_text():
    status = winctl.system_status()
    assert status.startswith("CPU ") and "RAM " in status


def test_startup_command_uses_pythonw():
    cmd = autostart.startup_command(r"C:\proj\.venv\Scripts\python.exe")
    assert cmd == r"C:\proj\.venv\Scripts\pythonw.exe -m luna"


def test_startup_command_quotes_spaces():
    cmd = autostart.startup_command(r"C:\My Projects\.venv\Scripts\python.exe")
    assert cmd == r'"C:\My Projects\.venv\Scripts\pythonw.exe" -m luna'
