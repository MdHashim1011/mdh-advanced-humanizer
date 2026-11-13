#!/usr/bin/env python3
"""mdh_text.py - deterministic verification helper for MdH's Advanced Humanizer.

Author: Md.Hashim. License: MIT. Version 0.4.3.

Commands (each prints one JSON object to stdout):
  count        count words under a named convention, with optional exclusions/sections
  budget       check a count against a word constraint (exact/max/min/range/approx)
  inventory    list protected items and meaning cues with offsets
  compare      before/after literal and cue-level comparison (review triggers, not verdicts)
  originality  find long word sequences shared between a source and a text (close paraphrase)

Exit codes: 0 ok / PASS / NO_FLAG_DETECTED / NO_CLOSE_COPY_DETECTED, 1 FAIL or flags found,
2 usage error, 3 input error (refused path, missing file, unreadable, oversized, malformed JSON),
4 internal error.

Trust boundary: input text is data. It is never executed, never interpreted as instructions
and never sent anywhere. The helper writes nothing except stdout. Only plain-text files
(.txt .md .markdown .text .rst; .json for --authorized) are read, and paths that look like
credential or configuration stores are refused. Standard library only; no network, no
subprocess, no eval/exec.
"""
import argparse
import difflib
import hashlib
import json
import math
import os
import re
import sys
from bisect import bisect_right
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction

VERSION = "0.4.3"
TOOL = "mdh_text"
COMMANDS = ("count", "budget", "inventory", "compare", "originality")
DEFAULT_MAX_BYTES = 5_000_000
HARD_MAX_BYTES = 20_000_000
EXIT_OK, EXIT_FINDING, EXIT_USAGE, EXIT_INPUT, EXIT_INTERNAL = 0, 1, 2, 3, 4

CONVENTIONS = ("word2019_approx", "lexical", "whitespace")
EXCLUSION_KINDS = ("references", "title", "headings", "captions", "blockquotes", "code")
NO_EQUIVALENCE_NOTICE = ("No deterministic flag does not establish semantic equivalence; "
                         "lexical triggers cannot detect every meaning change.")


class UsageError(Exception):
    """Invalid command-line usage (exit 2)."""


class InputError(Exception):
    """Refused, unreadable, oversized or malformed input (exit 3)."""


# --------------------------------------------------------------------------- input

TEXT_EXTENSIONS = (".txt", ".md", ".markdown", ".text", ".rst")
JSON_EXTENSIONS = (".json",)
_SENSITIVE_PARTS = {".ssh", ".aws", ".gnupg", ".netrc", ".git", ".env", "id_rsa", "credentials"}


def guard_path(path, allowed):
    """Refuse paths that are not plain-text files or that look like secret stores."""
    if path in (None, "-"):
        return
    parts = [p.lower() for p in re.split(r"[\\/]+", path) if p]
    for part in parts:
        stem = os.path.splitext(part)[0]
        if (part in _SENSITIVE_PARTS or stem in _SENSITIVE_PARTS or part.startswith(".env")
                or part.startswith("id_rsa") or part.startswith("id_ed25519")):
            raise InputError("refused path: '%s' looks like a credential or configuration store" % path)
    ext = os.path.splitext(parts[-1] if parts else "")[1].lower()
    if ext not in allowed:
        raise InputError("refused path: only %s files can be read (got '%s')" % (" ".join(allowed), ext or "no extension"))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_text(text):
    return sha256_bytes(text.encode("utf-8"))


def read_input(path, max_bytes, allowed=TEXT_EXTENSIONS):
    """Read a local file (or stdin for '-'). Returns (raw_bytes, text, warnings)."""
    guard_path(path, allowed)
    warnings = []
    try:
        if path in (None, "-"):
            data = sys.stdin.buffer.read(max_bytes + 1)
        else:
            if os.path.isdir(path):
                raise InputError("path is a directory: %s" % path)
            with open(path, "rb") as fh:
                data = fh.read(max_bytes + 1)
    except FileNotFoundError:
        raise InputError("file not found: %s" % path)
    except IsADirectoryError:
        raise InputError("path is a directory: %s" % path)
    except OSError as exc:
        raise InputError("cannot read %s: %s" % (path, exc.strerror or exc))
    if len(data) > max_bytes:
        raise InputError("input exceeds the %d-byte limit" % max_bytes)
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            return data, data.decode("utf-16"), warnings
        except UnicodeDecodeError:
            raise InputError("input has a UTF-16 byte-order mark but is not valid UTF-16")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        text = data.decode("cp1252", errors="replace")
        warnings.append("input is not valid UTF-8 (first bad byte at offset %d); decoded as Windows-1252, "
                        "so a few characters may be wrong" % exc.start)
    return data, text, warnings


def normalize_newlines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


# ------------------------------------------------------------------------ counting

_DASH_TABLE = {0x2014: " ", 0x2013: " ", 0x2012: " ", 0x2015: " ", 0x2212: " "}
_WORDCHAR = re.compile(r"[^\W_]")
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯"
                  r"ᄀ-ᇿ㄰-㆏ｦ-ﾟ]")
_THAI = re.compile(r"[฀-๿]+")
_NONSPACED = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯"
                        r"ᄀ-ᇿ㄰-㆏ｦ-ﾟ฀-๿]")
# CJK symbols and punctuation (excluding the ideographic space), fullwidth punctuation, and the curly quotes,
# ellipsis and em dash that Chinese text uses.
_CJK_PUNCT = re.compile(r"[、-〿！-／：-＠［-｀｛-･"
                        r"‘’“”…—]")
CJK_NOTE = ("Chinese and Japanese character limits (字数 / 文字数) conventionally include "
            "punctuation; check such limits against cjk_characters_with_punctuation "
            "(budget --count-mode cjk_chars_with_punct). Curly quotes, ellipses and em dashes are counted as "
            "punctuation wherever they appear.")
_SPACED_ELLIPSIS =re.compile(r"(?<=\S)[ \t]+\.(?:[ \t]+\.){2,}")


def _token_words(tok, lexical):
    if not _NONSPACED.search(tok):
        return 1 if (not lexical or _WORDCHAR.search(tok)) else 0
    n = len(_CJK.findall(tok))
    n += sum(int(math.ceil(len(run) / 5.0)) for run in _THAI.findall(tok))
    rest = _THAI.sub(" ", _CJK.sub(" ", tok)).split()
    return n + sum(1 for r in rest if _WORDCHAR.search(r))


def count_words(text, convention):
    """Count words.
    word2019_approx: dashes become spaces, spaced ellipses join the previous word, then a
    whitespace split; each Chinese/Japanese/Korean character counts as one word and Thai is
    estimated at one word per five characters. lexical: the same, but tokens without a letter
    or digit are not counted. whitespace: a plain Unicode whitespace split."""
    if convention == "whitespace":
        return len(text.split())
    if convention not in ("word2019_approx", "lexical"):
        raise UsageError("unknown convention: %s" % convention)
    t = _SPACED_ELLIPSIS.sub("...", text.translate(_DASH_TABLE))
    lexical = convention == "lexical"
    return sum(_token_words(tok, lexical) for tok in t.split())


