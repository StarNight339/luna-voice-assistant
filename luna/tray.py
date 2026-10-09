"""ไอคอนใน system tray: เปิด/หยุดฟัง, ตั้งค่า, log, เปิดตอนเข้า Windows, ออก"""
import ctypes
import logging
import os
import threading

import pystray
from PIL import Image, ImageEnhance, ImageOps

from . import autostart, commands, shortcut
from .paths import LOG_DIR, ROOT

log = logging.getLogger(__name__)

TOGGLE_EVENT = "Local\\LunaToggle"  # ตรงกับ __main__.TOGGLE_EVENT
WAIT_OBJECT_0 = 0

STATE_TEXT = {
    "starting": "กำลังโหลดโมเดล...",
    "listening": "ฟังอยู่ — พูด \"เฮ้ ลูน่า\"",
    "paused": "หยุดฟังชั่วคราว",
    "error": "มีปัญหา",
    "stopped": "ปิดแล้ว",
}


def _icons():
    base = Image.open(ROOT / "assets" / "listening.gif").convert("RGBA").resize((64, 64), Image.LANCZOS)
    paused = ImageEnhance.Brightness(ImageOps.grayscale(base).convert("RGBA")).enhance(0.5)
    error = Image.blend(base, Image.new("RGBA", base.size, (255, 59, 48, 255)), 0.45)
    return {"listening": base, "starting": paused, "paused": paused, "error": error, "stopped": paused}


def run_tray(luna):
    icons = _icons()
    detail = {"text": ""}

    def on_state(state, text=""):
        log.info("สถานะ: %s %s", state, text)
        detail["text"] = text
        icon.icon = icons.get(state, icons["paused"])
        icon.title = "Luna — " + STATE_TEXT.get(state, state) + (f": {text}" if text else "")
        icon.update_menu()

    def notify(title, emoji):
        cfg = getattr(luna, "cfg", None)
        if cfg and cfg.get("island"):
            commands.island(cfg, "/notify", {"title": title, "icon": emoji, "duration": 2})
        else:  # ไม่มี Dynamic Island ใช้ toast ของ Windows แทน
            icon.notify(title, "Luna")

    def toggle(_icon=None, _item=None):
        if luna.paused:
            luna.resume()
            notify("Luna ฟังต่อแล้ว", "🎙️")
        else:
            luna.pause()
            notify("Luna หยุดฟังชั่วคราว", "⏸️")

    def toggle_startup(_icon, _item):
        if autostart.is_enabled():
            autostart.disable()
        else:
            autostart.enable()
        icon.update_menu()

    def toggle_shortcut(_icon, _item):
        try:
            if shortcut.is_enabled():
                shortcut.disable()
            else:
                shortcut.enable()
        except Exception:
            log.exception("แก้ทางลัดไม่ได้")
        icon.update_menu()

    def listen_toggle():
        """ดับเบิลคลิกทางลัดตอน Luna เปิดอยู่ -> instance ใหม่ SetEvent -> สลับหยุดฟัง/ฟังต่อ"""
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateEventW.restype = ctypes.c_void_p
        handle = ctypes.c_void_p(kernel32.CreateEventW(None, False, False, TOGGLE_EVENT))  # auto-reset
        if not handle.value:
            log.warning("สร้าง toggle event ไม่ได้")
            return
        while not luna._stop.is_set():
            if kernel32.WaitForSingleObject(handle, 500) == WAIT_OBJECT_0:
                toggle()

    def quit_app(_icon, _item):
        luna.stop()
        icon.stop()

    def status_text(_item):
        text = STATE_TEXT.get(luna.state, luna.state)
        return f"{text}: {detail['text']}" if detail["text"] else text

    menu = pystray.Menu(
        pystray.MenuItem(status_text, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda _: "ฟังต่อ" if luna.paused else "หยุดฟังชั่วคราว", toggle, default=True),
        pystray.MenuItem("เปิดไฟล์ตั้งค่า", lambda: os.startfile(luna.config_path)),
        pystray.MenuItem("โหลดตั้งค่าใหม่", lambda: luna.reload_config()),
        pystray.MenuItem("เปิดโฟลเดอร์ log", lambda: os.startfile(LOG_DIR)),
        pystray.MenuItem("เปิดตอนเข้า Windows", toggle_startup, checked=lambda _: autostart.is_enabled()),
        pystray.MenuItem("ทางลัดใน Start Menu / Desktop", toggle_shortcut, checked=lambda _: shortcut.is_enabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("ออก", quit_app),
    )
    icon = pystray.Icon("Luna", icons["starting"], "Luna — " + STATE_TEXT["starting"], menu)
    luna.on_state = on_state

    def start_bot(tray_icon):
        tray_icon.visible = True
        # daemon: ถ้ากดออกระหว่าง Whisper กำลังถอดเสียง ไม่ต้องรอให้เสร็จ
        threading.Thread(target=luna.run, name="luna-bot", daemon=True).start()
        threading.Thread(target=listen_toggle, name="luna-toggle", daemon=True).start()

    icon.run(setup=start_bot)
