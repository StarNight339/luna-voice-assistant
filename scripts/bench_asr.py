"""วัดผล Thonburian Whisper: ความแม่น (CER) และความเร็ว (RTF/latency)

ต้องมีโฟลเดอร์ไฟล์เสียง + refs.json ({"ไฟล์.wav": "ข้อความเฉลย", ...} path อิงโฟลเดอร์นั้นหรือโฟลเดอร์โปรเจกต์)

ใช้งาน:
    uv run python scripts/bench_asr.py                 # GPU, beam 5 บน samples/refs.json
    uv run python scripts/bench_asr.py my_clips        # ใช้ my_clips/refs.json
    uv run python scripts/bench_asr.py --beam 1        # greedy (เร็วกว่า)
    uv run python scripts/bench_asr.py --cpu           # CPU int8
    uv run python scripts/bench_asr.py --mic 3         # อัดคำสั่งสั้นจากไมค์ 3 ครั้ง (ครั้งละ -s วินาที)
"""
import argparse
import json
import sys
import time
from pathlib import Path

from luna.asr import DEFAULT_MODEL_DIR
from luna.paths import ROOT, resolve
from luna.text import edit_distance, normalize

sys.path.insert(0, str(Path(__file__).parent))
from test_asr import load, record  # noqa: E402


def transcribe(model, audio, beam):
    t0 = time.perf_counter()
    segments, info = model.transcribe(
        audio,
        language="th",
        task="transcribe",
        beam_size=beam,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    text = "".join(s.text for s in segments).strip()
    return text, time.perf_counter() - t0, info.duration


def bench_samples(model, beam, folder):
    refs_file = folder / "refs.json"
    if not refs_file.exists():
        sys.exit(f"ไม่พบ {refs_file}")
    refs = json.loads(refs_file.read_text(encoding="utf-8"))

    def audio_path(p):
        return str(folder / p if (folder / p).exists() else ROOT / p)

    transcribe(model, audio_path(next(iter(refs))), beam)  # warm-up ไม่นับเวลา

    total_err = total_chars = total_dt = total_dur = 0
    for path, ref in refs.items():
        hyp, dt, dur = transcribe(model, audio_path(path), beam)
        r, h = normalize(ref), normalize(hyp)
        err = edit_distance(r, h)
        total_err += err
        total_chars += len(r)
        total_dt += dt
        total_dur += dur
        print(f"\n[{path}] เสียง {dur:.1f}s  ถอด {dt:.2f}s  RTF {dt / dur:.3f}  CER {err / len(r):.1%}")
        print(f"  ref: {ref}")
        print(f"  hyp: {hyp}")

    print("\n" + "=" * 60)
    print(f"CER รวม: {total_err / total_chars:.1%}  ({total_err}/{total_chars} ตัวอักษร)")
    print(f"RTF รวม: {total_dt / total_dur:.3f}  latency เฉลี่ย {total_dt / len(refs):.2f}s/ไฟล์")
    print("หมายเหตุ: ตัวเลข/ภาษาอังกฤษที่เขียนต่างรูป (เช่น 40 กับ สี่สิบ) จะนับเป็นผิด ให้ดูข้อความดิบประกอบ")


def bench_mic(model, beam, n, seconds):
    import numpy as np

    transcribe(model, np.zeros(16000, dtype="float32"), beam)  # warm-up
    for i in range(n):
        input(f"\n[{i + 1}/{n}] กด Enter แล้วพูดคำสั่ง...")
        audio = record(seconds)
        text, dt, _ = transcribe(model, audio, beam)
        print(f"📝 {text or '(ไม่พบเสียงพูด)'}  ⏱️ {dt:.2f}s")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("folder", nargs="?", default="samples", help="โฟลเดอร์ที่มี refs.json")
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--beam", type=int, default=5)
    p.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    p.add_argument("--mic", type=int, default=0, help="จำนวนครั้งที่อัดจากไมค์ (0 = ใช้ไฟล์)")
    p.add_argument("-s", "--seconds", type=float, default=3)
    args = p.parse_args()

    model = load(args.model_dir, args.cpu)
    print(f"beam {args.beam}")
    if args.mic:
        bench_mic(model, args.beam, args.mic, args.seconds)
    else:
        bench_samples(model, args.beam, resolve(args.folder))


if __name__ == "__main__":
    main()