_HEADING = re.compile(r"^[ \t]{0,3}(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_SETEXT_UNDERLINE = re.compile(r"^[ \t]{0,3}(=+|-+)[ \t]*$")
_REF_NAMES = {"references", "reference list", "bibliography", "works cited", "literature cited",
              "sources", "citations", "references and notes", "list of references", "sources cited"}
_REF_LIKE = re.compile(r"\b(?:1[5-9]|20)\d{2}[a-z]?\b|\bdoi\b|\b10\.\d{4,9}/|https?://|\bn\.d\.|\bet al\.|^\s*\[\d+\]",
                       re.IGNORECASE)
_CAPTION = re.compile(r"^[ \t]*[*_]{0,2}(?:figure|fig\.|table)[ \t]+(?:S?\d+(?:\.\d+)*[a-z]?|[IVXLC]+)"
                      r"[ \t]*[*_]{0,2}[ \t]*(?:[.:][*_]{0,2}|[-–—][ \t])", re.IGNORECASE)
_FENCE = re.compile(r"^[ \t]*(```|~~~)")
_BLOCKQUOTE = re.compile(r"^[ \t]*>")
_LIST_START = re.compile(r"^[ \t]*(?:[-*+]|\d{1,3}[.)])[ \t]+")
_GREETING = re.compile(r"^(?:hi|hello|hey|dear|greetings|good (?:morning|afternoon|evening))\b", re.IGNORECASE)


def _heading_level(line):
    m = _HEADING.match(line)
    return (len(m.group(1)), m.group(2).strip()) if m else (0, None)


def _setext_lines(lines):
    """Indices of setext heading text lines mapped to their underline index."""
    out = {}
    for k in range(len(lines) - 1):
        text, under = lines[k].strip(), lines[k + 1]
        if (text and _SETEXT_UNDERLINE.match(under) and not _LIST_START.match(lines[k])
                and not _HEADING.match(lines[k]) and (k == 0 or not lines[k - 1].strip())):
            out[k] = k + 1
    return out


def _clean_heading(text):
    t = re.sub(r"^[ \t]{0,3}#{1,6}[ \t]+", "", text)
    t = " ".join(t.split())
    t = t.strip("*_ ").rstrip(":.").strip("*_ ")
    t = re.sub(r"^\d+(?:\.\d+)*[.)]?\s+", "", t)
    return t.lower()


def _looks_like_title(lines, idx, setext):
    line = lines[idx].strip()
    if re.match(r"#[ \t]", line) or idx in setext:
        return True
    if _LIST_START.match(lines[idx]) or _GREETING.match(line) or _REF_LIKE.search(line):
        return False
    if line.endswith((".", "!", "?", ":", ";", ",", ")", "\"", "”", "'")):
        return False
    words = line.split()
    next_blank = idx + 1 >= len(lines) or not lines[idx + 1].strip()
    more_after = any(l.strip() for l in lines[idx + 1:])
    return 0 < len(words) <= 20 and next_blank and more_after


def _heading_like(lines, k, setext):
    line = lines[k].strip()
    if not line:
        return False
    if _heading_level(lines[k])[0] or k in setext:
        return True
    if _REF_LIKE.search(line) or line.endswith((".", ",", ";")) or len(line.split()) > 8:
        return False
    prev_blank = k == 0 or not lines[k - 1].strip()
    next_blank = k + 1 >= len(lines) or not lines[k + 1].strip()
    return line[0].isupper() and prev_blank and next_blank


def _find_reference_blocks(lines, fenced, setext):
    """Return list of (start, end) line ranges that are reference lists."""
    content = [k for k, l in enumerate(lines) if l.strip() and not fenced[k]]
    if not content:
        return []
    rank = {k: i for i, k in enumerate(content)}
    blocks = []
    k = 0
    while k < len(lines):
        if fenced[k] or not lines[k].strip() or _clean_heading(lines[k]) not in _REF_NAMES:
            k += 1
            continue
        end = k + 1
        while end < len(lines) and not fenced[end] and not _heading_like(lines, end, setext):
            end += 1
        body = [lines[j] for j in range(k + 1, end) if lines[j].strip() and not _SETEXT_UNDERLINE.match(lines[j])]
        if not body or not _REF_LIKE.search(body[0]):
            k += 1
            continue
        ref_share = sum(1 for b in body if _REF_LIKE.search(b)) / float(len(body))
        late = rank[k] >= len(content) * 0.5
        if late or ref_share >= 0.5:
            blocks.append((k, end))
            k = end
        else:
            k += 1
    return blocks


def apply_exclusions(lines, kinds):
    """Return (marks, warnings): an exclusion kind per line (None = kept). Line-based heuristics."""
    marks = [None] * len(lines)
    warnings = []
    fenced = [False] * len(lines)
    fence_lines = [k for k, l in enumerate(lines) if _FENCE.match(l)]
    pairs = len(fence_lines) // 2 * 2
    for a, b in zip(fence_lines[0:pairs:2], fence_lines[1:pairs:2]):
        for j in range(a, b + 1):
            fenced[j] = True
    if len(fence_lines) % 2:
        start = fence_lines[-1]
        warnings.append("unclosed code fence at line %d" % (start + 1))
        if "code" in kinds:
            for j in range(start, len(lines)):
                fenced[j] = True
    if "code" in kinds:
        for j, f in enumerate(fenced):
            if f:
                marks[j] = "code"
    setext = _setext_lines(lines)
    underline_of = {u: t for t, u in setext.items()}
    if "references" in kinds:
        for a, b in _find_reference_blocks(lines, fenced, setext):
            for j in range(a, b):
                if marks[j] is None:
                    marks[j] = "references"
    first_content = next((k for k, l in enumerate(lines) if l.strip() and not fenced[k]), None)
    for k, line in enumerate(lines):
        if marks[k] is not None or fenced[k]:
            continue
        level, _ = _heading_level(line)
        is_setext = k in setext or k in underline_of
        if "title" in kinds and first_content is not None and (
                k == first_content or (k in underline_of and underline_of[k] == first_content)) \
                and _looks_like_title(lines, first_content, setext):
            marks[k] = "title"
        elif "headings" in kinds and (level or is_setext):
            marks[k] = "headings"
        elif "captions" in kinds and _CAPTION.match(line):
            marks[k] = "captions"
        elif "blockquotes" in kinds and _BLOCKQUOTE.match(line):
            marks[k] = "blockquotes"
    return marks, warnings


def select_sections(lines, names):
    """Keep only lines under Markdown headings whose text matches one of names."""
    wanted = {_clean_heading(n) for n in names}
    keep = [False] * len(lines)
    found = {}
    i = 0
    while i < len(lines):
        level, title = _heading_level(lines[i])
        if level and _clean_heading(title) in wanted:
            j = i + 1
            while j < len(lines):
                lvl2, _ = _heading_level(lines[j])
                if lvl2 and lvl2 <= level:
                    break
                keep[j] = True
                j += 1
            found.setdefault(_clean_heading(title), []).append([i + 1, j])
            i = j
            continue
        i += 1
    sections = [{"name": n, "found": _clean_heading(n) in found,
                 "line_ranges": found.get(_clean_heading(n), [])} for n in names]
    return keep, sections


def _remove_html_comments(text):
    out, pos = [], 0
    while True:
        a = text.find("<!--", pos)
        if a < 0:
            break
        b = text.find("-->", a + 4)
        if b < 0:
            break
        out.append(text[pos:a])
        pos = b + 3
    out.append(text[pos:])
    return "".join(out)


# Every pattern is bounded or cannot re-scan the same characters, so stripping is linear.
_MD_RULES = [
    (re.compile(r"\[\^[^\]\s]{1,50}\]:?"), ""),                                  # footnote markers
    (re.compile(r"^[ \t]{0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$", re.M), ""),        # thematic breaks
    (re.compile(r"^[ \t]{0,3}=+[ \t]*$", re.M), ""),                              # setext underline
    (re.compile(r"^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)*\|?[ \t]*$", re.M), ""),
    (re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+", re.M), ""),
    (re.compile(r"^[ \t]*>[ \t]?", re.M), ""),
    (re.compile(r"^[ \t]*(?:[-*+]|\d{1,3}[.)])[ \t]+", re.M), ""),
    (re.compile(r"!\[([^\[\]\n]{0,500})\]\([^()\s]{0,2000}\)"), r"\1"),
    (re.compile(r"\[([^\[\]\n]{1,500})\]\([^()\s]{0,2000}\)"), r"\1"),
    (re.compile(r"\*\*(?=\S)([^*\n]{1,500}?)(?<=\S)\*\*"), r"\1"),
    (re.compile(r"__(?=\S)([^_\n]{1,500}?)(?<=\S)__"), r"\1"),
    (re.compile(r"(?<![\w*])\*(?=\S)([^*\n]{1,500}?)(?<=\S)\*(?![\w*])"), r"\1"),
    (re.compile(r"(?<![\w_])_(?=\S)([^_\n]{1,500}?)(?<=\S)_(?![\w_])"), r"\1"),
    (re.compile(r"`([^`\n]{0,500})`"), r"\1"),
    (re.compile(r"\|"), " "),
]


def strip_markdown(text):
    """Remove common Markdown syntax so the count reflects rendered words (heuristic)."""
    text = _remove_html_comments(text)
    for pattern, repl in _MD_RULES:
        text = pattern.sub(repl, text)
    return text


def measure(text, convention, exclude=(), sections=(), markdown=True, include_all=False):
    """Core of `count`/`budget`: select sections, apply exclusions, strip Markdown, count."""
    norm = normalize_newlines(text)
    lines = norm.split("\n")
    section_info = []
    keep = [True] * len(lines)
    if sections:
        keep, section_info = select_sections(lines, sections)
    marks, warnings = apply_exclusions(lines, set(exclude))
    excluded = []
    kept_lines = []
    for k, line in enumerate(lines):
        if not keep[k]:
            continue
        if marks[k]:
            if excluded and excluded[-1]["kind"] == marks[k] and excluded[-1]["lines"][1] == k:
                excluded[-1]["lines"][1] = k + 1
                excluded[-1]["_text"].append(line)
            else:
                excluded.append({"kind": marks[k], "lines": [k + 1, k + 1], "_text": [line]})
            continue
        kept_lines.append(line)
    counted = "\n".join(kept_lines)
    if markdown:
        counted = strip_markdown(counted)
    for ex in excluded:
        body = "\n".join(ex.pop("_text"))
        ex["words"] = count_words(strip_markdown(body) if markdown else body, convention)
    total = count_words(strip_markdown(norm) if markdown else norm, convention)
    excluded_words = sum(ex["words"] for ex in excluded)
    share = round(excluded_words / float(total), 3) if total else 0.0
    if share > 0.3:
        warnings.append("exclusions removed %d%% of the words; check that only the intended parts were excluded"
                        % round(share * 100))
    if _THAI.search(counted) and convention != "whitespace":
        warnings.append("thai_estimate: Thai has no spaces between words; Thai text was estimated at "
                        "one word per five characters")
    result = {
        "convention": convention,
        "count": count_words(counted, convention),
        "input_words_before_selection": total,
        "counted_sha256": sha256_text(counted),
        "exclusions_requested": sorted(set(exclude)),
        "excluded": excluded,
        "excluded_share": share,
        "markdown_stripped": bool(markdown),
        "sections": section_info,
        "warnings": warnings,
    }
    cjk = len(_CJK.findall(counted))
    if cjk:
        punct = len(_CJK_PUNCT.findall(counted))
        result["cjk_characters"] = cjk
        result["cjk_characters_with_punctuation"] = cjk + punct
        result["cjk_note"] = CJK_NOTE
    if include_all:
        result["all_conventions"] = {c: count_words(counted, c) for c in CONVENTIONS}
    return result


COUNT_LIMITATIONS = [
    "word2019_approx matched Microsoft Word 2019 on 24 recorded test texts; it is not proven identical to Word.",
    "Exclusions and section selection are line-based heuristics; unusual layouts may be misclassified.",
    "Thai is estimated; Chinese, Japanese and Korean count one word per character.",
    "The hash proves which text the helper received, not which text was finally delivered.",
]


def evaluate_constraint(count, ctype, target=None, lo=None, hi=None, tolerance_pct=10.0):
    """Return (status, delta, normalized_constraint). Uses exact arithmetic."""
    if ctype == "exact":
        return ("PASS" if count == target else "FAIL"), count - target, {"type": "exact", "target": target}
    if ctype == "max":
        return ("PASS" if count <= target else "FAIL"), count - target, {"type": "max", "max": target}
    if ctype == "min":
        return ("PASS" if count >= target else "FAIL"), count - target, {"type": "min", "min": target}
    if ctype in ("range", "approx"):
        if ctype == "approx":
            tol = Fraction(str(tolerance_pct)) / 100
            lo = int(math.ceil(Fraction(target) * (1 - tol)))
            hi = int(math.floor(Fraction(target) * (1 + tol)))
        delta = 0 if lo <= count <= hi else (count - hi if count > hi else count - lo)
        c = {"type": ctype, "min": lo, "max": hi}
        if ctype == "approx":
            c.update({"target": target, "tolerance_pct": tolerance_pct})
        return ("PASS" if delta == 0 else "FAIL"), delta, c
    raise UsageError("unknown constraint type: %s" % ctype)


# ----------------------------------------------------------------------- sentences

_ABBREV = {"e.g.", "i.e.", "al.", "etc.", "dr.", "mr.", "mrs.", "ms.", "prof.", "fig.", "figs.", "no.",
           "vs.", "p.", "pp.", "vol.", "ch.", "sec.", "approx.", "u.s.", "u.k.", "cf.", "jr.", "sr.",
           "st.", "inc.", "ltd.", "eq.", "ref.", "refs.", "ed.", "eds."}
_LABEL_NOUNS = {"group", "arm", "condition", "method", "model", "drug", "site", "option", "type", "class",
                "cohort", "phase", "version", "plan", "treatment", "sample", "region", "school", "clinic",
                "case", "scenario", "factor", "item", "level", "wave", "stage", "step", "appendix",
                "section", "part", "grade", "vitamin", "category", "team", "unit", "ward", "zone"}
_BOUNDARY = re.compile(r"[.!?…]+[\"”’)\]]*\s+")
_BLOCK_BREAK = re.compile(r"\n[ \t]*\n|\n(?=[ \t]*(?:#{1,6}\s|[-*+]\s|\d{1,3}[.)]\s|>))")


def split_sentences(text):
    """Split into sentences with character offsets. Heuristic: abbreviations, initials and
    lowercase continuations do not end a sentence; blank lines and list/heading lines do.
    A single capital letter after a label noun ("group A.") ends a sentence."""
    sentences = []
    block_start = 0
    blocks = []
    for m in _BLOCK_BREAK.finditer(text):
        blocks.append((block_start, m.start()))
        block_start = m.end()
    blocks.append((block_start, len(text)))
    for b_start, b_end in blocks:
        block = text[b_start:b_end]
        start = 0
        for m in _BOUNDARY.finditer(block):
            before = block[max(start, m.start() - 40):m.start() + 1].split()
            last = (before[-1].lower() if before else "")
            prev = (before[-2].lower().strip("(\"'") if len(before) > 1 else "")
            nxt = block[m.end():m.end() + 1]
            initial = re.fullmatch(r"[a-z]\.", last) and prev not in _LABEL_NOUNS
            if last in _ABBREV or initial or (nxt and nxt.islower()):
                continue
            _push_sentence(sentences, block, b_start, start, m.end())
            start = m.end()
        _push_sentence(sentences, block, b_start, start, len(block))
    return sentences


def _push_sentence(out, block, offset, start, end):
    seg = block[start:end]
    stripped = seg.strip()
    if not stripped:
        return
    lead = len(seg) - len(seg.lstrip())
    s = offset + start + lead
    out.append({"index": len(out), "start": s, "end": s + len(stripped), "text": stripped})


def sentence_of(starts, sentences, pos):
    """Index of the sentence containing character offset pos, or None."""
    k = bisect_right(starts, pos) - 1
    if k >= 0 and pos < sentences[k]["end"]:
        return k
    return None


# ----------------------------------------------------------------------- inventory

_YEAR = r"(?:1[5-9]|20)\d{2}[a-z]?"
_NAME = r"[A-Z][\w'’-]+"
_ITEM_PATTERNS = [
    ("code", re.compile(r"`[^`\n]{1,500}`"), "regex: backtick span"),
    ("url", re.compile(r"\bhttps?://[^\s<>\"'`]{1,2048}"), "regex: http(s) URL"),
    ("email", re.compile(r"\b[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,8}\b"), "regex: e-mail address"),
    ("doi", re.compile(r"\b10\.\d{4,9}/[^\s\"<>]{1,256}"), "regex: DOI"),
    ("quotation", re.compile(r"“[^”\n]{1,600}”|\"[^\"\n]{1,600}\""), "regex: paired double quotes"),
    ("citation", re.compile(r"\((?=[^()]{0,200}\b" + _YEAR + r"\b)(?=[^()]{0,200}" + _NAME + r")[^()\n]{1,200}\)"),
     "regex: parenthetical with capitalised name and year"),
    ("citation", re.compile(_NAME + r"(?:\s+et al\.|\s+(?:and|&)\s+" + _NAME + r")?\s+\(" + _YEAR +
                            r"(?:,\s*pp?\.\s*\d+(?:[–-]\d+)?)?\)"), "regex: narrative author (year)"),
    ("citation", re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]"), "regex: numeric bracket citation"),
    ("statistic", re.compile(r"\b\d{2}%\s*(?:CI|confidence interval)\s*[\[(][^\])\n]{1,60}[\])]"),
     "regex: confidence interval"),
    ("statistic", re.compile(r"\bp\s*(?:[<>=≤≥])\s*0?\.\d+"), "regex: p-value"),
    ("statistic", re.compile(r"(?<![\w.])(?:n|N|d|r|t|F|z|R2|R²|β|OR|RR|HR|SD|SE|M|df)"
                             r"\s*(?:\(\s*\d+(?:\s*,\s*\d+)?\s*\))?\s*=\s*[-−]?\d*\.?\d+"),
     "regex: test statistic"),
    ("technical_expression", re.compile(r"\b[A-Za-z_][\w.]{0,63}\s{0,3}(?:>=|<=|==|!=|<|>)\s{0,3}[\w.]{1,64}"
                                        r"(?:\s{0,3}(?:&&|\|\|)\s{0,3}[A-Za-z_][\w.]{0,63}\s{0,3}"
                                        r"(?:>=|<=|==|!=|<|>)\s{0,3}[\w.]{1,64}){0,8}"),
     "regex: comparison expression"),
    ("equation", re.compile(r"\b[A-Za-z][A-Za-z0-9_]{0,31}\s{0,3}=\s{0,3}[A-Za-z0-9_.()]{1,32}"
                            r"(?:\s{0,3}[-+*/^×÷]\s{0,3}[A-Za-z0-9_.()]{1,32}){1,16}"), "regex: simple equation"),
    ("identifier", re.compile(r"\b[A-Z][A-Z0-9]{1,15}-\d{1,10}[A-Za-z0-9-]{0,16}\b"
                              r"|\b[a-z][a-z0-9]{0,31}_[a-z0-9_]{1,48}\b"
                              r"|\b[a-z]{1,32}[A-Z][A-Za-z0-9]{1,48}\b|\b\w{1,64}\(\)|\bv?\d{1,6}\.\d{1,6}\.\d{1,6}\b"),
     "regex: code-like identifier"),
]

_NUM = re.compile(
    r"(?<![\w.,])(?P<cur>[$€£¥])?(?P<sign>[-−])?"
    r"(?P<val>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)"
    r"(?P<suf>[ \t]?%|-?fold\b|[x×](?![\w])|(?:k|bn|m)(?![\w])|(?:st|nd|rd|th)(?![\w]))?"
    r"(?:[ \t](?P<scale>thousand|million|billion|trillion)\b)?(?![\w])", re.IGNORECASE)
_SMALL = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
          "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
          "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
         "ninety": 90}
_SCALES = {"hundred": 100, "thousand": 1000, "million": 10 ** 6, "billion": 10 ** 9, "trillion": 10 ** 12}
_NUMWORD = "|".join(sorted(list(_SMALL) + list(_TENS) + list(_SCALES), key=len, reverse=True))
_WORDNUM = re.compile(r"\b(?:%s)(?:(?:[-\s]+|\s+and\s+)(?:%s))*\b" % (_NUMWORD, _NUMWORD), re.IGNORECASE)
_FOLDWORD = re.compile(r"\b(%s)[-]?fold\b" % "|".join(list(_SMALL) + list(_TENS) + ["hundred"]), re.IGNORECASE)
_ORDWORD = re.compile(r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)\b",
                      re.IGNORECASE)
