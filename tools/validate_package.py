#!/usr/bin/env python3
"""Package validator for the mdh-advanced-humanizer skill.

Checks the skill folder for release problems and prints a JSON report.
Standard library only; runs on Windows, macOS and Linux with Python 3.8+.

Usage:
    python3 tools/validate_package.py [SKILL_ROOT]
    py -I tools/validate_package.py "C:\\path\\to\\skill"

SKILL_ROOT defaults to the parent folder of this script's folder.
Exit codes: 0 all checks passed, 1 one or more checks failed, 2 usage error.

Copyright (c) 2026 Md.Hashim. MIT License.
"""
import json
import os
import re
import sys

NAME_MAX = 64
DESCRIPTION_MAX = 1024
PORTABLE_MAX_CHARS = 8000
SKILL_BODY_MAX_WORDS = 1800

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
REF_MENTION_RE = re.compile(r"(?<![\w/.-])references/[A-Za-z0-9_.-]+\.md\b")
VERSION_CONST_RE = re.compile(r"^VERSION\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)
CHANGELOG_ENTRY_RE = re.compile(r"^##\s+\[?v?(\d+\.\d+\.\d+[0-9A-Za-z.+-]*)\]?", re.MULTILINE)

DEV_MARKERS = [
    r"planning:start",
    r"Phase 3A",
    r"\bD-\d{2}\b",
    r"being tested",
    r"VERIFIED_DRAFT",
    r"IN_SESSION_VERIFIED",
    r"mdh-status",
]
TEXT_EXTENSIONS = {".md", ".py", ".json", ".yml", ".yaml", ".txt", ".toml", ".cfg"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "workspace"}


def read_text(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        return fh.read()


def split_frontmatter(text):
    """Return (frontmatter_text, body_text) or (None, text) if absent."""
    lines = text.splitlines(True)
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[1:i]), "".join(lines[i + 1:])
    return None, text


def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        if value[0] == "'":
            return inner.replace("''", "'")
        return inner.replace('\\"', '"')
    return value


def parse_frontmatter(fm):
    """Parse the small YAML subset used in SKILL.md frontmatter.

    Supports top-level scalars, block scalars (| and >) and one level of
    nested mappings (such as metadata.version). Returns a dict.
    """
    result = {}
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[0] in " \t":
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).rstrip()
        i += 1
        if rest in ("|", ">", "|-", ">-", "|+", ">+"):
            block = []
            while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
                block.append(lines[i].strip())
                i += 1
            if rest.startswith("|"):
                result[key] = "\n".join(block).strip()
            else:
                result[key] = " ".join(b for b in block if b).strip()
        elif rest == "":
            nested = {}
            while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
                nm = re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
                if nm:
                    nested[nm.group(1)] = _unquote(nm.group(2))
                i += 1
            result[key] = nested
        else:
            result[key] = _unquote(rest)
    return result


class Report(object):
    def __init__(self, root):
        self.root = root
        self.checks = []

    def add(self, name, ok, details=None):
        entry = {"check": name, "ok": bool(ok)}
        if details:
            entry["details"] = details
        self.checks.append(entry)

    def to_dict(self):
        failed = [c["check"] for c in self.checks if not c["ok"]]
        return {
            "tool": "validate_package.py",
            "skill_root": self.root,
            "ok": not failed,
            "passed": len(self.checks) - len(failed),
            "failed": len(failed),
            "failed_checks": failed,
            "checks": self.checks,
        }


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def check_frontmatter(root, report):
    path = os.path.join(root, "SKILL.md")
    if not os.path.isfile(path):
        report.add("skill_md_exists", False, ["SKILL.md not found"])
        return None, None
    report.add("skill_md_exists", True)
    text = read_text(path)
    fm, body = split_frontmatter(text)
    if fm is None:
        report.add("frontmatter_present", False, ["SKILL.md has no '---' frontmatter block"])
        return None, body
    report.add("frontmatter_present", True)
    data = parse_frontmatter(fm)

    name = data.get("name", "")
    problems = []
    if not isinstance(name, str) or not name:
        problems.append("name is missing")
    else:
        if len(name) > NAME_MAX:
            problems.append("name is %d characters (max %d)" % (len(name), NAME_MAX))
        if not NAME_RE.match(name):
            problems.append("name %r is not lowercase letters, digits and single hyphens" % name)
    report.add("frontmatter_name", not problems, problems or ["name=%s" % name])

    desc = data.get("description", "")
    problems = []
    if not isinstance(desc, str) or not desc.strip():
        problems.append("description is missing")
    elif len(desc) > DESCRIPTION_MAX:
        problems.append("description is %d characters (max %d)" % (len(desc), DESCRIPTION_MAX))
    report.add("frontmatter_description", not problems,
               problems or ["%d characters" % len(desc)])

    lic = data.get("license", "")
    report.add("frontmatter_license", isinstance(lic, str) and bool(lic.strip()),
               None if lic else ["license is missing"])

    meta = data.get("metadata", {})
    version = meta.get("version") if isinstance(meta, dict) else None
    if not version:
        report.add("frontmatter_version_semver", False, ["metadata.version is missing"])
    elif not SEMVER_RE.match(version):
        report.add("frontmatter_version_semver", False, ["%r is not semantic versioning" % version])
    else:
        report.add("frontmatter_version_semver", True, ["version=%s" % version])
    return version, body


