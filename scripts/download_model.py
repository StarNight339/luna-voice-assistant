"""เตรียมโมเดลที่ Luna ต้องใช้ (รันครั้งเดียวหลัง `uv sync`)

1. Thonburian Whisper distill large-v3 (biodatlab, MIT) แปลงเป็น CTranslate2 float16 สำหรับ faster-whisper
   ดาวน์โหลดต้นฉบับ ~3 GB แล้วได้ไฟล์ ~1.6 GB ที่ models/whisper/ — ตัวแปลง (transformers + torch) ติดตั้งชั่วคราวผ่าน uv
   ไม่ปนกับ environment ของ Luna
2. feature models ของ openWakeWord (melspectrogram / embedding)

ใช้งาน:
    uv run python scripts/download_model.py
    uv run python scripts/download_model.py --force    # แปลงใหม่ทับของเดิม
"""
import argparse
import shutil
import subprocess
import sys

from luna.asr import DEFAULT_MODEL_DIR
from luna.paths import resolve

SOURCE = "biodatlab/distill-whisper-th-large-v3"
CONVERTER_DEPS = ["ctranslate2>=4.4", "transformers[torch]>=4.40,<4.47", "huggingface_hub<0.30"]


def convert_whisper(force, out=None):
    out = resolve(out or DEFAULT_MODEL_DIR)
    if (out / "model.bin").exists() and not force:
        print(f"✓ มีโมเดล Whisper แล้ว: {out}")
        return
    uv = shutil.which("uv")
    if not uv:
        sys.exit("ต้องมี uv (https://docs.astral.sh/uv/) เพื่อติดตั้งตัวแปลงโมเดลชั่วคราว")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [uv, "run", "--no-project", "--python", "3.12"]
    for dep in CONVERTER_DEPS:
        cmd += ["--with", dep]
    cmd += ["ct2-transformers-converter", "--model", SOURCE, "--output_dir", str(out),
            "--copy_files", "tokenizer.json", "preprocessor_config.json", "--quantization", "float16"]
    if force:
        cmd.append("--force")
    print(f"⏳ แปลง {SOURCE} -> {out} (ดาวน์โหลด ~3 GB ครั้งแรก อาจใช้เวลาหลายนาที)")
    subprocess.run(cmd, check=True)
    print(f"✓ โมเดล Whisper พร้อมแล้ว: {out}")


def download_wakeword_features():
    import openwakeword.utils

    openwakeword.utils.download_models()
    print("✓ feature models ของ openWakeWord พร้อมแล้ว")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="แปลงโมเดล Whisper ใหม่แม้มีอยู่แล้ว")
    p.add_argument("--output", help=f"โฟลเดอร์ปลายทาง (ค่าเริ่มต้น {DEFAULT_MODEL_DIR})")
    args = p.parse_args()
    download_wakeword_features()
    convert_whisper(args.force, args.output)


if __name__ == "__main__":
    main()
