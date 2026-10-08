"""ทดสอบถอดเสียงด้วย Thonburian Whisper (distill large-v3) ทีละไฟล์/ทีละครั้ง

ใช้งาน:
    uv run python scripts/test_asr.py              # อัดเสียงจากไมค์ 5 วินาที แล้วถอดความ
    uv run python scripts/test_asr.py -s 8         # อัด 8 วินาที
    uv run python scripts/test_asr.py file.wav     # ถอดความจากไฟล์ (wav/mp3/m4a ฯลฯ)
    uv run python scripts/test_asr.py --cpu        # รันบน CPU (int8) เพื่อเทียบความเร็ว
"""
import argparse
import time

from luna.asr import DEFAULT_MODEL_DIR, add_cuda_dlls
from luna.paths import resolve


def record(seconds, sr=16000):
    import sounddevice as sd

    print(f"🎙️  พูดได้เลย ({seconds} วินาที)...")
    audio = sd.rec(int(seconds * sr), samplerate=sr, channels=1, dtype="float32")
    sd.wait()
    print("⏹️  อัดเสร็จ")
    return audio[:, 0]


def load(model_dir, cpu):
    if not cpu:
        add_cuda_dlls()
    from faster_whisper import WhisperModel

    device, compute = ("cpu", "int8") if cpu else ("cuda", "float16")
    t0 = time.perf_counter()
    model = WhisperModel(str(resolve(model_dir)), device=device, compute_type=compute)
    print(f"โหลดโมเดล ({device}/{compute}): {time.perf_counter() - t0:.1f}s")
    return model


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file", nargs="?", help="ไฟล์เสียง (ไม่ใส่ = อัดจากไมค์)")
    p.add_argument("-s", "--seconds", type=float, default=5)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    p.add_argument("--prompt", default=None, help="initial_prompt เช่น คำศัพท์/ชื่อเฉพาะ")
    args = p.parse_args()

    model = load(args.model_dir, args.cpu)
    audio = args.file if args.file else record(args.seconds)

    t0 = time.perf_counter()
    segments, info = model.transcribe(
        audio,
        language="th",
        task="transcribe",
        beam_size=5,
        vad_filter=True,  # Silero VAD ในตัว กัน hallucinate ช่วงเงียบ
        condition_on_previous_text=False,
        initial_prompt=args.prompt,
    )
    text = "".join(s.text for s in segments).strip()  # segments เป็น generator ต้องวนก่อนจับเวลา
    dt = time.perf_counter() - t0

    print("\n📝 ผลลัพธ์:", text or "(ไม่พบเสียงพูด)")
    print(f"⏱️  ถอดความ {dt:.2f}s สำหรับเสียง {info.duration:.1f}s "
          f"(หลังตัดเงียบ {info.duration_after_vad:.1f}s) → RTF {dt / max(info.duration, 1e-6):.2f}")


if __name__ == "__main__":
    main()
