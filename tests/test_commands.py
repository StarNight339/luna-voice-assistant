import pytest

from luna import commands
from luna.paths import CONFIG_EXAMPLE


@pytest.fixture(scope="module")
def cfg():
    return commands.load_config(CONFIG_EXAMPLE)


# (ข้อความที่ Whisper ถอดได้, ชื่อคำสั่งที่คาด, groups ที่คาด หรือ None = ไม่เช็ก)
CASES = [
    # ค้นหา
    ("ค้นหา ราคาทองวันนี้", "ค้นหา", ("ราคาทองวันนี้",)),
    ("Hey Luna, search how to cook rice", "ค้นหา", ("how to cook rice",)),
    ("ลูน่า กูเกิ้ล สภาพอากาศ", "ค้นหา", ("สภาพอากาศ",)),
    ("หาในยูทูป สอนทำกับข้าว", "ค้นหาใน YouTube", ("สอนทำกับข้าว",)),
    ("ยูทูบหา lofi music", "ค้นหาใน YouTube", ("lofi music",)),
    ("เปิดยูทูป", "เปิด YouTube", None),
    ("เปิดยูทูปหน่อย", "เปิด YouTube", None),
    ("หาเพลง Bodyslam", "หาเพลงใน Spotify", ("Bodyslam",)),
    # พิมพ์ / โน้ต
    ("พิมพ์ว่า สวัสดีครับ", "พิมพ์ตามเสียง", ("สวัสดีครับ",)),
    ("พิมว่า Hello World", "พิมพ์ตามเสียง", ("Hello World",)),
    ("จดโน้ต ซื้อนมก่อนกลับบ้าน", "จดโน้ต", ("ซื้อนมก่อนกลับบ้าน",)),
    ("บันทึกว่า ประชุมพรุ่งนี้บ่ายสอง", "จดโน้ต", ("ประชุมพรุ่งนี้บ่ายสอง",)),
    ("เปิดโน้ต", "เปิดโน้ต", None),
    ("เปิดโน้ตแพด", "เปิด Notepad", None),
    ("ขึ้นบรรทัดใหม่", "ขึ้นบรรทัดใหม่", None),
    # หน้าต่าง / ระบบ
    ("ย่อทุกหน้าต่าง", "ย่อทุกหน้าต่าง", None),
    ("ปิดหน้าต่างนี้", "ปิดหน้าต่าง", None),
    ("สลับหน้าต่าง", "สลับหน้าต่าง", None),
    ("แคปหน้าจอ", "แคปหน้าจอ", None),
    ("แบตเหลือเท่าไหร่", "สถานะเครื่อง", None),
    ("ปิดเครื่อง", "ปิดเครื่อง", None),
    ("รีสตาร์ทเครื่อง", "รีสตาร์ทเครื่อง", None),
    ("พักเครื่อง", "พักเครื่อง", None),
    # เตือนความจำ / ระดับเสียง
    ("เตือนให้กินข้าวในอีก 20 นาที", "เตือนความจำ", ("กินข้าว", "20 นาที")),
    ("เตือนให้ดื่มน้ำอีกห้านาทีนะ", "เตือนความจำ", ("ดื่มน้ำ", "ห้านาที")),
    ("ในอีกครึ่งชั่วโมงเตือนให้โทรหาแม่", "เตือนความจำ", ("ครึ่งชั่วโมง", "โทรหาแม่")),
    ("อีก 1 ชั่วโมงเตือนว่าเอาผ้าออก", "เตือนความจำ", ("1 ชั่วโมง", "เอาผ้าออก")),
    ("ตั้งเสียง 50", "ตั้งระดับเสียง", ("50",)),
    ("ปรับเสียงเป็น 30 เปอร์เซ็นต์", "ตั้งระดับเสียง", ("30",)),
    ("เสียงยี่สิบ", "ตั้งระดับเสียง", ("20",)),
    ("เสียงดังขึ้น", "เพิ่มเสียง", None),
    ("ปรับเสียงดังขึ้น", "เพิ่มเสียง", None),
    ("ปิดเสียง", "ปิดเสียง", None),
    ("ยกเลิก", "ยกเลิก", None),
    ("ยกเลิกเวลา", "ยกเลิกเวลา", None),
    # เปิดแอป / เวลา / มีเดีย
    ("ตั้งเวลา 5 นาที", "ตั้งเวลา", ("5 นาที",)),
    ("ตั้งเวลาห้านาที", "ตั้งเวลา", ("ห้านาที",)),
    ("ตั้งเวลา 1 ชั่วโมงครึ่ง", "ตั้งเวลา", ("1 ชั่วโมงครึ่ง",)),
    ("เปิดโปรแกรม เซนต์", "เปิด Zen", None),
    ("เปิดดิสคอร์ดหน่อยครับ", "เปิด Discord", None),
    ("ตอนนี้เวลาเท่าไหร่", "บอกเวลา", None),
    ("What is time", "บอกเวลา", None),
    ("วันนี้วันอะไร", "บอกวันที่", None),
    ("เพลงถัดไป", "เพลงถัดไป", None),
    ("ล็อกเครื่อง", "ล็อกเครื่อง", None),
    # ไม่ใช่คำสั่ง
    ("วันนี้อากาศดีจัง", None, None),
    ("หาวมากเลย", None, None),
    ("ไปกินข้าวกัน", None, None),
    ("", None, None),
]


