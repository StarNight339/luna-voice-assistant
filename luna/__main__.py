"""Luna — เรียก "เฮ้ ลูน่า" แล้วสั่งงานคอมเป็นภาษาไทย

ใช้งาน:
    luna                      # รันเบื้องหลังพร้อมไอคอนใน system tray (ค่าเริ่มต้น)
    luna --console            # รันใน console เห็น log สด
    luna --console --no-wake  # กด Enter แทน wake word (ทดสอบคำสั่ง)
    luna --console --debug    # พิมพ์คะแนน wake word
    luna install-startup      # เปิด Luna อัตโนมัติตอนเข้า Windows
    luna uninstall-startup
    luna install-shortcut     # ทางลัดใน Start Menu / Desktop (เปิดซ้ำ = หยุดฟัง/ฟังต่อ)
    luna uninstall-shortcut
"""
import argparse
import ctypes
import logging
import sys
from logging.handlers import RotatingFileHandler

from . import __version__, autostart, shortcut
from .paths import LOG_DIR, LOG_FILE, ensure_config

MUTEX_NAME = "Local\\LunaVoiceAssistant"
TOGGLE_EVENT = "Local\\LunaToggle"  # instance ที่สองสั่ง instance ที่รันอยู่ให้หยุดฟัง/ฟังต่อ
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002
SHORTCUT_OFFERED = LOG_DIR / "shortcut-offered"


def setup_logging(console):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handlers = [RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")]
    if console and sys.stderr is not None:  # pythonw ไม่มี stderr
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)  # ไม่ต้อง log ทุกครั้งที่ถอดเสียง


def single_instance():
    """คืน handle ของ mutex (ต้องเก็บไว้ตลอดอายุโปรแกรม) หรือ None ถ้ามี Luna เปิดอยู่แล้ว"""
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return None
    return handle


def signal_toggle():
    """บอก Luna ที่เปิดอยู่ให้สลับหยุดฟัง/ฟังต่อ; False ถ้าหา event ไม่เจอ (instance เวอร์ชันเก่า)"""
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenEventW.restype = ctypes.c_void_p
    handle = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, TOGGLE_EVENT)
    if not handle:
        return False
    try:
        return bool(kernel32.SetEvent(ctypes.c_void_p(handle)))
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))


def offer_shortcut(log):
    """สร้างทางลัดให้ครั้งแรกครั้งเดียว — ถ้าผู้ใช้ลบทีหลังจะไม่สร้างกลับมาเอง"""
    if SHORTCUT_OFFERED.exists():
        return
    try:
        shortcut.enable()
        log.info("สร้างทางลัด Luna ใน Start Menu / Desktop แล้ว")
    except Exception:
        log.exception("สร้างทางลัดไม่ได้")
    SHORTCUT_OFFERED.touch()


def main(argv=None):
    p = argparse.ArgumentParser(prog="luna", description="ผู้ช่วยสั่งงานคอมด้วยเสียงภาษาไทย")
    p.add_argument("action", nargs="?", choices=["run", "install-startup", "uninstall-startup", "install-shortcut", "uninstall-shortcut"], default="run")
    p.add_argument("--console", action="store_true", help="รันใน console แทน system tray")
    p.add_argument("--no-wake", action="store_true", help="กด Enter แทน wake word (ใช้คู่กับ --console)")
    p.add_argument("--debug", action="store_true", help="พิมพ์คะแนน wake word")
    p.add_argument("--cpu", action="store_true", help="บังคับใช้ CPU")
    p.add_argument("--config", help="path ของ config.yaml")
    p.add_argument("--version", action="version", version=f"luna {__version__}")
    args = p.parse_args(argv)

    if args.action == "install-startup":
        autostart.enable()
        print("เปิด Luna ตอนเข้า Windows แล้ว:", autostart.startup_command())
        return
    if args.action == "uninstall-startup":
        autostart.disable()
        print("ยกเลิกการเปิด Luna ตอนเข้า Windows แล้ว")
        return
    if args.action == "install-shortcut":
        shortcut.enable()
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        SHORTCUT_OFFERED.touch()
        print("สร้างทางลัด Luna แล้ว:", *shortcut.locations(), sep="\n  ")
        return
    if args.action == "uninstall-shortcut":
        shortcut.disable()
        print("ลบทางลัด Luna แล้ว")
        return
    if args.no_wake and not args.console:
        p.error("--no-wake ต้องใช้คู่กับ --console")

    setup_logging(args.console)
    log = logging.getLogger("luna")
    mutex = single_instance()
    if mutex is None:
        if not args.console and signal_toggle():
            log.info("Luna เปิดอยู่แล้ว — สั่งสลับหยุดฟัง/ฟังต่อ")
            return
        msg = "Luna เปิดอยู่แล้ว (ดูไอคอนใน system tray)"
        log.warning(msg)
        if not args.console:
            ctypes.windll.user32.MessageBoxW(None, msg, "Luna", 0x40)
        return

    from .bot import Luna

    config = args.config or ensure_config()
    log.info("Luna %s — config: %s", __version__, config)
    luna = Luna(config, cpu=args.cpu, no_wake=args.no_wake, debug=args.debug,
                on_state=lambda state, detail="": log.info("สถานะ: %s %s", state, detail))
    if args.console:
        try:
            luna.run()
        except KeyboardInterrupt:
            log.info("ปิด Luna")
    else:
        from .tray import run_tray

        offer_shortcut(log)
        if autostart.is_enabled():  # อัปเดตคำสั่งเก่า (pythonw ของ uv มีหน้าต่าง console) เป็น pythonw ของ Python หลัก
            autostart.enable()
        run_tray(luna)


if __name__ == "__main__":
    main()
