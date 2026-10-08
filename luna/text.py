import unicodedata


def normalize(text):
    """เทียบข้อความภาษาไทย: ไม่มีช่องว่างคั่นคำ จึงตัดช่องว่าง/วรรคตอน/อักขระควบคุมทิ้งและทำเป็นตัวเล็ก"""
    text = unicodedata.normalize("NFC", text).lower()
    return "".join(c for c in text if unicodedata.category(c)[0] not in "PZC")


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]