@pytest.mark.parametrize("text,want,want_groups", CASES)
def test_match(cfg, text, want, want_groups):
    cmd, groups, _ = commands.match(text, cfg)
    assert (cmd["name"] if cmd else None) == want
    if want_groups is not None:
        assert groups == want_groups


@pytest.mark.parametrize("text,seconds", [
    ("20 นาที", 1200), ("ห้านาที", 300), ("1 ชั่วโมง", 3600), ("ครึ่งชั่วโมง", 1800),
    ("1 ชั่วโมงครึ่ง", 5400), ("1 ชั่วโมง 30 นาที", 5400), ("ยี่สิบห้านาที", 1500),
    ("1.5 ชั่วโมง", 5400), ("หลายนาที", None), ("", None),
])
def test_parse_duration(text, seconds):
    assert commands.parse_duration(text) == seconds


@pytest.mark.parametrize("text,n", [("5", 5), ("ห้า", 5), ("สิบ", 10), ("ยี่สิบห้า", 25), ("สิบเอ็ด", 11),
                                    ("ร้อย", 100), ("แมว", None)])
def test_thai_number(text, n):
    assert commands.thai_number(text) == n


def test_format_duration():
    assert commands.format_duration(5400) == "1 ชั่วโมง 30 นาที"
    assert commands.format_duration(20) == "ไม่ถึงนาที"


def test_web_url_is_encoded(cfg, monkeypatch):
    opened = []
    monkeypatch.setattr(commands, "start_process", lambda *a: opened.append(a))
    cmd, groups, _ = commands.match("ค้นหา how to cook ข้าวผัด & more", cfg)
    commands.run(cmd, groups, cfg)
    url = opened[0][-1]
    assert url.startswith("https://www.google.com/search?q=how+to+cook+")
    assert "%26+more" in url and " " not in url


def test_note_appends_line(cfg, tmp_path):
    cfg = {**cfg, "notes_file": str(tmp_path / "notes.md")}
    cmd, groups, _ = commands.match("จดโน้ต ซื้อนม", cfg)
    assert commands.run(cmd, groups, cfg) == "จดโน้ตแล้ว"
    assert (tmp_path / "notes.md").read_text(encoding="utf-8").rstrip().endswith("ซื้อนม")


def test_reminder_fires(cfg, monkeypatch):
    sent, played = [], []
    monkeypatch.setattr(commands, "island", lambda _cfg, endpoint, payload: sent.append((endpoint, payload)))

    class InstantTimer:
        def __init__(self, seconds, fn):
            self.seconds, self.fn, self.daemon = seconds, fn, False

        def start(self):
            self.fn()

    monkeypatch.setattr(commands.threading, "Timer", InstantTimer)
    cmd, groups, _ = commands.match("เตือนให้ดื่มน้ำในอีก 5 นาที", cfg)
    result = commands.run(cmd, groups, cfg, {"play": played.append})
    assert result == 'จะเตือน "ดื่มน้ำ" ในอีก 5 นาที'
    assert sent == [("/notify", {"title": "เตือนความจำ", "body": "ดื่มน้ำ", "icon": "⏰",
                                 "color": "#FF9F0A", "duration": 15})]
    assert played == ["reminder"]


def test_bad_duration_raises(cfg):
    cmd = {"name": "ตั้งเวลา", "action": {"type": "timer", "duration": "{1}"}}
    with pytest.raises(ValueError):
        commands.run(cmd, ("หลายนาที",), cfg)


def test_island_down_is_silent():
    commands.island({"island": "http://127.0.0.1:9"}, "/notify", {"title": "x"})  # ไม่มี server = ไม่ error
