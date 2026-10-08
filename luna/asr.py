"""โหลด Thonburian Whisper (faster-whisper / CTranslate2) และถอดเสียงคำสั่ง"""
import logging
import os
import sys
from pathlib import Path

import numpy as np

from .paths import resolve

log = logging.getLogger(__name__)

DEFAULT_MODEL_DIR = "models/whisper/distill-th-large-v3-ct2"


def add_cuda_dlls():
    """ให้ ctranslate2 หา cuBLAS / cuDNN ที่ติดตั้งผ่าน pip (extra `cuda`) เจอบน Windows"""
    nvidia = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    for sub in ("cublas", "cudnn", "cuda_nvrtc"):
        d = nvidia / sub / "bin"
        if d.is_dir():
            os.add_dll_directory(str(d))
            os.environ["PATH"] = str(d) + os.pathsep + os.environ["PATH"]


def model_dir(cfg):
    return resolve(cfg.get("asr", {}).get("model_dir", DEFAULT_MODEL_DIR))


def load_model(cfg, cpu=False):
    """คืน (model, device) — ไม่มี GPU/CUDA ใช้ไม่ได้ จะ fallback เป็น CPU int8 (ช้ากว่ามาก)"""
    from faster_whisper import WhisperModel

    path = model_dir(cfg)
    if not (path / "model.bin").exists():
        raise FileNotFoundError(f"ไม่พบโมเดล Whisper ที่ {path} — รัน: uv run python scripts/download_model.py")
    if not cpu:
        add_cuda_dlls()
        try:
            model = WhisperModel(str(path), device="cuda", compute_type="float16")
            _warm_up(model)  # ครั้งแรกบน GPU ช้า (โหลด cuDNN) และถ้า CUDA มีปัญหาจะ error ตรงนี้
            return model, "cuda"
        except Exception as e:  # noqa: BLE001 — ctranslate2 โยน RuntimeError/OSError หลายแบบ
            log.warning("ใช้ GPU ไม่ได้ (%s) — เปลี่ยนเป็น CPU", e)
    model = WhisperModel(str(path), device="cpu", compute_type="int8")
    _warm_up(model)
    return model, "cpu"


def _warm_up(model):
    list(model.transcribe(np.zeros(16000, dtype=np.float32), language="th", beam_size=1)[0])


def build_prompt(model, cfg):
    """initial_prompt: คำหลักของ pattern ก่อน แล้วตามด้วย phrase แรกของแต่ละคำสั่ง จนเต็มงบ token
    (Whisper รับ prompt ได้ ~223 token ส่วนเกินถูกตัดทิ้งเงียบๆ และภาษาไทยกิน token เยอะ)"""
    asr = cfg.get("asr", {})
    if not asr.get("use_prompt", True):
        return None
    words = list(dict.fromkeys(asr.get("prompt_words", []) +
                               [c["phrases"][0] for c in cfg["commands"] if c.get("phrases")]))
    kept = []
    for w in words:
        if len(model.hf_tokenizer.encode(" " + " ".join(kept + [w])).ids) > asr.get("prompt_tokens", 200):
            break
        kept.append(w)
    if len(kept) < len(words):
        log.info("initial_prompt ใช้ %d/%d คำ (เต็มงบ token)", len(kept), len(words))
    return " ".join(kept)


def transcribe(model, audio, cfg, prompt=None):
    segments, _ = model.transcribe(
        audio, language="th", beam_size=cfg.get("asr", {}).get("beam", 1), vad_filter=True,
        condition_on_previous_text=False, initial_prompt=prompt,
    )
    return "".join(s.text for s in segments).strip()
