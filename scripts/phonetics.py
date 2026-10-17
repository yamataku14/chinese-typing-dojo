"""数字声調ピンイン（例: "lv4"）と注音符号の相互変換。

assets/js/phonetics.js と同じ規則。どちらかを変えたら両方そろえること。
"""

INITIALS = [
    ("zh", "ㄓ"), ("ch", "ㄔ"), ("sh", "ㄕ"),
    ("b", "ㄅ"), ("p", "ㄆ"), ("m", "ㄇ"), ("f", "ㄈ"), ("d", "ㄉ"), ("t", "ㄊ"),
    ("n", "ㄋ"), ("l", "ㄌ"), ("g", "ㄍ"), ("k", "ㄎ"), ("h", "ㄏ"),
    ("j", "ㄐ"), ("q", "ㄑ"), ("x", "ㄒ"), ("r", "ㄖ"), ("z", "ㄗ"), ("c", "ㄘ"), ("s", "ㄙ"),
]

FINALS = {
    "a": "ㄚ", "o": "ㄛ", "e": "ㄜ", "ai": "ㄞ", "ei": "ㄟ", "ao": "ㄠ", "ou": "ㄡ",
    "an": "ㄢ", "en": "ㄣ", "ang": "ㄤ", "eng": "ㄥ", "er": "ㄦ", "ong": "ㄨㄥ",
    "i": "ㄧ", "ia": "ㄧㄚ", "ie": "ㄧㄝ", "iao": "ㄧㄠ", "iu": "ㄧㄡ", "ian": "ㄧㄢ",
    "in": "ㄧㄣ", "iang": "ㄧㄤ", "ing": "ㄧㄥ", "iong": "ㄩㄥ", "io": "ㄧㄛ",
    "u": "ㄨ", "ua": "ㄨㄚ", "uo": "ㄨㄛ", "uai": "ㄨㄞ", "ui": "ㄨㄟ", "uan": "ㄨㄢ",
    "un": "ㄨㄣ", "uang": "ㄨㄤ", "ueng": "ㄨㄥ",
    "v": "ㄩ", "ve": "ㄩㄝ", "van": "ㄩㄢ", "vn": "ㄩㄣ", "ue": "ㄩㄝ",
}

# y・w で始まる音節（声母なし）
ZERO = {
    "yi": "ㄧ", "ya": "ㄧㄚ", "ye": "ㄧㄝ", "yao": "ㄧㄠ", "you": "ㄧㄡ", "yan": "ㄧㄢ",
    "yin": "ㄧㄣ", "yang": "ㄧㄤ", "ying": "ㄧㄥ", "yong": "ㄩㄥ", "yo": "ㄧㄛ",
    "yu": "ㄩ", "yue": "ㄩㄝ", "yuan": "ㄩㄢ", "yun": "ㄩㄣ",
    "wu": "ㄨ", "wa": "ㄨㄚ", "wo": "ㄨㄛ", "wai": "ㄨㄞ", "wei": "ㄨㄟ", "wan": "ㄨㄢ",
    "wen": "ㄨㄣ", "wang": "ㄨㄤ", "weng": "ㄨㄥ", "e": "ㄜ", "ê": "ㄝ",
}

TONE_MARKS = {1: "", 2: "ˊ", 3: "ˇ", 4: "ˋ", 5: "˙"}


def split(numeric):
    """'lv4' -> ('lv', 4)。不正なら ValueError。"""
    s = numeric.strip().lower().replace("u:", "v").replace("ü", "v")
    if not s or s[-1] not in "12345":
        raise ValueError(numeric)
    return s[:-1], int(s[-1])


def base_to_zhuyin(base):
    if base in ZERO:
        return ZERO[base]
    if base == "r":  # 兒化の r
        return "ㄦ"
    for ini, sym in INITIALS:
        if base.startswith(ini):
            fin = base[len(ini):]
            if fin == "i" and ini in ("zh", "ch", "sh", "r", "z", "c", "s"):
                return sym
            if ini in ("j", "q", "x") and fin.startswith("u"):
                fin = "v" + fin[1:]
            if fin in FINALS:
                return sym + FINALS[fin]
            raise ValueError(base)
    if base in FINALS:
        return FINALS[base]
    raise ValueError(base)


def to_zhuyin(numeric):
    base, tone = split(numeric)
    z = base_to_zhuyin(base)
    return "˙" + z if tone == 5 else z + TONE_MARKS[tone]


def build_reverse(syllables):
    """注音（声調つき）-> 数字ピンイン の辞書を、与えた音節集合から作る。"""
    rev = {}
    for syl in syllables:
        try:
            rev.setdefault(to_zhuyin(syl), syl)
        except ValueError:
            pass
    return rev
