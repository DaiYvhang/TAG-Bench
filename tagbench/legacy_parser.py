# Adapted from the author-provided mode_result_extractor/common_parse.py.
# Parsing rules intentionally retained for historical reproducibility.
#!/usr/bin/env python
"""各模型 hyp_content -> 标准时间范围 ("X.XXs~Y.YYs", 多区间 ';' 分隔) 的公共解析库。

解析级联:
  1. 预处理: 剥离 </think> 思考链 / <conclusion> 抽取 / </s> 清理 (按模型配置)
  2. 英文数字词转数字 (twenty-three -> 23, zero point five -> 0.5)
  3. 时间 token 识别: hh:mm:ss(.ms) / mm:ss / 纯数字(可带 s/seconds)
  4. 区间抽取: 显式 range 模式 -> [a,b] 列表 -> 恰好两数配对 -> 单数点区间
解析失败返回 None (调用方记 0s~0s 并留档手动处理)。
"""
import re

# ---------- 英文数字词 ----------
_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: i * 10 for i, w in enumerate(
    "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()) if i >= 2}
_NUMWORD = re.compile(
    r"\b((?:(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[-\s](?:one|two|three|four|five|six|seven|eight|nine))?"
    r"|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen)"
    r"(?:[\s-]+(?:point[\s-]+[a-z\s-]+?|(?:zero|one|two|three|four|five|six|seven|eight|nine)(?:[\s-]+(?:zero|one|two|three|four|five|six|seven|eight|nine))*))?)"
    r"(?=[\s,.;:!?]|$)", re.I)


def _words_to_number(phrase):
    toks = re.split(r"[\s-]+", phrase.lower().strip())
    if "point" in toks:
        i = toks.index("point")
        ip, fp = toks[:i], toks[i + 1:]
    else:
        ip, fp = toks, []
    val = 0
    for t in ip:
        if t in _TENS:
            val += _TENS[t]
        elif t in _UNITS:
            # "zero one four" 这类逐位念法: 按位拼接
            if val == 0 and len(ip) > 1 and all(x in _UNITS and _UNITS[x] <= 9 for x in ip):
                digits = "".join(str(_UNITS[x]) for x in ip)
                # 以 zero 开头的逐位念法视为小数 (zero one four -> 0.14)
                val = float("0." + digits[1:]) if digits.startswith("0") and len(digits) > 1 else int(digits)
                break
            val += _UNITS[t]
        else:
            return None
    frac = ""
    for t in fp:
        if t not in _UNITS or _UNITS[t] > 9:
            return None
        frac += str(_UNITS[t])
    if frac:
        val = float(f"{int(val)}.{frac}")
    return val


_MINSEC = re.compile(r"(\d+(?:\.\d+)?)\s*minutes?(?:\s*and\s*(\d+(?:\.\d+)?)\s*seconds?)?", re.I)


def _fold_minutes(text):
    def rep(m):
        sec = float(m.group(1)) * 60 + (float(m.group(2)) if m.group(2) else 0)
        return f"{sec:g} seconds"
    return _MINSEC.sub(rep, text)


def normalize_number_words(text):
    def rep(m):
        v = _words_to_number(m.group(1))
        return str(v) if v is not None else m.group(1)
    return _fold_minutes(_NUMWORD.sub(rep, text))


# ---------- 时间 token ----------
_CLOCK = r"\d{1,2}:\d{2}(?::\d{2,3})?(?:\.\d+)?"
_NUM = r"\d+(?:\.\d+)?"
_T = rf"(?:{_CLOCK}|{_NUM})"


def to_seconds(tok):
    tok = tok.strip()
    if ":" in tok:
        parts = [float(p) for p in tok.split(":")]
        # mm:ss:ms (毫秒段 >=100, 如 mimo 的 00:05:662) 与 hh:mm:ss 区分
        if len(parts) == 3 and parts[2] >= 100:
            return parts[0] * 60 + parts[1] + parts[2] / 1000
        sec = 0.0
        for p in parts:
            sec = sec * 60 + p
        return sec
    return float(tok)


_RANGE_PATTERNS = [
    # Start time: X ... End time: Y (kimi 编号列表等), 优先于通用分隔符
    re.compile(rf"start\s*(?:time)?\s*(?:is|of|:|at)?\s*(?:around|approximately)?\s*({_T})\s*s?[^0-9\n]{{0,40}}?end\s*(?:time)?\s*(?:is|of|:|at)?\s*(?:around|approximately)?\s*({_T})", re.I),
    # 显式分隔: 5.86s~6.20s / 1.2 - 3.4 / 00:01 to 00:05 / 0.5s--0.8s / 2.41s;2.85s(gt风格不会出现在hyp,保底)
    re.compile(rf"({_T})\s*(?:s|sec(?:ond)?s?)?\s*(?:~|–|—|-{{1,2}}|to|until|till|through|,|;|and)\s*({_T})\s*(?:s|sec(?:ond)?s?)?\b", re.I),
    # start ... X ... end ... Y (跨句)
    re.compile(rf"start(?:s|ing)?[^.\d:]*?({_T})[^.]*?end(?:s|ing)?[^.\d:]*?({_T})", re.I | re.S),
    re.compile(rf"begin(?:s|ning)?[^.\d:]*?({_T})[^.]*?(?:end|stop)(?:s|ing)?[^.\d:]*?({_T})", re.I | re.S),
]
_BRACKET = re.compile(rf"\[\s*({_NUM})\s*(?:[,|]\s*({_NUM})\s*)?\]")
_LONE_TIME = re.compile(rf"(?<![\d:.])({_CLOCK})(?![\d:]|\.\d)|({_NUM})\s*(?:s\b|sec(?:ond)?s?\b)", re.I)
_ANY_NUM = re.compile(rf"(?<![\d:.\w])({_T})(?![\d:%\w]|\.\d)")


def _valid(a, b):
    return 0 <= a <= b and b < 12 * 3600


def _mmss_guard(text, tok_a, tok_b, a, b):
    """kimi '1.250-1.300' 这类小数不是 mm:ss; 但 '06:00-06:01' 是。已由 to_seconds 处理, 此处仅占位。"""
    return a, b


def extract_ranges(text):
    """返回 [(start, end), ...] 或 []"""
    ranges = []
    for pat in _RANGE_PATTERNS:
        for m in pat.finditer(text):
            try:
                a, b = to_seconds(m.group(1)), to_seconds(m.group(2))
            except ValueError:
                continue
            if _valid(a, b):
                ranges.append((a, b))
        if ranges:
            return _dedup(ranges)
    for m in _BRACKET.finditer(text):
        a = float(m.group(1))
        b = float(m.group(2)) if m.group(2) else a
        if _valid(a, b):
            ranges.append((a, b))
    if ranges:
        return _dedup(ranges)
    # 落到孤立时间值: 恰好两个 -> 区间; 恰好一个 -> 点区间
    times = []
    for m in _LONE_TIME.finditer(text):
        tok = m.group(1) or m.group(2)
        try:
            t = to_seconds(tok)
        except (ValueError, OverflowError):
            continue
        if _valid(t, t):
            times.append(t)
    if not times:
        times = []
        for m in _ANY_NUM.finditer(text):
            try:
                t = to_seconds(m.group(1))
            except (ValueError, OverflowError):
                continue
            if _valid(t, t):
                times.append(t)
        if len(times) > 2:
            return []
    if len(times) == 2 and times[0] <= times[1]:
        return [(times[0], times[1])]
    if len(times) == 1:
        return [(times[0], times[0])]
    if len(times) == 2:  # 乱序
        return [(times[1], times[0])]
    if len(times) >= 3:  # 多个孤立时间点 (如 "four times, at 0.4, 2.1, 2.9, 4.9 seconds") -> 各记点区间
        return [(t, t) for t in times]
    return []


def _dedup(ranges):
    out = []
    for r in ranges:
        if not any(abs(r[0] - o[0]) < 1e-6 and abs(r[1] - o[1]) < 1e-6 for o in out):
            out.append(r)
    return out


# ---------- 预处理 ----------
def strip_think(text):
    if "</think>" in text:
        return text.split("</think>")[-1]
    return text


def take_conclusion(text):
    m = re.findall(r"<conclusion>(.*?)</conclusion>", text, re.S)
    return m[-1] if m else text


def clean_tail(text):
    return text.replace("</s>", " ").strip()


def parse_hyp(text, preprocess=(), number_words=False):
    if text.startswith("__ERROR__"):
        return None
    raw = text
    for fn in preprocess:
        text = fn(text)
    for cand in ([text, raw] if text != raw else [text]):  # 结论段解析失败时回退到含思考链的全文
        cand = clean_tail(cand)
        if number_words:
            cand = normalize_number_words(cand)
        ranges = extract_ranges(cand)
        if ranges:
            return ";".join(f"{a:.2f}s~{b:.2f}s" for a, b in ranges)
    return None


