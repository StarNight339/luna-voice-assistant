"""โหลด config, จับคู่ข้อความกับคำสั่ง และรัน action ของ Luna bot"""
import ctypes
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from difflib import SequenceMatcher

import yaml

from . import winctl
from .paths import resolve
from .text import normalize

log = logging.getLogger(__name__)

WAKE_PREFIX = re.compile(r"^(เฮ้|เฮ|hey|hi)?(ลูน่า|ลูนา|ลูน้า|luna)")
WAKE_PREFIX_RAW = re.compile(r"^(?:(?:เฮ้|เฮ|hey|hi)[\s,]*)?(?:ลูน่า|ลูนา|ลูน้า|luna)[\s,]*", re.IGNORECASE)
# คำเสริมที่ไม่เปลี่ยนความหมายคำสั่ง ("เปิดโปรแกรมซูมหน่อยครับ" -> "เปิดซูม")
FILLERS = re.compile(r"โปรแกรม|แอปพลิเคชัน|แอป|แอพ|หน่อย|ครับ|ค่ะ|คะ|นะ")

THAI_DIGITS = {"ศูนย์": 0, "หนึ่ง": 1, "เอ็ด": 1, "สอง": 2, "ยี่": 2, "สาม": 3, "สี่": 4,
               "ห้า": 5, "หก": 6, "เจ็ด": 7, "แปด": 8, "เก้า": 9}

THAI_DAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
THAI_MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
               "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]

POWER = {
    "shutdown": ["shutdown", "/s", "/t", "0"],
    "restart": ["shutdown", "/r", "/t", "0"],
    "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],  # จะ hibernate ถ้าเปิด hibernation ไว้
}


def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for cmd in cfg["commands"]:
        cmd["_phrases"] = [FILLERS.sub("", normalize(p)) for p in cmd.get("phrases", [])]
        if "pattern" in cmd:
            cmd["_pattern"] = re.compile(cmd["pattern"], re.IGNORECASE)
    return cfg


def thai_number(s):
    """'5' / 'ห้า' / 'ยี่สิบห้า' -> 5 / 5 / 25 (รองรับถึง 99), แปลงไม่ได้ = None"""
    s = s.replace(" ", "")
    if s.isdigit():
        return int(s)
    if s in ("ร้อย", "หนึ่งร้อย"):
        return 100
    if "สิบ" in s:
        tens, ones = s.split("สิบ", 1)
        t = THAI_DIGITS.get(tens, None) if tens else 1
        o = THAI_DIGITS.get(ones, None) if ones else 0
        return None if t is None or o is None else t * 10 + o
    return THAI_DIGITS.get(s)


def to_number(s):
    """thai_number + ทศนิยม ('1.5')"""
    n = thai_number(s)
    if n is not None:
        return n
    try:
        return float(s.replace(" ", ""))
    except ValueError:
        return None


def parse_duration(s):
    """'20 นาที' / 'ห้านาที' / '1 ชั่วโมง 30 นาที' / 'ครึ่งชั่วโมง' / 'ชั่วโมงครึ่ง' -> วินาที, แปลงไม่ได้ = None"""
    s = re.sub(r"\s+", "", s)
    total, pos = 0.0, 0
    for m in re.finditer(r"ชั่วโมง|นาที", s):
        num = s[pos:m.start()]
        n = 1 if num == "" else 0.5 if num == "ครึ่ง" else to_number(num)
        if n is None:
            return None
        unit = 3600 if m[0] == "ชั่วโมง" else 60
        total += n * unit
        pos = m.end()
        if s.startswith("ครึ่ง", pos):  # "ชั่วโมงครึ่ง"
            total += unit / 2
            pos += len("ครึ่ง")
    return total or None


def format_duration(seconds):
    h, m = divmod(round(seconds / 60), 60)
    return " ".join(p for p in (f"{h} ชั่วโมง" if h else "", f"{m} นาที" if m else "") if p) or "ไม่ถึงนาที"


def clean(text):
    """ข้อความสำหรับ pattern: คงช่องว่าง/ตัวพิมพ์ไว้ (ข้อความอิสระอย่างคำค้นต้องการ) ตัดแค่ชื่อเรียกและวรรคตอนหัวท้าย"""
    t = unicodedata.normalize("NFC", text).strip()
    t = WAKE_PREFIX_RAW.sub("", t)
    return re.sub(r"\s+", " ", t).strip(" .,!?…\"'")


def match(text, cfg):
    """คืน (คำสั่ง, กลุ่มที่ regex จับได้, คะแนน) หรือ (None, (), คะแนนสูงสุด)"""
    t = FILLERS.sub("", WAKE_PREFIX.sub("", normalize(text)))
    raw = clean(text)
    if not t:
        return None, (), 0.0

    best, best_score = None, 0.0
    for cmd in cfg["commands"]:
        if "_pattern" in cmd:
            m = cmd["_pattern"].search(raw)
            if m:
                groups = tuple((g or "").strip() for g in m.groups())
                groups = tuple(g if thai_number(g) is None else str(thai_number(g)) for g in groups)
                return cmd, groups, 1.0
            continue
        for p in cmd["_phrases"]:
            score = SequenceMatcher(None, t, p).ratio()
            if p in t:  # phrase อยู่ในประโยค ให้ phrase ที่ยาวกว่า (เจาะจงกว่า) ชนะ
                score = max(score, 0.9 + 0.1 * len(p) / len(t))
            if score > best_score:
                best, best_score = cmd, score

    if best_score >= cfg.get("match_threshold", 0.75):
        return best, (), best_score
    return None, (), best_score


