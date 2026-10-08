"""Luna — เรียก "เฮ้ ลูน่า" แล้วสั่งงานคอมเป็นภาษาไทย

ใช้งาน:
    luna                      # รันเบื้องหลังพร้อมไอคอนใน system tray (ค่าเริ่มต้น)
    luna --console            # รันใน console เห็น log สด
    luna --console --no-wake  # กด Enter แทน wake word (ทดสอบคำสั่ง)
    luna --console --debug    # พิมพ์คะแนน wake word
    luna install-startup      # เปิด Luna อัตโนมัติตอนเข้า Windows
    luna uninstall-startup
"""
import argparse
import ctypes
import logging
import sys
from logging.handlers import RotatingFileHandler

from . import __version__, autostart
from .paths import LOG_DIR, LOG_FILE, ensure_config

MUTEX_NAME = "Local\\LunaVoiceAssistant"
ERROR_ALREADY_EXISTS = 183


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


def main(argv=None):
    p = argparse.ArgumentParser(prog="luna", description="ผู้ช่วยสั่งงานคอมด้วยเสียงภาษาไทย")
    p.add_argument("action", nargs="?", choices=["run", "install-startup", "uninstall-startup"], default="run")
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
    if args.no_wake and not args.console:
        p.error("--no-wake ต้องใช้คู่กับ --console")

    setup_logging(args.console)
    log = logging.getLogger("luna")
    mutex = single_instance()
    if mutex is None:
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

        run_tray(luna)


if __name__ == "__main__":
    main()