def collect_versions(root, skill_version):
    found = {"SKILL.md metadata.version": skill_version}

    script = os.path.join(root, "scripts", "mdh_text.py")
    if os.path.isfile(script):
        m = VERSION_CONST_RE.search(read_text(script))
        found["scripts/mdh_text.py VERSION"] = m.group(1) if m else None
    else:
        found["scripts/mdh_text.py VERSION"] = None

    for manifest in (".claude-plugin/plugin.json", ".cursor-plugin/plugin.json"):
        path = os.path.join(root, *manifest.split("/"))
        value = None
        if os.path.isfile(path):
            try:
                value = json.loads(read_text(path)).get("version")
            except (ValueError, AttributeError):
                value = "<invalid JSON>"
        found[manifest + " version"] = value

    changelog = os.path.join(root, "CHANGELOG.md")
    value = None
    if os.path.isfile(changelog):
        m = CHANGELOG_ENTRY_RE.search(read_text(changelog))
        value = m.group(1) if m else None
    found["CHANGELOG.md top entry"] = value
    return found


def check_versions(root, skill_version, report):
    found = collect_versions(root, skill_version)
    missing = ["%s: not found" % k for k, v in found.items() if not v]
    distinct = sorted(set(v for v in found.values() if v))
    details = ["%s = %s" % (k, v) for k, v in found.items()]
    ok = not missing and len(distinct) == 1
    if missing:
        details = missing + details
    if len(distinct) > 1:
        details.insert(0, "versions differ: %s" % ", ".join(distinct))
    report.add("version_consistency", ok, details)


def markdown_files(root):
    files = []
    for name in ("SKILL.md", "PORTABLE.md"):
        path = os.path.join(root, name)
        if os.path.isfile(path):
            files.append(path)
    ref_dir = os.path.join(root, "references")
    if os.path.isdir(ref_dir):
        for dirpath, dirnames, filenames in os.walk(ref_dir):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for fn in sorted(filenames):
                if fn.lower().endswith(".md"):
                    files.append(os.path.join(dirpath, fn))
    return files


def strip_code_blocks(text):
    """Remove fenced code blocks so example links inside them are not checked."""
    return re.sub(r"^(```|~~~).*?^\1[^\n]*$", "", text, flags=re.MULTILINE | re.DOTALL)


def check_links(root, report):
    broken = []
    checked = 0
    for path in markdown_files(root):
        text = strip_code_blocks(read_text(path))
        base = os.path.dirname(path)
        for m in MD_LINK_RE.finditer(text):
            target = m.group(1)
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = target.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            checked += 1
            resolved = os.path.normpath(os.path.join(base, target))
            if not os.path.exists(resolved):
                broken.append("%s: link '%s' does not resolve" % (rel(root, path), m.group(1)))
        for m in REF_MENTION_RE.finditer(read_text(path)):
            checked += 1
            resolved = os.path.join(root, *m.group(0).split("/"))
            if not os.path.isfile(resolved):
                broken.append("%s: mention '%s' does not resolve" % (rel(root, path), m.group(0)))
    details = sorted(set(broken)) or ["%d links and mentions checked" % checked]
    report.add("links_resolve", not broken, details)


def check_sizes(root, body, report):
    portable = os.path.join(root, "PORTABLE.md")
    if os.path.isfile(portable):
        n = len(read_text(portable))
        report.add("portable_md_size", n <= PORTABLE_MAX_CHARS,
                   ["%d characters (max %d)" % (n, PORTABLE_MAX_CHARS)])
    else:
        report.add("portable_md_size", False, ["PORTABLE.md not found"])

    if body is not None:
        words = len(body.split())
        report.add("skill_body_words", words <= SKILL_BODY_MAX_WORDS,
                   ["%d words (max %d)" % (words, SKILL_BODY_MAX_WORDS)])


def iter_package_text_files(root):
    """Yield shipped text files. Test folders are skipped because test inputs
    may contain marker strings on purpose (for example an HTML comment that
    must not be counted)."""
    this_file = os.path.normcase(os.path.abspath(__file__))
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and d != "tests" and not d.startswith("workspace"))
        for fn in sorted(filenames):
            path = os.path.join(dirpath, fn)
            if os.path.normcase(os.path.abspath(path)) == this_file:
                continue
            if os.path.splitext(fn)[1].lower() in TEXT_EXTENSIONS or fn in ("LICENSE", ".gitignore"):
                yield path


def check_dev_markers(root, report):
    patterns = [(p, re.compile(p)) for p in DEV_MARKERS]
    hits = []
    for path in iter_package_text_files(root):
        try:
            text = read_text(path)
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for raw, rx in patterns:
                if rx.search(line):
                    hits.append("%s:%d matches /%s/" % (rel(root, path), lineno, raw))
    report.add("no_dev_markers", not hits, hits or ["no development markers found"])


def check_license(root, report):
    path = os.path.join(root, "LICENSE")
    ok = os.path.isfile(path) and bool(read_text(path).strip())
    report.add("license_file", ok, None if ok else ["LICENSE missing or empty"])


def validate(root):
    report = Report(root)
    version, body = check_frontmatter(root, report)
    check_versions(root, version, report)
    check_links(root, report)
    check_sizes(root, body, report)
    check_dev_markers(root, report)
    check_license(root, report)
    return report


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) > 1 or (argv and argv[0] in ("-h", "--help")):
        sys.stderr.write("usage: validate_package.py [SKILL_ROOT]\n")
        return 2 if len(argv) > 1 else 0
    if argv:
        root = os.path.abspath(argv[0])
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(root):
        sys.stderr.write("not a directory: %s\n" % root)
        return 2
    report = validate(root).to_dict()
    out = json.dumps(report, indent=2, ensure_ascii=False)
    try:
        sys.stdout.write(out + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=True) + "\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