def island(cfg, endpoint, payload):
    url = cfg.get("island")
    if not url:
        return
    req = urllib.request.Request(
        url.rstrip("/") + endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=1).close()
    except OSError:
        pass  # island ไม่ได้เปิดอยู่


def start_process(target, *args):
    target = os.path.expandvars(target)  # รองรับ %APPDATA% ฯลฯ
    if "://" not in target and resolve(target).exists():  # path สัมพัทธ์ เช่น notes.md อิงโฟลเดอร์โปรเจกต์
        target = str(resolve(target))
    cmd = f"Start-Process '{target.replace(chr(39), chr(39) * 2)}'"
    if args:
        cmd += " -ArgumentList " + ",".join(f"'{a.replace(chr(39), chr(39) * 2)}'" for a in args)
    subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd], creationflags=subprocess.CREATE_NO_WINDOW)


def run(cmd, groups, cfg, ctx=None):
    """รัน action ของคำสั่ง คืนข้อความสรุปผล; ctx = {"play": fn(ชื่อเสียง)} สำหรับ action ที่ทำงานภายหลัง"""
    def fill(v):
        # {1} = ข้อความดิบ, {1:url} = encode สำหรับใส่ใน URL (ไม่ใช้ str.format เพราะ shell command มีปีกกาได้)
        if not isinstance(v, str):
            return v
        return re.sub(r"\{(\d+)(?::(url))?\}",
                      lambda m: urllib.parse.quote_plus(groups[int(m[1]) - 1]) if m[2] else groups[int(m[1]) - 1], v)

    action = {k: fill(v) for k, v in cmd["action"].items()}
    kind = action["type"]

    if kind == "open":
        start_process(action["target"])
    elif kind == "web":
        url, browser = action["url"], cfg.get("browser")
        if browser and url.startswith(("http://", "https://")):
            start_process(browser, url)
        else:
            start_process(url)  # browser ค่าเริ่มต้น / spotify: URI
    elif kind == "shell":
        subprocess.Popen(["powershell", "-NoProfile", "-Command", action["command"]],
                         creationflags=subprocess.CREATE_NO_WINDOW)
    elif kind == "key":
        winctl.press_key(action["key"], action.get("repeat", 1))
    elif kind == "hotkey":
        winctl.hotkey(*action["keys"])
    elif kind == "type":
        winctl.type_text(action["text"])
        return "พิมพ์แล้ว"
    elif kind == "note":
        path = resolve(cfg.get("notes_file", "notes.md"))
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"- {datetime.now():%Y-%m-%d %H:%M}  {action['text']}\n")
        return "จดโน้ตแล้ว"
    elif kind == "lock":
        ctypes.windll.user32.LockWorkStation()
    elif kind == "power":
        subprocess.Popen(POWER[action["mode"]], creationflags=subprocess.CREATE_NO_WINDOW)
    elif kind == "status":
        return winctl.system_status()
    elif kind == "volume":
        level = to_number(action["level"])
        if level is None:
            raise ValueError(f"ไม่เข้าใจระดับเสียง: {action['level']}")
        return f"ตั้งเสียง {winctl.set_volume(level)}%"
    elif kind == "timer":
        if "duration" in action:
            seconds = parse_duration(action["duration"])
            if seconds is None:
                raise ValueError(f"ไม่เข้าใจระยะเวลา: {action['duration']}")
        else:
            seconds = float(action["minutes"]) * 60
        island(cfg, "/timer", {"seconds": int(seconds)})
        return f"ตั้งเวลา {format_duration(seconds)}" if seconds > 0 else "ยกเลิกตัวจับเวลา"
    elif kind == "reminder":
        seconds, message = parse_duration(action["after"]), action["message"]
        if seconds is None:
            raise ValueError(f"ไม่เข้าใจระยะเวลา: {action['after']}")

        def fire():
            log.info("เตือนความจำ: %s", message)
            island(cfg, "/notify", {"title": "เตือนความจำ", "body": message, "icon": "⏰",
                                    "color": "#FF9F0A", "duration": 15})
            if ctx:
                ctx["play"]("reminder")

        timer = threading.Timer(seconds, fire)
        timer.daemon = True  # ปิด Luna แล้วไม่ต้องค้างรอ (เตือนที่ค้างอยู่จะหายไปด้วย)
        timer.start()
        return f"จะเตือน \"{message}\" ในอีก {format_duration(seconds)}"
    elif kind == "notify":
        island(cfg, "/notify", {k: v for k, v in action.items() if k != "type"})
        return action.get("title", cmd.get("name", ""))
    elif kind == "time":
        now = datetime.now()
        if action.get("show") == "date":
            return f"วัน{THAI_DAYS[now.weekday()]}ที่ {now.day} {THAI_MONTHS[now.month - 1]} {now.year + 543}"
        return f"ตอนนี้ {now:%H:%M} น."
    elif kind == "claude":
        exe = shutil.which("claude")
        if not exe:
            raise ValueError("ไม่พบคำสั่ง claude (ติดตั้ง Claude Code ก่อน)")
        prompt = action.get("prompt", "").strip()
        cwd = os.path.expandvars(os.path.expanduser(cfg.get("claude_cwd") or "~"))
        # ส่ง argv เป็น list ไม่ผ่าน shell: ข้อความจากเสียงที่มี ' " ; จะไม่กลายเป็นคำสั่ง
        subprocess.Popen([exe, prompt] if prompt else [exe], cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        return "ถาม Claude Code แล้ว" if prompt else "เปิด Claude Code"
    elif kind == "cancel":
        return "ยกเลิกแล้ว"
    else:
        raise ValueError(f"ไม่รู้จัก action type: {kind}")
    return cmd.get("name", kind)