_ORD_VALUE = {w: i + 1 for i, w in enumerate(["first", "second", "third", "fourth", "fifth", "sixth", "seventh",
                                              "eighth", "ninth", "tenth", "eleventh", "twelfth"])}
_SCALE_SUFFIX = {"k": 1000, "bn": 10 ** 9, "m": 10 ** 6}

_UNIT_CANON = {
    "%": "%", "percent": "%", "pct": "%", "pp": "pp", "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gram": "g", "grams": "g", "mg": "mg", "milligram": "mg", "milligrams": "mg", "ug": "ug",
    "µg": "ug", "microgram": "ug", "micrograms": "ug", "km": "km", "kilometre": "km", "kilometres": "km",
    "kilometer": "km", "kilometers": "km", "m": "m", "metre": "m", "metres": "m", "meter": "m", "meters": "m",
    "cm": "cm", "centimetre": "cm", "centimetres": "cm", "centimeter": "cm", "centimeters": "cm", "mm": "mm",
    "millimetre": "mm", "millimetres": "mm", "millimeter": "mm", "millimeters": "mm", "nm": "nm",
    "mi": "mi", "mile": "mi", "miles": "mi", "ft": "ft", "foot": "ft", "feet": "ft", "in": None,
    "s": "s", "sec": "s", "second": "s", "seconds": "s", "ms": "ms", "min": "min", "minute": "min",
    "minutes": "min", "h": "h", "hr": "h", "hrs": "h", "hour": "h", "hours": "h", "day": "day", "days": "day",
    "week": "week", "weeks": "week", "month": "month", "months": "month", "year": "year", "years": "year",
    "ml": "ml", "millilitre": "ml", "millilitres": "ml", "milliliter": "ml", "milliliters": "ml", "l": "l",
    "litre": "l", "litres": "l", "liter": "l", "liters": "l", "hz": "hz", "khz": "khz", "mhz": "mhz",
    "ghz": "ghz", "kb": "kb", "mb": "mb", "gb": "gb", "tb": "tb", "kw": "kw", "w": "w", "v": "v", "a": None,
    "c": "c", "k": "k", "mol": "mol", "points": "point", "point": "point", "words": "words", "pages": "pages",
    "usd": "usd", "dollars": "usd", "dollar": "usd", "eur": "eur", "euros": "eur", "euro": "eur",
    "gbp": "gbp", "kwh": "kwh", "db": "db", "°c": "°c", "°f": "°f", "mmhg": "mmhg",
    "degrees": "degree", "degree": "degree", "times": "fold", "fold": "fold", "x": "fold",
}
_UNIT_PHRASE = re.compile(r"\s*(percentage points?|per cent|percent)\b")
_UNIT_PHRASE_CANON = {"percentage points": "pp", "percentage point": "pp", "per cent": "%", "percent": "%"}
_CLAUSE_STOP = re.compile(r"[.;:!?,)\]](?:\s|$)")
_TAIL_TOKEN = re.compile(r"[^\s.,;:()\[\]]+")
_ROLE_SKIP = {"versus", "vs", "relative", "compared", "against", "than", "over", "per", "from", "to", "by", "at",
              "in", "on", "with", "within", "across", "among", "after", "before", "during", "since", "until",
              "of", "the", "a", "an", "and", "or", "for", "respectively", "each", "only", "about", "around",
              "approximately", "nearly", "almost", "roughly", "more", "less", "fewer"}
_ROLE_WORD = re.compile(r"[^\W\d_][\w'-]*")
MAX_NUMBER_ITEMS = 50_000
def repeated_openers(sentences, min_run=3):
    """Runs of >= min_run consecutive sentences that open with the same word (ignoring the/a/an).
    Informational: a style signal, not an error."""
    firsts = []
    for s in sentences:
        toks = _TOKEN.findall(s["text"])
        low = [t.lower() for t in toks[:2]]
        if low and low[0] in ("the", "a", "an"):
            low = low[1:]
        firsts.append(low[0] if low else None)
    runs, i = [], 0
    while i < len(firsts):
        j = i
        while j + 1 < len(firsts) and firsts[i] is not None and firsts[j + 1] == firsts[i]:
            j += 1
        if firsts[i] is not None and j - i + 1 >= min_run:
            runs.append({"word": firsts[i], "sentence_indexes": list(range(i, j + 1))})
        i = j + 1
    return runs


TRUNCATION_WARNING =("more than %d numbers found; numbers after that point were not analysed, so changes "
                      "to them are not detected" % MAX_NUMBER_ITEMS)
_STOP = {"of", "the", "a", "an", "in", "on", "for", "to", "and", "or", "per", "at", "by", "with", "from"}
_TRAIL = ".,;:)]}>'\""
_LABEL_NUMBER_PREFIX = re.compile(r"(?:figure|fig\.|table|section|chapter|appendix|step|page|pp?\.|eq\.|"
                                  r"equation|item|question|q)\s*$", re.IGNORECASE)
ITEM_LIMITATION = ("Conservative regular expressions: unusual citation styles, multi-line equations "
                   "and non-English number formats may be missed or misclassified.")


def _clean_span(category, text, start, end):
    if category in ("url", "doi", "technical_expression", "equation"):
        while text and text[-1] in _TRAIL and not (text[-1] == ")" and text.count("(") >= text.count(")")):
            text, end = text[:-1], end - 1
    return text, start, end


def _normalize_statistic(text):
    t = text.replace("−", "-").replace(" ", "")
    return re.sub(r"(?<![\d])\.(\d)", r"0.\1", t)


def _canonical_value(value):
    try:
        d = Decimal(value)
    except InvalidOperation:
        return value
    if d == d.to_integral_value():
        return str(int(d))
    return format(d.normalize(), "f")


def _parse_wordnum(text):
    total, current = 0, 0
    for w in re.split(r"[-\s]+", text.lower()):
        if not w or w == "and":
            continue
        if w in _SMALL:
            current += _SMALL[w]
        elif w in _TENS:
            current += _TENS[w]
        elif w == "hundred":
            current = (current or 1) * 100
        elif w in _SCALES:
            total += (current or 1) * _SCALES[w]
            current = 0
    return total + current


def _number_context(text, end):
    """Unit and role word that follow a number inside the same clause."""
    tail = text[end:end + 80]
    stop = _CLAUSE_STOP.search(tail)
    if stop:
        tail = tail[:stop.start()]
    low = tail.lower()
    unit = None
    m = _UNIT_PHRASE.match(low)
    if m:
        unit, low = _UNIT_PHRASE_CANON[m.group(1)], low[m.end():]
    role = None
    for tok in _TAIL_TOKEN.findall(low)[:7]:
        if unit is None and role is None and _UNIT_CANON.get(tok):
            unit = _UNIT_CANON[tok]
            continue
        if tok in _STOP or tok in _ROLE_SKIP:
            continue
        if _ROLE_WORD.fullmatch(tok):
            role = tok
        break
    return unit, role


def _number_key(value, unit, cur=""):
    v = (cur or "") + value
    if not unit:
        return v
    return v + unit if unit == "%" else v + " " + unit


class _Items(list):
    """Item list that records whether number analysis stopped at MAX_NUMBER_ITEMS."""
    truncated = False


class _Coverage:
    """Tracks claimed character spans; overlap test and marking are proportional to span length."""

    def __init__(self, n):
        self.cov = bytearray(n + 1)

    def free(self, s, e):
        return self.cov.find(1, s, e) == -1

    def take(self, s, e):
        self.cov[s:e] = b"\x01" * (e - s)


