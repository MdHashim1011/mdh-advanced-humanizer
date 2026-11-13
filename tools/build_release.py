#!/usr/bin/env python3
"""Build dist/mdh-advanced-humanizer.zip, the folder users upload to Claude.ai or unzip into a skills directory.

Standard library only. Usage: python -I tools/build_release.py [repo_root]
"""
import os
import sys
import zipfile

NAME = "mdh-advanced-humanizer"
INCLUDE_FILES = ["SKILL.md", "LICENSE", "PORTABLE.md", "scripts/mdh_text.py"]
INCLUDE_DIRS = ["references"]
FIXED_TIME = (2026, 1, 1, 0, 0, 0)  # same bytes for the same sources


def collect(root):
    files = [f for f in INCLUDE_FILES]
    for d in INCLUDE_DIRS:
        for base, _, names in os.walk(os.path.join(root, d)):
            for n in names:
                if n.endswith(".md"):
                    files.append(os.path.relpath(os.path.join(base, n), root).replace("\\", "/"))
    return sorted(set(files))


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), ".."))
    files = collect(root)
    missing = [f for f in files if not os.path.isfile(os.path.join(root, f))]
    if missing:
        sys.exit("missing files: " + ", ".join(missing))
    out_dir = os.path.join(root, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, NAME + ".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            data = open(os.path.join(root, f), "rb").read().replace(b"\r\n", b"\n")
            info = zipfile.ZipInfo(NAME + "/" + f, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
    print("built %s (%d files)" % (os.path.relpath(out, root), len(files)))


if __name__ == "__main__":
    main()
