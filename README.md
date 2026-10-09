# Luna 🌙 — สั่งงานคอมด้วยเสียงภาษาไทย

เรียก **"เฮ้ ลูน่า"** แล้วพูดคำสั่งได้เลย เช่น "เปิด Spotify", "ค้นหา ราคาทองวันนี้", "เตือนให้กินข้าวในอีก 20 นาที"
ทำงานในเครื่องทั้งหมด (ไม่ส่งเสียงขึ้น cloud) และไม่ใช้ LLM

- **Wake word**: [openWakeWord](https://github.com/dscripka/openWakeWord) โมเดล `hey luna` ที่เทรนเอง (`models/wakeword/hey_luna.onnx`)
- **ถอดเสียง**: [Thonburian Whisper distill large-v3](https://huggingface.co/biodatlab/distill-whisper-th-large-v3) ผ่าน [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
  — CER ~2.7%, ~0.6 วินาที/คำสั่งบน GPU
- **แสดงผล**: ไอคอนใน system tray และ (ถ้ามี) [Dynamic Island for Windows](https://github.com/StarNight339/Dynamic-Island-for-Windows)

## ความต้องการ

- Windows 10/11
- การ์ดจอ NVIDIA (แนะนำ, ใช้ VRAM ~2 GB) — ไม่มีก็รันบน CPU ได้แต่ถอดเสียงช้า (~5–7 วินาที/คำสั่ง)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) และไมโครโฟน

## ติดตั้ง

```powershell
git clone https://github.com/StarNight339/luna-voice-assistant.git
cd luna-voice-assistant
uv sync --extra cuda                       # ไม่มีการ์ด NVIDIA ใช้: uv sync
uv run python scripts/download_model.py    # ครั้งเดียว: แปลงโมเดล Whisper (~3 GB ดาวน์โหลด, ได้ไฟล์ ~1.6 GB)
uv run luna                                # เปิด Luna (ไอคอนขึ้นใน system tray)
```

ครั้งแรกที่รัน Luna จะสร้าง `config.yaml` จาก `config.example.yaml` ให้แก้ได้ตามต้องการ
และสร้างทางลัด **Luna** ใน Start Menu กับ Desktop ให้ ครั้งต่อไปดับเบิลคลิกทางลัดได้เลย ไม่ต้องเปิด terminal

## ใช้งาน

พูด **"เฮ้ ลูน่า"** รอเสียง/แจ้งเตือน "ฟังอยู่..." แล้วพูดคำสั่งภายใน 4 วินาที (จะพูดต่อกันในประโยคเดียวก็ได้)

| กลุ่ม | ตัวอย่าง |
|---|---|
| เปิดแอป | "เปิด Chrome", "เปิด Zen", "เปิด Discord", "เปิด Spotify", "เปิดยูทูป", "เปิดโน้ตแพด" |
| ค้นหา | "ค้นหา ราคาทองวันนี้", "หาในยูทูป สอนทำกับข้าว", "หาเพลง Bodyslam" |
| พิมพ์ / โน้ต | "พิมพ์ว่า สวัสดีครับ" (พิมพ์ลงหน้าต่างที่เปิดอยู่), "จดโน้ต ซื้อนม", "เปิดโน้ต", "ขึ้นบรรทัดใหม่" |
| เพลง / เสียง | "เพิ่มเสียง", "ลดเสียง", "ตั้งเสียง 50", "ปิดเสียง", "หยุดเพลง", "เพลงถัดไป" |
| เวลา | "ตอนนี้กี่โมง", "วันนี้วันอะไร", "ตั้งเวลา 5 นาที", "เตือนให้ดื่มน้ำในอีกครึ่งชั่วโมง" |
| หน้าต่าง | "ย่อทุกหน้าต่าง", "ปิดหน้าต่างนี้", "สลับหน้าต่าง", "แคปหน้าจอ" |
| ระบบ | "แบตเหลือเท่าไหร่", "ล็อกเครื่อง", "ปิดเครื่อง" / "รีสตาร์ท" / "พักเครื่อง" (ต้องพูด **"ยืนยัน"** อีกครั้ง) |
| อื่นๆ | "ยกเลิก" (กรณีเรียกโดยไม่ตั้งใจ) |

### เปิด/ปิด Luna

ทางลัด **Luna** บน Desktop / Start Menu (หรือกดปุ่ม Start แล้วพิมพ์ "Luna"):

- **ยังไม่เปิด** → ดับเบิลคลิก = เปิด Luna
- **เปิดอยู่แล้ว** → ดับเบิลคลิก = หยุดฟังชั่วคราว / ฟังต่อ (มีแจ้งเตือนบอกทุกครั้ง)
- อยากได้คีย์ลัด: คลิกขวาทางลัดใน Start Menu → Open file location → คลิกขวา Luna → Properties → **Shortcut key** เช่น `Ctrl+Alt+L`
  แล้วกดคีย์นั้นเพื่อเปิด/หยุดฟัง/ฟังต่อได้จากทุกที่

ไอคอน 🌙 ใน system tray (มุมขวาล่าง):

- **คลิกซ้าย** = หยุดฟังชั่วคราว / ฟังต่อ (ตอนหยุด Luna ปิดไมค์จริง ไอคอนเป็นสีเทา)
- **คลิกขวา** = เมนู: เปิดไฟล์ตั้งค่า · โหลดตั้งค่าใหม่ · เปิดโฟลเดอร์ log · ☑ เปิดตอนเข้า Windows · ☑ ทางลัดใน Start Menu / Desktop · ออก

หรือใช้คำสั่ง:

```powershell
uv run luna install-startup      # เปิด Luna อัตโนมัติตอนเข้า Windows (ไม่มีหน้าต่าง console)
uv run luna uninstall-startup
uv run luna install-shortcut     # สร้างทางลัดใน Start Menu / Desktop ใหม่ (ถ้าลบไปแล้ว)
uv run luna uninstall-shortcut
uv run luna --console            # รันใน console เห็น log สด
uv run luna --console --no-wake  # กด Enter แทนการเรียกชื่อ (ทดสอบคำสั่ง)
uv run luna --console --debug    # ดูคะแนน wake word (ไว้ปรับ threshold)
```

log อยู่ที่ `%LOCALAPPDATA%\Luna\luna.log`

## ตั้งค่า (`config.yaml`)

แก้แล้วกด **"โหลดตั้งค่าใหม่"** จากเมนู tray ได้ทันที ดูคำอธิบายทุกช่องในไฟล์ ตัวอย่างที่ใช้บ่อย:

```yaml
wake:
  threshold: 0.5        # เรียกแล้วไม่ค่อยติด → ลดเป็น 0.3–0.4, ตื่นเองบ่อย → เพิ่มเป็น 0.6–0.7
browser: 'C:\Program Files\Zen Browser\zen.exe'   # browser สำหรับผลค้นหา
sounds:                 # ใส่ไฟล์เสียงตอบรับเองใน sounds/ (ไม่มี = เงียบ)
  wake: sounds/wake.wav
```

**เพิ่มคำสั่งเอง** — ต่อท้าย `commands:`

```yaml
  - name: เปิด VS Code
    phrases: [เปิดวีเอสโค้ด, เปิด vs code, เปิดโค้ด]   # Whisper อาจถอดชื่ออังกฤษเป็นไทยได้หลายแบบ ใส่ไว้หลายๆ แบบ
    action: {type: open, target: code}

  - name: แปลภาษา
    pattern: '^แปล(?:ว่า)?\s*(.+)'                       # ข้อความอิสระต่อท้าย -> {1}
    action: {type: web, url: "https://translate.google.com/?sl=th&tl=en&text={1:url}"}
```

ประเภท action: `open` `web` `shell` `key` `hotkey` `type` `note` `lock` `power` `status` `volume` `timer` `reminder` `notify` `time` `cancel`
— รายละเอียดอยู่ในหัว `config.example.yaml`

## เทรน wake word ใหม่

ใช้ `training/train_hey_luna.ipynb` บน Google Colab (GPU T4 ฟรี) — notebook สร้างเสียงสังเคราะห์ด้วย Piper TTS แล้วเทรน openWakeWord
(แยก Python 3.10 ไว้ในตัว เพราะ Colab เป็น 3.13 แต่ piper-phonemize รองรับถึง 3.11) ได้ไฟล์ `.onnx` มาใส่ `models/wakeword/`
แล้วแก้ `wake.model` ใน `config.yaml`

## แก้ปัญหา

| อาการ | วิธีแก้ |
|---|---|
| ไอคอนแดง "ไม่พบไมโครโฟน" | เช็กไมค์ใน Settings → Privacy → Microphone; Luna จะลองเชื่อมต่อใหม่ทุก 3 วินาทีเอง |
| ถอดเสียงช้ามาก | log มี "ใช้ GPU ไม่ได้" → ติดตั้งด้วย `uv sync --extra cuda` และอัปเดตไดรเวอร์ NVIDIA |
| ตื่นเองบ่อย / เรียกไม่ติด | ปรับ `wake.threshold` (ดูคะแนนด้วย `luna --console --debug`) |
| คำสั่งไม่ตรง | ดูใน log ว่า Whisper ถอดเป็นอะไร แล้วเพิ่มคำนั้นใน `phrases` |
| "พิมพ์ว่า" ไม่พิมพ์ | คลิกหน้าต่างที่จะพิมพ์ก่อนเรียก Luna; แอปที่รันแบบ admin รับการพิมพ์จาก Luna ไม่ได้ |

## พัฒนา

```powershell
uv sync --extra cuda   # dev dependencies (pytest) มาด้วยอัตโนมัติ
uv run pytest
uv run python scripts/bench_asr.py samples   # วัด CER/ความเร็ว (ต้องมี samples/refs.json)
uv run python scripts/test_asr.py            # อัดไมค์แล้วถอดความ
```

```
luna/
  __main__.py   CLI + tray/console, single instance, logging
  bot.py        วงจรหลัก: wake word -> ฟัง -> ถอดเสียง -> จับคู่ -> ทำ action (pause/resume/reload)
  commands.py   โหลด config, จับคู่คำสั่ง (phrases fuzzy / pattern regex), action ทั้งหมด
  asr.py        โหลด Whisper (GPU -> CPU fallback), initial_prompt
  audio.py      ไมค์, ตรวจพูดจบด้วย Silero VAD, เสียงตอบรับ
  winctl.py     Win32 ผ่าน ctypes: คีย์/คีย์ผสม, พิมพ์ข้อความ, สถานะเครื่อง, ระดับเสียง
  tray.py       ไอคอน system tray + รับสัญญาณสลับฟังจากทางลัด
  shortcut.py   ทางลัดใน Start Menu / Desktop
  autostart.py  เปิดตอนเข้า Windows (HKCU Run)
scripts/        download_model.py, bench_asr.py, test_asr.py
training/       notebook เทรน wake word
```

## เครดิต / License

- โค้ดใน repo นี้: [MIT](LICENSE)
- Thonburian Whisper (biodatlab) — MIT · openWakeWord — Apache-2.0 (โมเดลสำเร็จรูปของ openWakeWord เป็น CC BY-NC-SA 4.0)
  · faster-whisper — MIT · Silero VAD — MIT
