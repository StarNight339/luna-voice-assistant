"""ไมค์ / เสียงตอบรับ / ตรวจว่าพูดจบ"""
import logging
import queue

import numpy as np

from .paths import resolve

log = logging.getLogger(__name__)

SR = 16000
CHUNK = 1280  # 80ms ตามที่ openWakeWord ต้องการ
PLAY_SR = 44100


def load_sounds(cfg):
    from faster_whisper import decode_audio

    sounds = {}
    for name, path in (cfg.get("sounds") or {}).items():
        p = resolve(path)
        if p.exists():
            sounds[name] = decode_audio(str(p), sampling_rate=PLAY_SR)
        else:
            log.info("ไม่พบไฟล์เสียง %s: %s (ข้าม)", name, path)
    return sounds


def play(sounds, name, fallback="done"):
    import sounddevice as sd

    data = sounds.get(name, sounds.get(fallback))
    if data is not None:
        try:
            sd.play(data, PLAY_SR)  # ไม่ block
        except Exception as e:  # noqa: BLE001 — ลำโพงหลุดไม่ควรทำให้ bot ล้ม
            log.warning("เล่นเสียง %s ไม่ได้: %s", name, e)


def drain(q):
    while True:
        try:
            q.get_nowait()
        except queue.Empty:
            return


def listen(get_chunk, vad, cfg):
    """เก็บเสียงคำสั่งจนพูดจบ คืน float32 array หรือ None ถ้าไม่มีใครพูด
    get_chunk() คืน int16 chunk ถัดไป (block จนกว่าจะมี)"""
    opts = cfg.get("listen", {})
    timeout, max_len = opts.get("timeout", 4), opts.get("max", 10)
    th = opts.get("vad_threshold", 0.5)
    win_len = int(opts.get("silence", 0.8) * SR) // 512 * 512  # Silero รับทีละ 512 samples

    chunks, started = [], False
    while True:
        chunks.append(get_chunk())
        audio = np.concatenate(chunks).astype(np.float32) / 32768
        elapsed = len(audio) / SR
        win = audio[-win_len:]
        win = win[len(win) % 512:]
        speech = len(win) and vad(win).max() >= th

        if not started:
            if speech:
                started = True
            elif elapsed >= timeout:
                return None
        elif not speech and len(win) == win_len:
            return audio
        if elapsed >= max_len:
            return audio if started else None
