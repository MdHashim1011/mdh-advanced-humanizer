# MdH's Advanced Humanizer

A writing skill for agents that write, revise and edit prose. It helps produce text a careful human expert would sign: specific, accurate, at the right level and within the word limit, with facts, numbers, citations, negations and the writer's voice kept intact.

Version 0.4.5. Author: Md.Hashim. License: MIT.

## What it does

- Writes and revises essays, reports, papers, theses, literature reviews, lab reports, abstracts, cover letters, personal statements, emails and messages.
- Proofreads, paraphrases, shortens, expands, and changes tone or education level.
- Handles requests to make writing "more natural", "less robotic", "less generic" or "smoother" as ordinary editing: it removes filler and stock phrasing and restructures sentences, using a two-tier clarity checklist.
- Routes each request (proofread, revise, short new writing, long new writing, source-based writing) and reads only the reference files that route needs.
- Protects meaning. Numbers and units, citations, quotations, hedges, negations, conditions, direction words, quantifiers and attribution are kept exactly unless the user authorises a change.
- Respects length limits without padding. When a minimum cannot be reached honestly, it delivers the faithful version and says what information would let it reach the target.

## What it does not do

- **It is not a detector-evasion tool.** It does not add typos, fake hesitations, rare words or random sentence variation to make text "pass" an AI detector, and it declines requests framed that way. Those tricks also make writing worse.
- It does not invent facts, data, quotations, references or personal experiences. Missing material is requested or marked with a placeholder.
- It does not describe a source's findings from a title or citation alone.
- It is not meant for code, code comments, READMEs, API docs or commit messages.

## Installation

### Claude Code

Install as a plugin from this repository:

```text
/plugin marketplace add MdHashim1011/mdh-advanced-humanizer
/plugin install mdh-advanced-humanizer@mdh-advanced-humanizer
```

Or copy the folder into your skills directory, for example `~/.claude/skills/mdh-advanced-humanizer/` (personal) or `.claude/skills/mdh-advanced-humanizer/` (project). The folder must contain `SKILL.md` at its top level.

### Claude.ai (zip upload)

1. Zip the skill folder so that `SKILL.md` sits at the top level of the folder inside the zip. Leave out `.git`, `.github` and any `__pycache__` folders.
2. In Claude.ai, open Settings, go to Capabilities, and upload the zip under Skills.
3. Code execution is optional. Without it, the skill works normally and labels word counts as estimates.

### Other agents and chat platforms

For custom GPTs, Gemini Gems, Cursor rules, system prompts or any platform without skill folders, paste the contents of `PORTABLE.md` into the instructions field. It is a single-file version of the rules, under 8,000 characters, and assumes no code execution.

Cursor can also load the plugin manifest in `.cursor-plugin/`. Agents that read `agents/openai.yaml` get a display name and a default prompt.

## Optional Python helper

`scripts/mdh_text.py` gives exact word counts, meaning-change flags and close-paraphrase checks. It uses only the Python 3 standard library, makes no network calls and writes only JSON to standard output.

```text
python3 scripts/mdh_text.py count       --file draft.md [--exclude references,title,headings]
python3 scripts/mdh_text.py budget      --file draft.md --type max --target 250
python3 scripts/mdh_text.py inventory   --file draft.md
python3 scripts/mdh_text.py compare     --original before.md --revised after.md
python3 scripts/mdh_text.py originality --source source.md --text draft.md
```

On Windows, use `py -3` if `python3` is not available. Exit code `1` means a budget failed or a flag was raised; read the JSON either way. Full usage, exit codes and the safety rules the agent follows when running it are in `references/helper.md`.

## Tests and validation

Run from the skill root, or pass full paths:

```text
python3 -I -B -m unittest discover -s scripts/tests
python3 -I tools/validate_package.py .
```

On Windows replace `python3` with `py`. The validator prints a JSON report and exits with `0` when every check passes and `1` otherwise. It checks the `SKILL.md` frontmatter, version consistency across all manifests, link targets, size limits and leftover development markers.

The CI workflow in `.github/workflows/ci.yml` runs both on Linux, Windows and macOS with Python 3.9 and 3.13.

## Reporting problems

Use the issue forms: "Meaning changed" when a revision altered a claim, "Writing quality" for style and length problems, and "Helper script bug" for `mdh_text.py`. Maintainers should read `CONTRIBUTING.md`.

## License

MIT. Copyright (c) 2026 Md.Hashim. See `LICENSE`.
