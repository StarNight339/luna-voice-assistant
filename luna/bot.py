"""วงจรหลักของ Luna: ฟัง wake word -> อัดคำสั่ง -> Whisper -> จับคู่ -> ทำ action

รันใน thread แยกได้ (tray อยู่ main thread) และควบคุมด้วย pause()/resume()/reload_config()/stop()
"""
import logging
import queue
import threading
import time

from . import asr, audio, commands
from .audio import CHUNK, SR
from .paths import resolve

log = logging.getLogger(__name__)

CONFIRM_WORDS = ("ยืนยัน", "ตกลง", "ใช่", "confirm", "yes")
MIC_SILENT_SECONDS = 3  # ไม่มีเสียงเข้ามาเลยนานเท่านี้ = ไมค์หลุด


class _Interrupt(Exception):
    """ออกจากการรอเสียงเพราะ pause/stop/reload"""


class _MicLost(Exception):
    pass


class Luna:
    def __init__(self, config_path, *, cpu=False, no_wake=False, debug=False, on_state=None):
        self.config_path = config_path
        self.cpu, self.no_wake, self.debug = cpu, no_wake, debug
        self.on_state = on_state or (lambda state, detail="": None)
        self.state = "starting"
        self._paused = threading.Event()
        self._stop = threading.Event()
        self._reload = threading.Event()
        self._q = queue.Queue()

    # ---- ควบคุมจากภายนอก (thread-safe) ----
    def pause(self):
        self._paused.set()

    def resume(self):
        self._paused.clear()

    @property
    def paused(self):
        return self._paused.is_set()

    def reload_config(self):
        self._reload.set()

    def stop(self):
        self._stop.set()

    # ---- โหลด ----
    def _set_state(self, state, detail=""):
        self.state = state
        self.on_state(state, detail)

    def _load_config(self):
        self.cfg = commands.load_config(self.config_path)
        self.sounds = audio.load_sounds(self.cfg)
        self.prompt = asr.build_prompt(self.model, self.cfg)
        self.listening_notice = {"title": "ฟังอยู่...", "icon": "🎙️",
                                 "duration": self.cfg.get("listen", {}).get("max", 10)}
        if self.cfg.get("listening_image"):
            image = resolve(self.cfg["listening_image"])
            if image.exists():
                self.listening_notice["image"] = str(image)  # DynamicIsland อ่านไฟล์จาก path ในเครื่องได้
        self.oww = None
        if not self.no_wake:
            from openwakeword.model import Model

            wake = self.cfg["wake"]
            path = resolve(wake["model"])
            self.oww = Model(wakeword_models=[str(path) if path.exists() else wake["model"]],
                             inference_framework="onnx")
        self.ctx = {"play": lambda name: audio.play(self.sounds, name)}

    def _load(self):
        from faster_whisper.vad import get_vad_model

        self.cfg = commands.load_config(self.config_path)
        self.model, self.device = asr.load_model(self.cfg, cpu=self.cpu)
        self.vad = get_vad_model()
        self._load_config()
        log.info("โหลดเสร็จ (%s)", self.device)

    # ---- วงจรหลัก ----
    def run(self):
        import sounddevice as sd

        try:
            self._load()
        except Exception as e:
            log.exception("เริ่ม Luna ไม่สำเร็จ")
            self._set_state("error", str(e))
            return

        while not self._stop.is_set():
            if self._reload.is_set():
                self._reload.clear()
                try:
                    self._load_config()
                    log.info("โหลดตั้งค่าใหม่แล้ว")
                    commands.island(self.cfg, "/notify", {"title": "โหลดตั้งค่าใหม่แล้ว", "icon": "🔄", "duration": 3})
                except Exception as e:
                    log.exception("โหลดตั้งค่าใหม่ไม่สำเร็จ (ใช้ค่าเดิมต่อ)")
                    commands.island(self.cfg, "/notify", {"title": "config.yaml ผิดรูปแบบ", "body": str(e)[:80],
                                                          "icon": "❌", "color": "#FF3B30"})
            if self._paused.is_set():
                self._set_state("paused")
                while self._paused.is_set() and not self._stop.is_set() and not self._reload.is_set():
                    time.sleep(0.2)
                continue

            try:
                # เปิดไมค์เฉพาะตอนฟัง: หยุดชั่วคราว = ปิด stream จริง ไมค์ถูกปล่อย
                with sd.InputStream(samplerate=SR, channels=1, dtype="int16", blocksize=CHUNK,
                                    callback=lambda data, *_: self._q.put(data[:, 0].copy())):
                    audio.drain(self._q)
                    self._set_state("listening")
                    self._loop()
            except _Interrupt:
                pass
            except (_MicLost, sd.PortAudioError) as e:
                log.warning("ไมค์มีปัญหา (%s) — ลองเชื่อมต่อใหม่ใน 3 วินาที", e or "ไม่มีเสียงเข้า")
                self._set_state("error", "ไม่พบไมโครโฟน")
                self._stop.wait(3)
        self._set_state("stopped")

    def _chunk(self):
        """chunk เสียงถัดไป; ยกเลิกเมื่อ pause/stop/reload, แจ้งไมค์หลุดเมื่อเงียบสนิทนานเกิน"""
        waited = 0.0
        while True:
            if self._stop.is_set() or self._paused.is_set() or self._reload.is_set():
                raise _Interrupt
            try:
                return self._q.get(timeout=0.2)
            except queue.Empty:
                waited += 0.2
                if waited >= MIC_SILENT_SECONDS:
                    raise _MicLost

    def _wait_trigger(self):
        if self.no_wake:
            input()
            audio.drain(self._q)
            return
        threshold = self.cfg["wake"].get("threshold", 0.5)
        while True:
            score = max(self.oww.predict(self._chunk()).values())
            if self.debug and score > 0.05:
                log.info("wake score %.2f", score)
            if score >= threshold:
                log.info("wake (%.2f)", score)
                return

    def _loop(self):
        while True:
            self._wait_trigger()
            try:
                self._handle_command()
            except (_Interrupt, _MicLost):
                raise
            except Exception as e:  # คำสั่งพังไม่ควรทำให้ทั้งโปรแกรมหยุด
                log.exception("ทำคำสั่งไม่สำเร็จ")
                audio.play(self.sounds, "error")
                commands.island(self.cfg, "/notify", {"title": "ทำคำสั่งไม่สำเร็จ", "body": str(e)[:80],
                                                      "icon": "❌", "color": "#FF3B30"})
            if self.oww:
                self.oww.reset()  # ล้าง buffer กัน trigger ซ้ำ
            audio.drain(self._q)

    def _listen_text(self):
        clip = audio.listen(self._chunk, self.vad, self.cfg)
        return "" if clip is None else asr.transcribe(self.model, clip, self.cfg, self.prompt)

    def _handle_command(self):
        cfg = self.cfg
        audio.play(self.sounds, "wake", fallback=None)
        commands.island(cfg, "/notify", self.listening_notice)

        t0 = time.perf_counter()
        text = self._listen_text()
        if not text:
            log.info("ไม่ได้ยินคำสั่ง")
            return
        cmd, groups, score = commands.match(text, cfg)
        log.info('"%s" (%.2fs) -> %s (%.2f)', text, time.perf_counter() - t0,
                 cmd["name"] if cmd else "ไม่ตรงคำสั่ง", score)

        if cmd is None:
            audio.play(self.sounds, "error", fallback=None)
            commands.island(cfg, "/notify", {"title": "ไม่เข้าใจคำสั่ง", "body": text,
                                             "icon": "❓", "color": "#FF9F0A"})
            return
        if cmd.get("confirm") and not self._confirmed(cmd):
            log.info("ยกเลิก %s (ไม่ได้ยืนยัน)", cmd["name"])
            commands.island(cfg, "/notify", {"title": "ยกเลิกแล้ว", "body": cmd["name"],
                                             "icon": "✋", "color": "#8E8E93", "duration": 3})
            return

        result = commands.run(cmd, groups, cfg, self.ctx)
        audio.play(self.sounds, "done", fallback=None)
        if cmd["action"]["type"] != "notify":
            body = text if len(text) <= 60 else text[:57] + "..."
            commands.island(cfg, "/notify", {"title": result, "body": body,
                                             "icon": "✅", "color": "#34C759", "duration": 4})

    def _confirmed(self, cmd):
        """ถามยืนยันคำสั่งอันตราย: ต้องพูด ยืนยัน/ตกลง/ใช่ ภายในเวลา listen.timeout"""
        audio.drain(self._q)
        audio.play(self.sounds, "wake", fallback=None)
        commands.island(self.cfg, "/notify", {"title": f"พูด \"ยืนยัน\" เพื่อ{cmd['name']}", "icon": "⚠️",
                                              "color": "#FF3B30", "duration": 5})
        reply = self._listen_text()
        log.info('ยืนยัน? "%s"', reply)
        r = commands.normalize(reply)
        if "ไม่" in r or "ยกเลิก" in r:  # "ไม่ใช่" มีคำว่า "ใช่" อยู่ข้างใน
            return False
        return any(w in r for w in CONFIRM_WORDS)