def find_items(text, sentences):
    cov = _Coverage(len(text))
    starts = [s["start"] for s in sentences]
    items = _Items()
    numbers = 0

    def add(category, span, s, e, method, **extra):
        if not span.strip() or not cov.free(s, e):
            return False
        cov.take(s, e)
        item = {"category": category, "text": span, "start": s, "end": e,
                "sentence_index": sentence_of(starts, sentences, s), "method": method}
        item.update(extra)
        items.append(item)
        return True

    for category, pattern, method in _ITEM_PATTERNS:
        for m in pattern.finditer(text):
            span, s, e = _clean_span(category, m.group(0), m.start(), m.end())
            norm = _normalize_statistic(span) if category == "statistic" else " ".join(span.split())
            add(category, span, s, e, method, normalized=norm)

    for m in _NUM.finditer(text):
        s, e = m.start(), m.end()
        if not cov.free(s, e):
            continue
        numbers += 1
        if numbers > MAX_NUMBER_ITEMS:
            items.truncated = True
            break
        suf = (m.group("suf") or "").strip().lower()
        val = m.group("val").replace(",", "")
        if suf in ("st", "nd", "rd", "th"):
            add("ordinal", m.group(0), s, e, "regex: ordinal", normalized=_canonical_value(val))
            continue
        plain = val.isdigit() and not suf and not m.group("scale") and not m.group("sign")
        if not plain:
            try:
                d = Decimal(val)
            except InvalidOperation:
                continue
        unit = None
        if suf == "%":
            unit = "%"
        elif suf in ("x", "×") or suf.endswith("fold"):
            unit = "fold"
        elif suf == "m" and not m.group("cur"):
            unit = "m"
        elif suf in _SCALE_SUFFIX:
            d *= _SCALE_SUFFIX[suf]
        if m.group("scale"):
            d *= _SCALES[m.group("scale").lower()]
        if plain:
            value = str(int(val))
        else:
            if m.group("sign"):
                d = -d
            value = _canonical_value(str(d))
        ctx_unit, role = _number_context(text, e)
        unit = unit or ctx_unit
        if _LABEL_NUMBER_PREFIX.search(text[max(0, s - 12):s]):
            role = None
        add("number", m.group(0), s, e, "regex: numeral",
            normalized=_number_key(value, unit, m.group("cur")), value=value, unit=unit, role_word=role)

    for m in _FOLDWORD.finditer(text):
        word = m.group(1).lower()
        value = str(_SMALL.get(word) or _TENS.get(word) or 100)
        add("number", m.group(0), m.start(), m.end(), "words: multiplier",
            normalized=_number_key(value, "fold"), value=value, unit="fold", role_word=None)

    for m in _WORDNUM.finditer(text):
        span = m.group(0)
        words = re.split(r"[-\s]+", span.lower())
        if len(words) == 1 and words[0] in ("one", "hundred", "thousand", "million", "billion", "trillion"):
            continue
        value = str(_parse_wordnum(span))
        unit, role = _number_context(text, m.end())
        add("number", span, m.start(), m.end(), "words: spelled-out number",
            normalized=_number_key(value, unit), value=value, unit=unit, role_word=role)

    for m in _ORDWORD.finditer(text):
        add("ordinal", m.group(0), m.start(), m.end(), "words: ordinal",
            normalized=str(_ORD_VALUE[m.group(1).lower()]))

    items.sort(key=lambda it: it["start"])
    for k, it in enumerate(items):
        it["id"] = "I%03d" % (k + 1)
    return items


def _cue(pattern, form):
    return re.compile(pattern, re.IGNORECASE), form


_CUES = {
    "negation": [
        _cue(r"\bnot any\b", "no"),
        _cue(r"\b\w+n[’']t\b", "not"), _cue(r"\bnot\b", "not"), _cue(r"\bcannot\b", "not"),
        _cue(r"\bfail(?:s|ed|ing)?\s+to\b", "not"), _cue(r"\black(?:s|ed|ing)?\b", "not"),
        _cue(r"\bnon-?significant\b|\binsignificant\b", "not"),
        _cue(r"\bno\b(?!\.\s*\d)", "no"), _cue(r"\bnone\b|\bnothing\b|\bnobody\b|\bno one\b", "none"),
        _cue(r"\bnever\b", "never"), _cue(r"\bneither\b|\bnor\b", "neither"), _cue(r"\bwithout\b", "without"),
        _cue(r"\babsence of\b", "absence"),
    ],
    "hedge": [_cue(r"\b(?:may|might|could|possibly|perhaps|probably|likely|unlikely|potentially|plausibly|"
                   r"tentative(?:ly)?|preliminary|roughly|approximately|seem(?:s|ed)?|appear(?:s|ed)?|"
                   r"suggest(?:s|ed|ing)?|indicat(?:e|es|ed|ing)|tend(?:s|ed)? to|is consistent with|"
                   r"to some extent)\b", "hedge")],
    "certainty": [_cue(r"\b(?:clearly|prov(?:e|es|ed|en)|demonstrat(?:e|es|ed)|establish(?:es|ed)?|"
                       r"confirm(?:s|ed)?|definitely|certainly|undoubtedly|conclusively|show(?:s|ed|n)?)\b",
                       "certainty")],
    "condition": [_cue(r"\bonly if\b|\bonly when\b|\bif and only if\b", "only_if"), _cue(r"\bunless\b", "unless"),
                  _cue(r"\b(?:provided that|as long as|on condition that|assuming that)\b", "if"),
                  _cue(r"\bif\b", "if"), _cue(r"\bwhen(?:ever)?\b(?!\s+compared\s+(?:with|to|against)\b)", "when")],
    "causal": [_cue(r"\b(?:caus(?:e|es|ed|ing)|lead(?:s)? to|led to|result(?:s|ed)? in|due to|because|"
                    r"therefore|consequently|effect of|affect(?:s|ed)|driv(?:e|es)|drove|produc(?:e|es|ed)|"
                    r"responsible for)\b", "causal")],
    "association": [_cue(r"\b(?:associated with|association|correlat\w*|linked (?:to|with)|related to|"
                         r"relationship between|co-occur\w*|predict(?:s|ed|or|ors)?)\b", "association")],
    "quantifier": [_cue(r"\b(?:all|every|each|most|many|some|several|few|majority|minority|half|"
                        r"(?<!not )any|always|often|frequently|commonly|sometimes|occasionally|rarely|seldom|"
                        r"usually|typically|generally|numerous)\b", "q")],
    "qualifier": [_cue(r"\b(?:only|partly|partially|largely|mainly|primarily|in part|slightly|at least|"
                       r"up to|at most|except|in some cases|under certain conditions)\b", "qual")],
    "equivalence": [_cue(r"\b(?:equivalent|no difference|did not differ|does not differ|same as|identical|"
                         r"comparable|equally effective|no effect)\b", "equivalence")],
}
_HEDGE_CLASS = [
    (re.compile(r"^(?:may|might|could|possibly|perhaps|potentially|plausibly)$"), "possible"),
    (re.compile(r"^(?:probably|likely)$"), "likely"),
    (re.compile(r"^unlikely$"), "unlikely"),
    (re.compile(r"^(?:seem|appear)"), "appears"),
    (re.compile(r"^(?:suggest|indicat|is consistent with)"), "suggests"),
    (re.compile(r"^(?:roughly|approximately)$"), "approx"),
    (re.compile(r"^(?:tentative|preliminary)"), "tentative"),
    (re.compile(r"^tend"), "tends"),
    (re.compile(r"^to some extent$"), "partial"),
]
_QUANT_CLASS = {"all": "all", "every": "all", "each": "all", "most": "most", "majority": "most",
                "many": "many", "numerous": "many", "some": "some", "several": "several", "few": "few",
                "minority": "few", "half": "half", "any": "any", "always": "always", "often": "often",
                "frequently": "often", "commonly": "often", "sometimes": "sometimes", "occasionally": "sometimes",
                "rarely": "rarely", "seldom": "rarely", "usually": "usually", "typically": "usually",
                "generally": "usually"}
_STRONG_CERTAINTY = re.compile(r"^(?:clearly|prov|definitely|certainly|undoubtedly|conclusively)")
_QUALIFIER_WATCH = {"only", "at least", "at most", "up to", "except"}
_NONSIG = re.compile(r"\bnot (?:statistically )?significant\b|\bnon-?significant\b|"
                     r"\bp\s*[=>≥]\s*0?\.(?:0[5-9]|[1-9])", re.IGNORECASE)
_DIRECTIONAL = re.compile(r"\b(?:than|outperform\w*|exceed\w*|surpass\w*|preced\w*|caus\w*|led to|"
                          r"lead to|before|after)\b", re.IGNORECASE)


def _axis_table():
    t = {}

    def put(axis, value, words):
        for w in words.split():
            t[w] = (axis, value)
    put("amount", "up", "increase increases increased increasing rise rises rose risen rising raise raises raised "
                        "raising grow grows grew grown growing gain gains gained higher highest more greater larger "
                        "above exceed exceeds exceeded boost boosts boosted climb climbs climbed surge surged")
    put("amount", "down", "decrease decreases decreased decreasing fall falls fell fallen falling drop drops dropped "
                          "decline declines declined declining reduce reduces reduced reducing reduction lower "
                          "lowers lowered lowest less fewer smaller below shrink shrank shrunk cut cuts loss losses "
                          "plunge plunged")
    put("time", "before", "before prior earlier preceded precedes")
    put("time", "after", "after later afterwards subsequently")
    put("quality", "good", "better best improve improves improved improving improvement benefit benefits "
                           "benefited superior")
    put("quality", "bad", "worse worst worsen worsens worsened deteriorate deteriorated deterioration harm harms "
                          "harmed inferior")
    put("likelihood", "likely", "likely probable")
    put("likelihood", "unlikely", "unlikely improbable")
    put("decision", "yes", "approve approves approved approval accept accepts accepted acceptance grant granted "
                           "allow allows allowed permit permitted")
    put("decision", "no", "reject rejects rejected rejection deny denies denied refuse refused forbid forbidden "
                          "prohibit prohibited")
    put("outcome", "positive", "positive")
    put("outcome", "negative", "negative")
    put("outcome", "inconclusive", "inconclusive")
    put("outcome", "conclusive", "conclusive")
    put("significance", "significant", "significant significantly")
    put("significance", "nonsignificant", "insignificant nonsignificant")
    put("share", "majority", "majority")
    put("share", "minority", "minority")
    put("obligation", "required", "must shall required mandatory obligatory")
    put("obligation", "recommended", "should ought recommended")
    put("obligation", "permitted", "may optional")
    return t


_AXES = _axis_table()
_POLARITY_PREFIXES = ("un", "in", "non", "non-", "im", "ir", "il", "dis")
_LABEL_RE = re.compile(r"\b(?i:%s)\s+([A-Z]|[IVX]{1,4}|\d{1,2})\b" % "|".join(sorted(_LABEL_NOUNS)))
_MONTH_CONTEXT = re.compile(r"\s*\d")


def find_cues(text, sentences):
    starts = [s["start"] for s in sentences]
    cues = []
    for cls, patterns in _CUES.items():
        cov = _Coverage(len(text))
        for pattern, form in patterns:
            for m in pattern.finditer(text):
                if not cov.free(m.start(), m.end()):
                    continue
                if cls == "hedge" and m.group(0) == "May":
                    before = text[max(0, m.start() - 200):m.start()].rstrip()
                    at_start = not before or before[-1] in ".!?\n"
                    if not at_start or _MONTH_CONTEXT.match(text[m.end():]):
                        continue
                cov.take(m.start(), m.end())
                f = m.group(0).lower() if form in ("q", "qual", "hedge", "certainty", "causal") else form
                cues.append({"class": cls, "form": " ".join(f.split()), "text": m.group(0), "start": m.start(),
                             "end": m.end(), "sentence_index": sentence_of(starts, sentences, m.start())})
    cues.sort(key=lambda c: (c["start"], c["class"]))
    return cues


def build_inventory(text):
    norm = normalize_newlines(text)
    sentences = split_sentences(norm)
    items = find_items(norm, sentences)
    cues = find_cues(norm, sentences)
    return norm, sentences, items, cues


# ------------------------------------------------------------------------- compare

_TOKEN = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)
_LITERAL_CATEGORIES = ("code", "url", "email", "doi", "quotation", "citation", "statistic",
                       "technical_expression", "equation", "identifier", "number")


def _tokens(s):
    return [t.lower() for t in _TOKEN.findall(s)]


def _dice(ca, cb, la, lb):
    if not la and not lb:
        return 1.0
    return 2.0 * sum((ca & cb).values()) / (la + lb)


def align_sentences(orig, rev):
    """Align each original sentence to the best revised sentence or adjacent pair.
    Identical sentences are anchored first (sequence match over normalised sentence keys);
    the rest are matched only inside the gap between anchors, so inserted or deleted
    passages do not shift every later sentence."""
    otok = [_tokens(s["text"]) for s in orig]
    rtok = [_tokens(s["text"]) for s in rev]
    ocnt = [Counter(t) for t in otok]
    rcnt = [Counter(t) for t in rtok]
    out = [None] * len(orig)
    sm = difflib.SequenceMatcher(None, [" ".join(t) for t in otok], [" ".join(t) for t in rtok], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                out[i1 + k] = {"original": i1 + k, "revised": [j1 + k], "score": 1.0, "ambiguous": False,
                               "confident": True, "exact": True}
            continue
        lo_j, hi_j = max(0, j1 - 1), min(len(rev), j2 + 1)
        span_o = max(1, i2 - i1)
        for i in range(i1, i2):
            expected = j1 + (i - i1) * (j2 - j1) / float(span_o)
            lo, hi = max(lo_j, int(expected) - 30), min(hi_j, int(expected) + 31)
            cands = []
            for j in range(lo, hi):
                single = _dice(ocnt[i], rcnt[j], len(otok[i]), len(rtok[j]))
                cands.append(((j,), single))
                if j + 1 < hi:
                    nxt = _dice(ocnt[i], rcnt[j + 1], len(otok[i]), len(rtok[j + 1]))
                    merged = _dice(ocnt[i], rcnt[j] + rcnt[j + 1], len(otok[i]), len(rtok[j]) + len(rtok[j + 1]))
                    if merged >= max(single, nxt) + 0.1:
                        cands.append(((j, j + 1), merged))
            cands.sort(key=lambda c: (-c[1], abs(c[0][0] - expected)))
            best = cands[0] if cands else ((), 0.0)
            second = cands[1][1] if len(cands) > 1 else 0.0
            # A single sentence sandwiched between identical anchors is almost certainly its own rewrite.
            sandwiched = i2 - i1 == 1 and j2 - j1 == 1 and best[0] == (j1,)
            floor = 0.25 if sandwiched else 0.5
            ambiguous = best[1] < floor or (not sandwiched and best[1] < 0.9 and second >= 0.5
                                            and best[1] - second < 0.05 and not set(best[0]) & set(cands[1][0]))
            out[i] = {"original": i, "revised": list(best[0]), "score": round(best[1], 3),
                      "ambiguous": bool(ambiguous), "confident": best[1] >= floor, "exact": False}
    return out


def _group_by_sentence(entries):
    by = {}
    for e in entries:
        by.setdefault(e["sentence_index"], []).append(e)
    return by


def _cues_in(by_sentence, idxs):
    by = {}
    for i in idxs:
        for c in by_sentence.get(i, []):
            by.setdefault(c["class"], []).append(c["form"])
    return by


def _osa_distance(a, b, limit=2):
    """Damerau-Levenshtein (optimal string alignment) distance, or limit + 1 once it exceeds limit."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > limit:
            return limit + 1
        prev2, prev = prev, cur
    return prev[-1]


def _absorb_spelling_fixes(oc, by_sentence, rev_idxs, otext):
    """Treat a cue that appears in the revision as already present in the original when the original
    has a misspelling of it (distance <= 2, same first letter, cue word of 5+ letters): a spelling fix
    such as 'becuase' -> 'because' is not a new causal claim."""
    rc = _cues_in(by_sentence, rev_idxs)
    otoks = set(_tokens(otext))
    out = {k: list(v) for k, v in oc.items()}
    for cls, forms in rc.items():
        excess = Counter(forms) - Counter(out.get(cls, []))
        if not excess:
            continue
        for i in rev_idxs:
            for c in by_sentence.get(i, []):
                if c["class"] != cls or excess[c["form"]] <= 0:
                    continue
                words = [w for w in _tokens(c["text"]) if len(w) >= 5]
                if any(t != w and t[0] == w[0] and _osa_distance(t, w) <= 2 for w in words for t in otoks):
                    out.setdefault(cls, []).append(c["form"])
                    excess[c["form"]] -= 1
    return out


def _items_in(by_sentence, idxs, category=None):
    out = []
    for i in idxs:
        out.extend(it for it in by_sentence.get(i, []) if category is None or it["category"] == category)
    return out


def _side_flips(otext, rtext):
    om, rm = _DIRECTIONAL.search(otext), _DIRECTIONAL.search(rtext)
    if not om or not rm:
        return []
    ignore = _STOP | {"was", "were", "is", "are", "be", "been", "by", "than", "that", "this"}

    def keep(t):  # single capital letters are entity labels ("method A")
        return (len(t) > 2 and t.lower() not in ignore) or (len(t) == 1 and t.isupper())

    def sides(text, pos):
        left = [t.lower() for t in _TOKEN.findall(text[:pos]) if keep(t)]
        right = [t.lower() for t in _TOKEN.findall(text[pos:]) if keep(t)]
        return left, right
    ol, orr = sides(otext, om.start())
    rl, rr = sides(rtext, rm.start())
    to_right = [w for w in ol if w in rr and w not in rl and w not in orr]
    to_left = [w for w in orr if w in rl and w not in rr and w not in ol]
    return sorted(set(to_right)) + sorted(set(to_left)) if to_right and to_left else []


class Findings:
    def __init__(self, authorized_pairs):
        self.items = []
        self.pairs = authorized_pairs

    def add(self, kind, code, category, message, orig=None, rev=None, score=None, values=None, literal=False,
            authorizable=True):
        values = values or {}
        auth = False
        if literal and authorizable:
            key = (values.get("original", ""), values.get("revised", ""))
            auth = key in self.pairs
        self.items.append({"id": "F%03d" % (len(self.items) + 1), "kind": kind, "code": code,
                           "category": category, "literal": literal, "authorized": auth, "message": message,
                           "original_sentence": orig, "revised_sentence": rev, "alignment_score": score,
                           "values": values})


def auth_key(s):
    """Canonical form of an authorised value, matching how protected items are normalised."""
    s = " ".join((s or "").split())
    if not s:
        return ""
    items = [it for it in find_items(s, split_sentences(s)) if it["category"] in _LITERAL_CATEGORIES]
    if len(items) == 1 and len(items[0]["text"]) >= len(s.rstrip(".")) - 1:
        return items[0]["normalized"]
    num = [it for it in items if it["category"] == "number"]
    if len(num) == 1 and items == num:
        return num[0]["normalized"]
    return s


def _term_count(text, term):
    """Exact, case-sensitive occurrences of term; word-character edges must not touch other word characters."""
    pattern = re.escape(term)
    if _WORDCHAR.match(term[0]) or term[0].isdigit():
        pattern = r"(?<![\w])" + pattern
    if _WORDCHAR.match(term[-1]) or term[-1].isdigit():
        pattern += r"(?![\w])"
    return len(re.findall(pattern, text))


def compare_texts(original, revised, authorized=(), protect=()):
    """Compare original and revised text.
    authorized: iterable of (from, to) string pairs; protect: iterable of exact terms that must survive."""
    pairs = {(auth_key(a), auth_key(b)) for a, b in authorized}
    ot, osent, oitems, ocues = build_inventory(original)
    rt, rsent, ritems, rcues = build_inventory(revised)
    f = Findings(pairs)

    # 0. user-protected terms (exact, case-sensitive; never authorisable)
    for term in protect:
        oc, rc = _term_count(ot, term), _term_count(rt, term)
        if oc != rc:
            f.add("DETECTED_CHANGE", "PROTECTED_TERM_CHANGED", "protected_term",
                  "Protected term '%s' occurs %d time(s) in the original and %d in the revision." % (term, oc, rc),
                  values={"term": term, "original_count": oc, "revised_count": rc}, literal=True, authorizable=False)
    alignment = align_sentences(osent, rsent)
    ocue_by, rcue_by = _group_by_sentence(ocues), _group_by_sentence(rcues)
    oitem_by, ritem_by = _group_by_sentence(oitems), _group_by_sentence(ritems)

    # 1. literal multiset comparison of protected items (document level)
    changed_keys = set()
    onum_by_key = {it["normalized"]: it for it in oitems if it["category"] == "number"}
    rnum_by_key = {it["normalized"]: it for it in ritems if it["category"] == "number"}
    for cat in _LITERAL_CATEGORIES:
        oc = Counter(it["normalized"] for it in oitems if it["category"] == cat)
        rc = Counter(it["normalized"] for it in ritems if it["category"] == cat)
        missing = list((oc - rc).elements())
        added = list((rc - oc).elements())
        changed_keys.update(missing)
        changed_keys.update(added)
        paired = min(len(missing), len(added)) if cat in ("number", "citation", "identifier", "statistic") else 0
        for k in range(paired):
            code = "%s_CHANGED" % cat.upper()
            if cat == "number":
                ov, rv = onum_by_key.get(missing[k], {}), rnum_by_key.get(added[k], {})
                if ov.get("value") == rv.get("value") and ov.get("unit") != rv.get("unit"):
                    code = "UNIT_CHANGED"
            f.add("DETECTED_CHANGE", code, cat,
                  "Protected %s changed from '%s' to '%s'." % (cat, missing[k], added[k]),
                  values={"original": missing[k], "revised": added[k]}, literal=True)
        for v in missing[paired:]:
            f.add("DETECTED_CHANGE", "MISSING_ITEM", cat, "Protected %s '%s' is missing from the revision." % (cat, v),
                  values={"original": v, "revised": ""}, literal=True)
        for v in added[paired:]:
            f.add("DETECTED_CHANGE", "ADDED_ITEM", cat, "New %s '%s' appears in the revision." % (cat, v),
                  values={"original": "", "revised": v}, literal=True)

    # 2. per aligned sentence pair
    target_count = Counter(j for a in alignment if a["confident"] for j in a["revised"])
    rev_to_orig = {}
    for a in alignment:
        for j in (a["revised"] if a["confident"] else []):
            rev_to_orig.setdefault(j, set()).add(a["original"])
        o = osent[a["original"]]
        rtext = " ".join(rsent[j]["text"] for j in a["revised"])
        if a["ambiguous"]:
            f.add("POTENTIAL_CHANGE", "ALIGNMENT_UNCERTAIN", "alignment",
                  "Original sentence could not be aligned confidently; review it manually.",
                  o["text"], rtext or None, a["score"])
        if not a["revised"] or a.get("exact"):
            continue
        oc = _absorb_spelling_fixes(_cues_in(ocue_by, [a["original"]]), rcue_by, a["revised"], o["text"])
        rc = _cues_in(rcue_by, a["revised"])
        _compare_cues(f, oc, rc, o["text"], rtext, a["score"])
        _compare_cue_bindings(f, o["text"], rtext, oc, rc, a["score"])
        _compare_axes(f, o["text"], rtext, a["score"])
        _compare_labels(f, o["text"], rtext, a["score"], one_to_one=len(a["revised"]) == 1 and a["confident"])
        _compare_negation_scope(f, o["text"], rtext, a["score"])
        onums = _items_in(oitem_by, [a["original"]], "number")
        rnums = _items_in(ritem_by, a["revised"], "number")
        exclusive = a["confident"] and all(target_count[j] == 1 for j in a["revised"])
        _compare_numbers(f, onums, rnums, o["text"], rtext, a["score"], changed_keys, exclusive)
        oords = Counter(it["normalized"] for it in _items_in(oitem_by, [a["original"]], "ordinal"))
        rords = Counter(it["normalized"] for it in _items_in(ritem_by, a["revised"], "ordinal"))
        if oords and rords and oords != rords:
            f.add("POTENTIAL_CHANGE", "ORDINAL_CHANGED", "number", "An ordinal (first, second, 1st...) changed.",
                  o["text"], rtext, a["score"])
        if a["confident"] and not a["ambiguous"] and len(a["revised"]) == 1:
            _compare_change_bases(f, o, rsent[a["revised"][0]], onums, rnums, a["score"])
            _compare_direct_roles(f, o["text"], rtext, a["score"])
            if _cues_in(ocue_by, [a["original"]]).get("negation") == rc.get("negation") == ["not"]:
                _compare_reported_negation(f, o["text"], rtext, a["score"])
        flips = _side_flips(o["text"], rtext)
        if flips:
            f.add("POTENTIAL_CHANGE", "ORDER_REVERSED", "relation",
                  "Words moved across a directional/comparative cue; subject and object may be reversed.",
                  o["text"], rtext, a["score"], {"moved_words": ", ".join(flips)})

    # 3. citation position
    orig_cite_pos = {}
    for x in oitems:
        if x["category"] == "citation":
            orig_cite_pos.setdefault(x["normalized"], set()).add(x["sentence_index"])
    for it in ritems:
        if it["category"] != "citation":
            continue
        orig_pos = orig_cite_pos.get(it["normalized"])
        if orig_pos and it["sentence_index"] is not None:
            mapped = rev_to_orig.get(it["sentence_index"], set())
            if mapped and not (mapped & orig_pos):
                f.add("POTENTIAL_CHANGE", "CITATION_MOVED", "citation",
                      "Citation '%s' now sits in a sentence aligned to different original content." % it["text"],
                      None, rsent[it["sentence_index"]]["text"], None, {"citation": it["normalized"]})

    # 4. unaligned revised sentences
    for s in rsent:
        if s["index"] not in rev_to_orig:
            f.add("POTENTIAL_CHANGE", "UNALIGNED_REVISED_SENTENCE", "alignment",
                  "Revised sentence has no aligned original sentence (added or heavily rewritten content).",
                  None, s["text"])

    active = [x for x in f.items if not x["authorized"]]
    if any(x["literal"] for x in active):
        status = "DETERMINISTIC_LITERAL_FAILURE"
    elif active:
        status = "SEMANTIC_RISK_FLAG"
    else:
        status = "NO_FLAG_DETECTED"
    return {
        "status": status,
        "semantic_equivalence_established": False,
        "notice": NO_EQUIVALENCE_NOTICE,
        "summary": {"findings": len(f.items), "active": len(active),
                    "detected_change": sum(1 for x in active if x["kind"] == "DETECTED_CHANGE"),
                    "potential_change": sum(1 for x in active if x["kind"] == "POTENTIAL_CHANGE"),
                    "authorized": len(f.items) - len(active)},
        "findings": f.items,
        "alignment": alignment,
        "original_sha256": sha256_text(ot),
        "revised_sha256": sha256_text(rt),
        "original_sentences": len(osent),
        "revised_sentences": len(rsent),
        "protected_terms_checked": len(protect),
        "warnings": [TRUNCATION_WARNING] if (oitems.truncated or ritems.truncated) else [],
    }


def _hedge_classes(forms):
    out = Counter()
    for form in forms:
        for pattern, cls in _HEDGE_CLASS:
            if pattern.match(form):
                out[cls] += 1
                break
    return out


def _certainty_score(forms):
    return sum(2 if _STRONG_CERTAINTY.match(x) else 1 for x in forms)


def _compare_cues(f, oc, rc, otext, rtext, score):
    on, rn = oc.get("negation", []), rc.get("negation", [])
    if len(on) != len(rn):
        f.add("DETECTED_CHANGE", "NEGATION_COUNT_CHANGED", "negation",
              "Negation cues changed from %d to %d." % (len(on), len(rn)), otext, rtext, score,
              {"original_forms": ", ".join(on), "revised_forms": ", ".join(rn)})
    elif Counter(on) != Counter(rn):
        f.add("POTENTIAL_CHANGE", "NEGATION_FORM_CHANGED", "negation",
              "Negation form changed (for example 'not' to 'no'); the scope of the negation may differ.",
              otext, rtext, score, {"original_forms": ", ".join(on), "revised_forms": ", ".join(rn)})
    oh, rh = _hedge_classes(oc.get("hedge", [])), _hedge_classes(rc.get("hedge", []))
    hv = {"original": ", ".join(oc.get("hedge", [])), "revised": ", ".join(rc.get("hedge", []))}
    if sum(rh.values()) < sum(oh.values()):
        f.add("POTENTIAL_CHANGE", "HEDGE_REMOVED", "uncertainty", "Uncertainty markers were removed.",
              otext, rtext, score, hv)
    elif sum(rh.values()) > sum(oh.values()):
        f.add("POTENTIAL_CHANGE", "HEDGE_ADDED", "uncertainty", "Uncertainty markers were added.",
              otext, rtext, score, hv)
    elif oh != rh:
        f.add("POTENTIAL_CHANGE", "HEDGE_CHANGED", "uncertainty",
              "Uncertainty markers changed strength (for example 'may' to 'likely').", otext, rtext, score, hv)
    if _certainty_score(rc.get("certainty", [])) > _certainty_score(oc.get("certainty", [])):
        f.add("POTENTIAL_CHANGE", "CERTAINTY_INCREASED", "uncertainty", "Certainty markers were strengthened.",
              otext, rtext, score, {"original": ", ".join(oc.get("certainty", [])),
                                    "revised": ", ".join(rc.get("certainty", []))})
    ocond, rcond = Counter(oc.get("condition", [])), Counter(rc.get("condition", []))
    cv = {"original": ", ".join(oc.get("condition", [])), "revised": ", ".join(rc.get("condition", []))}
    if sum(rcond.values()) < sum(ocond.values()):
        f.add("POTENTIAL_CHANGE", "CONDITION_REMOVED", "condition", "Conditional markers were removed.",
              otext, rtext, score, cv)
    elif ocond != rcond:
        f.add("POTENTIAL_CHANGE", "CONDITION_CHANGED", "condition", "Conditional markers changed meaning.",
              otext, rtext, score, cv)
    ocaus, rcaus = len(oc.get("causal", [])), len(rc.get("causal", []))
    oass, rass = len(oc.get("association", [])), len(rc.get("association", []))
    if rcaus > ocaus:
        code = "CAUSAL_STRENGTHENED" if oass else "CAUSAL_ADDED"
        f.add("POTENTIAL_CHANGE", code, "causal", "Causal language was added%s." %
              (" where the original described an association" if oass else ""),
              otext, rtext, score, {"revised": ", ".join(rc.get("causal", []))})
    elif rcaus < ocaus and rass > oass:
        f.add("POTENTIAL_CHANGE", "CAUSAL_WEAKENED", "causal", "Causal language became associational.",
              otext, rtext, score, {"original": ", ".join(oc.get("causal", []))})
    oq = Counter(_QUANT_CLASS.get(x, x) for x in oc.get("quantifier", []))
    rq = Counter(_QUANT_CLASS.get(x, x) for x in rc.get("quantifier", []))
    if oq != rq:
        f.add("POTENTIAL_CHANGE", "QUANTIFIER_CHANGED", "quantifier", "Quantifiers changed.",
              otext, rtext, score, {"original": ", ".join(oc.get("quantifier", [])),
                                    "revised": ", ".join(rc.get("quantifier", []))})
    oqual, rqual = Counter(oc.get("qualifier", [])), Counter(rc.get("qualifier", []))
    missing_q = oqual - rqual
    added_q = Counter({k: v for k, v in (rqual - oqual).items() if k in _QUALIFIER_WATCH})
    if missing_q:
        f.add("POTENTIAL_CHANGE", "QUALIFIER_REMOVED", "qualifier", "Limiting qualifiers were removed.",
              otext, rtext, score, {"removed": ", ".join(missing_q.elements())})
    if added_q:
        f.add("POTENTIAL_CHANGE", "QUALIFIER_ADDED", "qualifier", "Limiting qualifiers were added.",
              otext, rtext, score, {"added": ", ".join(added_q.elements())})
    if rc.get("equivalence") and not oc.get("equivalence") and _NONSIG.search(otext):
        f.add("POTENTIAL_CHANGE", "NONSIGNIFICANCE_AS_EQUIVALENCE", "statistics",
              "A non-significant result may have been restated as equivalence or no effect.",
              otext, rtext, score, {"revised": ", ".join(rc.get("equivalence", []))})


_BINDING_CLASSES = ("negation", "hedge", "certainty", "causal", "association")
_CLAUSE_SPLIT = re.compile(r"[,;:.!?]+(?:\s|$)|\s(?:and|but|while|whereas|although|though|yet)\s|\s[—–-]{1,2}\s",
                           re.IGNORECASE)
_BINDING_STOP = _STOP | {"is", "are", "was", "were", "be", "been", "being", "it", "its", "they", "them", "their",
                         "this", "that", "these", "those", "which", "who", "whom", "there", "here", "has", "have",
                         "had", "do", "does", "did", "also", "than", "as", "so", "such", "into", "onto", "both",
                         "we", "our", "he", "she", "his", "her", "not", "no", "very", "more", "less", "then"}
_CUE_WORDS = {"may", "might", "could", "possibly", "perhaps", "probably", "likely", "unlikely", "potentially",
              "plausibly", "linked", "associated", "related", "correlated", "causes", "cause", "caused",
              "causing", "leads", "lead", "led", "due", "because", "therefore", "results", "result", "resulted",
              "suggests", "suggest", "suggested", "indicates", "indicate", "indicated", "seems", "seem", "appears",
              "appear", "clearly", "proves", "proved", "proven", "shows", "showed", "shown", "never", "cannot",
              "without", "nor", "neither", "none"}


def _stem(tok):
    for suf in ("ing", "ed", "es", "s"):
        if len(tok) > len(suf) + 3 and tok.endswith(suf):
            return tok[: -len(suf)]
    return tok


def _cue_bindings(text):
    """Map each content word to the set of claim-strength cue classes found in the same clause."""
    sentences = split_sentences(text)
    cues = [c for c in find_cues(text, sentences) if c["class"] in _BINDING_CLASSES]
    bounds = [0]
    for m in _CLAUSE_SPLIT.finditer(text):
        bounds.append(m.end())
    bounds.append(len(text) + 1)
    out = {}
    for lo, hi in zip(bounds, bounds[1:]):
        classes = frozenset(c["class"] for c in cues if lo <= c["start"] < hi)
        for tok in _tokens(text[lo:hi]):
            if len(tok) < 3 or tok in _BINDING_STOP or tok in _CUE_WORDS or tok.isdigit():
                continue
            out.setdefault(_stem(tok), set()).update(classes)
    return out


def _compare_cue_bindings(f, otext, rtext, oc, rc, score):
    """Flag a cue that kept its count but moved to a different part of the claim.

    Catches swaps such as 'linked to A and causes B' -> 'causes A and linked to B', and a hedge that
    moves to the other clause when one sentence is split. Count changes are reported elsewhere."""
    classes = [c for c in _BINDING_CLASSES if oc.get(c) and len(oc[c]) == len(rc.get(c, []))]
    if not classes:
        return
    ob, rb = _cue_bindings(otext), _cue_bindings(rtext)
    shared = set(ob) & set(rb)
    for cls in classes:
        lost = sorted(w for w in shared if cls in ob[w] and cls not in rb[w])
        gained = sorted(w for w in shared if cls not in ob[w] and cls in rb[w])
        if lost and gained:
            f.add("POTENTIAL_CHANGE", "CUE_MOVED", "relation",
                  "A '%s' cue kept its count but now applies to different words; the claim it qualifies "
                  "may have changed." % cls, otext, rtext, score,
                  {"cue_class": cls, "no_longer_applies_to": ", ".join(lost[:6]),
                   "now_applies_to": ", ".join(gained[:6])})


def _axis_values(tokens):
    by = {}
    for t in tokens:
        hit = _AXES.get(t)
        if hit:
            by.setdefault(hit[0], Counter())[hit[1]] += 1
    return by


def _compare_axes(f, otext, rtext, score):
    otoks, rtoks = _tokens(otext), _tokens(rtext)
    oa, ra = _axis_values(otoks), _axis_values(rtoks)
    for axis in sorted(set(oa) & set(ra)):
        o, r = oa[axis], ra[axis]
        if o == r:
            continue
        reversal = bool(set(o) - set(r)) and bool(set(r) - set(o))
        swapped_counts = sum(o.values()) == sum(r.values())
        if reversal or swapped_counts:
            code = "DIRECTION_REVERSED" if axis == "amount" else "POLARITY_OR_DIRECTION_CHANGED"
            f.add("POTENTIAL_CHANGE", code, "direction",
                  "Directional or polar wording changed on the '%s' axis." % axis, otext, rtext, score,
                  {"axis": axis, "original": ", ".join(sorted(o.elements())),
                   "revised": ", ".join(sorted(r.elements()))})
    oset, rset = set(otoks), set(rtoks)
    flips = []
    for a, b in ((rset - oset, oset), (oset - rset, rset)):
        for w in a:
            for p in _POLARITY_PREFIXES:
                base = w[len(p):]
                if w.startswith(p) and len(base) >= 4 and base in b:
                    flips.append("%s/%s" % (base, w))
                    break
    if flips:
        f.add("POTENTIAL_CHANGE", "POLARITY_OR_DIRECTION_CHANGED", "direction",
              "A word gained or lost a negating prefix (for example reliable/unreliable).", otext, rtext, score,
              {"pairs": ", ".join(sorted(flips))})


def _label_map(text):
    found = list(_LABEL_RE.finditer(text))
    out = []
    for k, m in enumerate(found):
        end = found[k + 1].start() if k + 1 < len(found) else len(text)
        words = [t for t in _tokens(text[m.end():end]) if t not in _STOP and t not in _LABEL_NOUNS
                 and t not in ("was", "were", "is", "are", "had", "has", "have")][:3]
        out.append((m.group(1), tuple(words)))
    return out


def _compare_labels(f, otext, rtext, score, one_to_one):
    o, r = _label_map(otext), _label_map(rtext)
    if not o or not r:
        return
    ol, rl = Counter(x[0] for x in o), Counter(x[0] for x in r)
    if len(o) >= 2 and ol == rl and Counter(x[1] for x in o) == Counter(x[1] for x in r) \
            and dict(o) != dict(r) and len(dict(o)) == len(o):
        f.add("POTENTIAL_CHANGE", "LABEL_ROLES_SWAPPED", "relation",
              "Labelled groups exchanged what is said about them. Check which group did what.",
              otext, rtext, score, {"original": "; ".join("%s: %s" % (a, " ".join(b)) for a, b in o),
                                    "revised": "; ".join("%s: %s" % (a, " ".join(b)) for a, b in r)})
    elif one_to_one and set(ol) != set(rl):
        f.add("POTENTIAL_CHANGE", "LABEL_CHANGED", "relation", "A group or item label changed.",
              otext, rtext, score, {"original": ", ".join(sorted(ol)), "revised": ", ".join(sorted(rl))})


_NOT_ALL = re.compile(r"\bnot (?:all|every|each|always)\b", re.IGNORECASE)
_ALL_NOT = re.compile(r"\b(?:all|every|each|always)\b[^.;]{0,80}?\b(?:not|\w+n't|never)\b", re.IGNORECASE)


def _compare_negation_scope(f, otext, rtext, score):
    o_na, r_na = bool(_NOT_ALL.search(otext)), bool(_NOT_ALL.search(rtext))
    o_an, r_an = bool(_ALL_NOT.search(otext)) and not o_na, bool(_ALL_NOT.search(rtext)) and not r_na
    if (o_na and r_an and not r_na) or (o_an and r_na and not o_na):
        f.add("POTENTIAL_CHANGE", "NEGATION_SCOPE_CHANGED", "negation",
              "Negation moved relative to a quantifier ('not all' versus 'all ... not').", otext, rtext, score)


def _compare_numbers(f, onums, rnums, otext, rtext, score, doc_changed, confident):
    rby = {}
    for it in rnums:
        rby.setdefault(it["normalized"], []).append(it)
    for it in onums:
        cands = rby.get(it["normalized"])
        if not cands:
            continue
        r = cands.pop(0)
        if it.get("role_word") and r.get("role_word") and it["role_word"] != r["role_word"]:
            f.add("POTENTIAL_CHANGE", "NUMBER_ROLE_CHANGED", "number",
                  "Number %s is now attached to '%s' instead of '%s'." % (it["text"], r["role_word"], it["role_word"]),
                  otext, rtext, score, {"number": it["normalized"], "original_role": it["role_word"],
                                        "revised_role": r["role_word"]})
    if confident:
        oc = Counter(it["normalized"] for it in onums)
        rc = Counter(it["normalized"] for it in rnums)
        moved = [k for k in (set(oc) ^ set(rc)) if k not in doc_changed]
        if moved:
            f.add("POTENTIAL_CHANGE", "NUMBER_MOVED", "number",
                  "Numbers moved between sentences; check that each number still belongs to the right item.",
                  otext, rtext, score, {"numbers": ", ".join(sorted(moved))})


_CHANGE_BASIS_PREFIX = re.compile(
    r"\b(?:fall(?:s|en)?|fell|ris(?:e|es|en)|rose|drop(?:s|ped)?|"
    r"(?:decreas|increas|declin|reduc)(?:e|es|ed)|climb(?:s|ed)?)"
    r"\s{1,8}(by|to)\s{1,8}\Z",
    re.IGNORECASE,
)


def _change_bases(sentence, numbers):
    counts = Counter(item["normalized"] for item in numbers)
    bases = {}
    for item in numbers:
        value = item["normalized"]
        if counts[value] != 1:
            continue
        start = item["start"] - sentence["start"]
        prefix = sentence["text"][max(0, start - 48):start]
        match = _CHANGE_BASIS_PREFIX.search(prefix)
        if match:
            bases[value] = match.group(1).lower()
    return bases


def _compare_change_bases(f, original, revised, onums, rnums, score):
    before = _change_bases(original, onums)
    after = _change_bases(revised, rnums)
    for value, old_basis in before.items():
        if value in after and after[value] != old_basis:
            f.add("POTENTIAL_CHANGE", "QUANTITY_CHANGE_BASIS", "number",
                  "Check %s: 'by' gives the amount of change and 'to' gives the final value." % value,
                  original["text"], revised["text"], score,
                  {"number": value, "original_basis": old_basis, "revised_basis": after[value]})


_REPORTING_PAST = {
    "confirm": "confirmed", "establish": "established", "show": "showed",
    "find": "found", "conclude": "concluded", "demonstrate": "demonstrated",
    "determine": "determined", "verify": "verified", "report": "reported",
}


def _reported_negation(text):
    """Return a comparison key and the clause negated by a simple 'not'."""
    words = _tokens(text.replace("’", "'"))
    if words.count("that") != 1:
        return None
    split = words.index("that")
    head, claim = words[:split], words[split + 1:]
    if not head or not claim:
        return None
    verb = head[-1]
    if head[-3:-1] == ["did", "not"] and len(head) > 3 and verb in _REPORTING_PAST:
        return (head[:-3] + [_REPORTING_PAST[verb]], claim), "reporting clause"
    if head[-2:-1] == ["didn't"] and len(head) > 2 and verb in _REPORTING_PAST:
        return (head[:-2] + [_REPORTING_PAST[verb]], claim), "reporting clause"
    if len(head) < 2 or verb not in _REPORTING_PAST.values() or claim.count("not") != 1:
        return None
    pos = claim.index("not")
    if (pos < 2 or pos + 1 == len(claim) or claim[pos - 1] not in {"was", "were", "is", "are"}
            or claim[pos + 1] in {"only", "just", "merely"}):
        return None
    return (head, claim[:pos] + claim[pos + 1:]), "reported claim"


def _compare_reported_negation(f, original, revised, score):
    before = _reported_negation(original)
    after = _reported_negation(revised)
    if before and after and before[0] == after[0] and before[1] != after[1]:
        f.add("POTENTIAL_CHANGE", "REPORTED_NEGATION_SCOPE_CHANGED", "negation",
              "Negation moved between the reporting verb and the reported claim. Check which statement is denied.",
              original, revised, score, {"original_scope": before[1], "revised_scope": after[1]})


_PARTICIPANT = r"(?:the\s{{1,8}})?(?P<{}>[^\W\d_][\w'’-]{{0,39}})"
_DIRECT_ROLE_CLAUSE = re.compile(
    _PARTICIPANT.format("subject")
    + r"\s{1,8}(?P<verb>notified|informed|warned|advised|interviewed|trained|supervised|evaluated|briefed)"
    + r"\s{1,8}" + _PARTICIPANT.format("object") + r"[.!?]?\Z",
    re.IGNORECASE,
)


def _compare_direct_roles(f, original, revised, score):
    before = _DIRECT_ROLE_CLAUSE.fullmatch(original)
    after = _DIRECT_ROLE_CLAUSE.fullmatch(revised)
    if not before or not after:
        return
    subject, verb, recipient = (x.casefold() for x in before.groups())
    other_subject, other_verb, other_recipient = (x.casefold() for x in after.groups())
    if subject != recipient and (other_subject, other_verb, other_recipient) == (recipient, verb, subject):
        f.add("POTENTIAL_CHANGE", "PARTICIPANT_ROLES_SWAPPED", "relation",
              "The two participants exchanged subject and object roles. Check who did what.",
              original, revised, score, {"original_subject": subject, "revised_subject": other_subject,
                                         "verb": verb})


COMPARE_LIMITATIONS = [
    ITEM_LIMITATION,
    "Alignment uses token overlap; heavy restructuring is reported as ALIGNMENT_UNCERTAIN or UNALIGNED "
    "rather than approved.",
    "Triggers are review prompts, not verdicts; synonyms, reorderings and clause splits without cue words "
    "can change meaning undetected (for example a hedge moved into a different clause of a split sentence).",
    "Cue and direction lists are English only.",
]


# --------------------------------------------------------------------- originality

_QUOTE_SPAN = re.compile(r"“[^”]{0,2000}”|\"[^\"]{0,2000}\"")


def _word_positions(text):
    return [(m.group(0).lower().replace("’", "'"), m.start(), m.end()) for m in _TOKEN.finditer(text)]


def originality(source, text, n=6, span_flag=12, ratio_flag=0.15):
    src = _word_positions(normalize_newlines(source))
    txt_norm = normalize_newlines(text)
    txt = _word_positions(txt_norm)
    quoted = [False] * len(txt)
    qspans = [(m.start(), m.end()) for m in _QUOTE_SPAN.finditer(txt_norm)]
    if qspans:
        qstarts = [a for a, _ in qspans]
        for i, (_, s, _e) in enumerate(txt):
            k = bisect_right(qstarts, s) - 1
            quoted[i] = k >= 0 and s < qspans[k][1]
    grams = set()
    sw = [w for w, _, _ in src]
    for i in range(len(sw) - n + 1):
        grams.add(tuple(sw[i:i + n]))
    tw = [w for w, _, _ in txt]
    shared = [False] * len(tw)
    for i in range(len(tw) - n + 1):
        if tuple(tw[i:i + n]) in grams:
            for j in range(i, i + n):
                shared[j] = True
    spans, quoted_spans = [], []
    i = 0
    while i < len(tw):
        if not shared[i]:
            i += 1
            continue
        j = i
        while j < len(tw) and shared[j] and quoted[j] == quoted[i]:
            j += 1
        s, e = txt[i][1], txt[j - 1][2]
        entry = {"words": j - i, "start": s, "end": e, "text": txt_norm[s:e][:300]}
        (quoted_spans if quoted[i] else spans).append(entry)
        i = j
    unquoted_total = sum(1 for q in quoted if not q)
    shared_unquoted = sum(1 for k in range(len(tw)) if shared[k] and not quoted[k])
    ratio = round(shared_unquoted / float(unquoted_total), 3) if unquoted_total else 0.0
    longest = max((sp["words"] for sp in spans), default=0)
    reordered, lcs_words = _reordered_sentences(normalize_newlines(source), txt_norm, txt, quoted)
    flagged = longest >= span_flag or ratio >= ratio_flag or bool(reordered)
    spans.sort(key=lambda sp: -sp["words"])
    return {
        "status": "CLOSE_PARAPHRASE_FLAG" if flagged else "NO_CLOSE_COPY_DETECTED",
        "n": n,
        "thresholds": {"longest_span_words": span_flag, "shared_ngram_ratio": ratio_flag,
                       "reordered_sentence_dice": REORDER_DICE, "reordered_min_content_words": REORDER_MIN_WORDS},
        "source_words": len(src),
        "text_words": len(txt),
        "longest_span_words": longest,
        "shared_ngram_ratio": ratio,
        "reordered_close_sentences": reordered[:200],
        "lcs_words": lcs_words,
        "spans": spans[:200],
        "quoted_spans": quoted_spans[:200],
        "limitations": ["Detects word-for-word overlap and sentences that reuse the same content words in a "
                        "different order; copying that swaps in synonyms is missed.",
                        "Text inside double quotation marks is reported separately as quoted and is not "
                        "counted toward the flag; check that each quotation is cited.",
                        "The content-word stop list is English only."],
    }


REORDER_DICE = 0.8
REORDER_MIN_WORDS = 8
_CONTENT_STOP = set("""a an the and or but nor so yet for of in on at to from by with without into onto over under
about above below between among through during before after as than then that this these those there here
is are was were be been being am do does did done have has had having it its it's they them their theirs we us
our you your he him his she her i me my which who whom whose what when where why how not no also very too
can could may might will would shall should must just only more most less such each other some any all both
either neither one ones s t""".split())
_LCS_CAP = 150


def _content_words(text):
    return [t for t in _tokens(text) if t not in _CONTENT_STOP]


def _lcs_len(a, b):
    a, b = a[:_LCS_CAP], b[:_LCS_CAP]
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def _reordered_sentences(source, txt_norm, txt_words, quoted):
    """Text sentences whose content words closely match one source sentence in any order (Dice on
    content-word multisets), plus the longest common subsequence of content words over best pairs."""
    ssent = split_sentences(source)
    scont = [_content_words(s["text"]) for s in ssent]
    scnt = [Counter(c) for c in scont]
    index = {}
    for k, c in enumerate(scont):
        for w in set(c):
            index.setdefault(w, []).append(k)
    common = {w for w, ks in index.items() if len(ks) > 200}
    wstarts = [s for _, s, _ in txt_words]
    reordered, lcs_best = [], 0
    for t in split_sentences(txt_norm):
        lo, hi = bisect_right(wstarts, t["start"] - 1), bisect_right(wstarts, t["end"] - 1)
        if hi > lo and sum(quoted[lo:hi]) * 2 >= hi - lo:
            continue
        cont = _content_words(t["text"])
        if not cont:
            continue
        votes = Counter()
        for w in set(cont):
            if w not in common:
                for k in index.get(w, ()):
                    votes[k] += 1
        if not votes:
            continue
        tc = Counter(cont)
        best_k, best_d = None, 0.0
        for k, _ in votes.most_common(10):
            d = _dice(tc, scnt[k], len(cont), len(scont[k]))
            if d > best_d:
                best_k, best_d = k, d
        if best_d >= 0.5:
            lcs_best = max(lcs_best, _lcs_len(cont, scont[best_k]))
        if best_d >= REORDER_DICE and len(cont) >= REORDER_MIN_WORDS:
            reordered.append({"text_sentence_index": t["index"], "source_sentence_index": best_k,
                              "dice": round(best_d, 3), "content_words": len(cont),
                              "text": t["text"][:300], "source": ssent[best_k]["text"][:300]})
    reordered.sort(key=lambda r: -r["dice"])
    return reordered, lcs_best


# ----------------------------------------------------------------------------- CLI

class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def _positive_int(v):
    try:
        n = int(v)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer")
    if n < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return n


def _exclusions(v):
    kinds = [k.strip() for k in v.split(",") if k.strip()]
    bad = [k for k in kinds if k not in EXCLUSION_KINDS]
    if bad:
        raise argparse.ArgumentTypeError("unknown exclusion(s): %s" % ", ".join(bad))
    return kinds


def build_parser():
    p = _Parser(prog="mdh_text.py", description="MdH deterministic verification helper (JSON output).")
    p.add_argument("--version", action="version", version="%s %s" % (TOOL, VERSION))
    sub = p.add_subparsers(dest="command")

    def add_common_count(sp):
        sp.add_argument("--file", "-f", required=True, help="UTF-8 text file, or '-' to read stdin explicitly")
        sp.add_argument("--convention", choices=CONVENTIONS, default="word2019_approx")
        sp.add_argument("--exclude", type=_exclusions, default=[],
                        help="comma list: " + ",".join(EXCLUSION_KINDS))
        sp.add_argument("--section", action="append", default=[], help="count only this Markdown section (repeatable)")
        sp.add_argument("--keep-markdown", action="store_true", help="count Markdown syntax as written")
        sp.add_argument("--strip-markdown", action="store_true", help=argparse.SUPPRESS)
        sp.add_argument("--all", action="store_true", help="also report every convention")
        sp.add_argument("--max-bytes", type=_positive_int, default=DEFAULT_MAX_BYTES)

    add_common_count(sub.add_parser("count", help="count words"))
    b = sub.add_parser("budget", help="check a word constraint")
    add_common_count(b)
    b.add_argument("--type", required=True, choices=("exact", "max", "min", "range", "approx"))
    b.add_argument("--target", type=_positive_int)
    b.add_argument("--min", dest="lo", type=_positive_int)
    b.add_argument("--max", dest="hi", type=_positive_int)
    b.add_argument("--tolerance-pct", type=float, default=10.0)
    b.add_argument("--count-mode", choices=("words", "cjk_chars_with_punct"), default="words",
                   help="check the limit against words (default) or against Chinese/Japanese/Korean characters "
                        "including CJK punctuation (the usual convention for character limits)")
    inv = sub.add_parser("inventory", help="list protected items and meaning cues")
    inv.add_argument("--file", "-f", required=True)
    inv.add_argument("--max-bytes", type=_positive_int, default=DEFAULT_MAX_BYTES)
    c = sub.add_parser("compare", help="compare original and revised text")
    c.add_argument("--original", required=True, help="file or '-' for stdin")
    c.add_argument("--revised", required=True, help="file or '-' for stdin (only one side may use stdin)")
    c.add_argument("--authorized", help="JSON file: {\"authorized\": [{\"from\": \"...\", \"to\": \"...\"}]}")
    c.add_argument("--protect", help="text file with one protected term per line (exact, case-sensitive)")
    c.add_argument("--max-bytes", type=_positive_int, default=DEFAULT_MAX_BYTES)
    o = sub.add_parser("originality", help="find long word sequences shared with a source")
    o.add_argument("--source", required=True, help="source file or '-' for stdin")
    o.add_argument("--text", required=True, help="text file to check or '-' for stdin (only one side may use stdin)")
    o.add_argument("--n", type=_positive_int, default=6, help="n-gram length (3-20, default 6)")
    o.add_argument("--max-bytes", type=_positive_int, default=DEFAULT_MAX_BYTES)
    return p


def _envelope(command, extra):
    out = {"tool": TOOL, "version": VERSION, "command": command}
    out.update(extra)
    return out


def _check_max(n):
    if n <= 0 or n > HARD_MAX_BYTES:
        raise UsageError("--max-bytes must be between 1 and %d" % HARD_MAX_BYTES)


def _load_authorized(path, max_bytes):
    if not path:
        return []
    _, text, _ = read_input(path, max_bytes, JSON_EXTENSIONS)
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise InputError("authorized-changes file is not valid JSON: %s" % exc)
    entries = data.get("authorized") if isinstance(data, dict) else None
    shape = "authorized-changes file must be {\"authorized\": [{\"from\": \"...\", \"to\": \"...\"}, ...]}"
    if not isinstance(entries, list):
        raise InputError(shape)
    pairs = []
    for e in entries:
        if not isinstance(e, dict) or set(e) != {"from", "to"} or not all(isinstance(e[k], str) for k in e):
            raise InputError(shape)
        a, b = e["from"], e["to"]
        for v in (a, b):
            if v and not v.strip():
                raise InputError("authorized-changes entries must not be blank or whitespace-only")
        if not a.strip() and not b.strip():
            raise InputError("authorized-changes entries need a non-empty 'from' or 'to'")
        if a.strip() == b.strip():
            raise InputError("authorized-changes entry has identical 'from' and 'to': %s" % a)
        pairs.append((a, b))
    return pairs


def run(argv):
    """Execute the CLI. Returns (exit_code, result_dict)."""
    args = build_parser().parse_args(argv)
    if not args.command:
        raise UsageError("a command is required: " + ", ".join(COMMANDS))
    _check_max(args.max_bytes)
    if args.command in ("count", "budget"):
        if args.command == "budget":
            if args.type == "range":
                if args.lo is None or args.hi is None or args.lo > args.hi:
                    raise UsageError("--type range needs --min <= --max")
                if args.target is not None:
                    raise UsageError("--type range takes --min and --max, not --target")
            else:
                if args.target is None:
                    raise UsageError("--target is required for --type %s" % args.type)
                if args.lo is not None or args.hi is not None:
                    raise UsageError("--min/--max apply only to --type range")
            if args.type == "approx" and not (0 <= args.tolerance_pct < 100):
                raise UsageError("--tolerance-pct must be in [0, 100)")
        raw, text, read_warnings = read_input(args.file, args.max_bytes)
        m = measure(text, args.convention, args.exclude, args.section, not args.keep_markdown, args.all)
        base = {"input_sha256": sha256_bytes(raw), "measurement": "helper count of the exact text it received"}
        base.update(m)
        base["warnings"] = read_warnings + m["warnings"] + [
            "requested section not found: %s" % s["name"] for s in m["sections"] if not s["found"]]
        base["limitations"] = COUNT_LIMITATIONS
        if args.command == "count":
            return EXIT_OK, _envelope("count", base)
        base["count_mode"] = args.count_mode
        if args.count_mode == "cjk_chars_with_punct":
            measured = m.get("cjk_characters_with_punctuation", 0)
            base["count_words"] = m["count"]
            base["count"] = measured
            empty_msg = "no Chinese, Japanese or Korean characters counted"
        else:
            measured = m["count"]
            empty_msg = "no words counted"
        not_run = any(not s["found"] for s in m["sections"]) or measured == 0
        if measured == 0:
            base["warnings"].append(empty_msg)
        if not_run:
            base.update({"status": "FAIL", "verification_state": "NOT_RUN", "delta": None,
                         "constraint": {"type": args.type}})
            return EXIT_FINDING, _envelope("budget", base)
        status, delta, constraint = evaluate_constraint(measured, args.type, args.target, args.lo, args.hi,
                                                        args.tolerance_pct)
        base.update({"constraint": constraint, "status": status, "delta": delta,
                     "verification_state": "VERIFIED" if status == "PASS" else "FAILED"})
        return (EXIT_OK if status == "PASS" else EXIT_FINDING), _envelope("budget", base)
    if args.command == "inventory":
        raw, text, read_warnings = read_input(args.file, args.max_bytes)
        norm, sentences, items, cues = build_inventory(text)
        return EXIT_OK, _envelope("inventory", {
            "input_sha256": sha256_bytes(raw), "text_sha256": sha256_text(norm),
            "warnings": read_warnings + ([TRUNCATION_WARNING] if items.truncated else []),
            "counts": dict(Counter(it["category"] for it in items)),
            "cue_counts": dict(Counter(c["class"] for c in cues)),
            "items": items, "cues": cues, "sentences": sentences,
            "repeated_openers": repeated_openers(sentences),
            "limitations": [ITEM_LIMITATION, "Cue lists are closed English word lists; they mark words, "
                            "not meanings.", "Sentence splitting is heuristic."]})
    if args.command == "compare":
        if args.original == "-" and args.revised == "-":
            raise UsageError("only one of --original/--revised may read stdin")
        authorized = _load_authorized(args.authorized, args.max_bytes)
        _, otext, w1 = read_input(args.original, args.max_bytes)
        _, rtext, w2 = read_input(args.revised, args.max_bytes)
        protect = []
        if args.protect:
            _, ptext, _ = read_input(args.protect, args.max_bytes)
            for line in normalize_newlines(ptext).split("\n"):
                term = line.strip()
                if term and term not in protect:
                    protect.append(term)
        res = compare_texts(otext, rtext, authorized, protect)
        res["warnings"] = w1 + w2 + res["warnings"]
        res["limitations"] = COMPARE_LIMITATIONS
        return (EXIT_OK if res["status"] == "NO_FLAG_DETECTED" else EXIT_FINDING), _envelope("compare", res)
    if args.command == "originality":
        if args.source == "-" and args.text == "-":
            raise UsageError("only one of --source/--text may read stdin")
        if not 3 <= args.n <= 20:
            raise UsageError("--n must be between 3 and 20")
        _, stext, w1 = read_input(args.source, args.max_bytes)
        _, ttext, w2 = read_input(args.text, args.max_bytes)
        res = originality(stext, ttext, args.n)
        res["warnings"] = w1 + w2
        return (EXIT_OK if res["status"] == "NO_CLOSE_COPY_DETECTED" else EXIT_FINDING), _envelope("originality", res)
    raise UsageError("unknown command")


def _guess_command(argv):
    return next((a for a in argv if a in COMMANDS), None)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    command = _guess_command(argv)
    try:
        code, result = run(argv)
    except UsageError as exc:
        code, result = EXIT_USAGE, _envelope(command, {"error": {"type": "USAGE_ERROR", "message": str(exc)}})
    except InputError as exc:
        code, result = EXIT_INPUT, _envelope(command, {"error": {"type": "INPUT_ERROR", "message": str(exc)}})
    except RecursionError:
        code, result = EXIT_INTERNAL, _envelope(command, {"error": {"type": "INTERNAL_ERROR",
                                                                    "message": "recursion limit"}})
    except Exception as exc:  # last resort: never crash without a JSON error
        code, result = EXIT_INTERNAL, _envelope(command, {"error": {"type": "INTERNAL_ERROR",
                                                                    "message": exc.__class__.__name__}})
    out = json.dumps(result, ensure_ascii=False, indent=1)
    sys.stdout.buffer.write(out.encode("utf-8") + b"\n")
    sys.stdout.flush()
    return code


if __name__ == "__main__":
    sys.exit(main())
