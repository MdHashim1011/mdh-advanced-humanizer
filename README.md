# MdH's Advanced Humanizer

Makes writing read like a careful person wrote it, without changing what it says.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/before-after-dark.svg">
  <img alt="A stiff 74-word email full of stock phrases such as 'I hope this message finds you well' and 'it is crucial to highlight' becomes a 25-word email: 'Hi team, the quarterly meeting has moved to Thursday, 14 March, at 10:00. Attendance is mandatory for all team leads. Thanks, Priya.' The date, the time, 'mandatory', 'all team leads' and the sender are kept exactly." src="assets/before-after-light.svg" width="100%">
</picture>

Most humanizers rewrite text until it sounds different. That is easy, and it is how a "may" turns into a certainty, a "not significant" result turns into "no effect", or a 250-word limit turns into 290 words. This skill edits the way a good editor does. It cuts filler and stock phrasing, restructures sentences that read stiffly and keeps the writer's voice, while every number, negation, hedge, condition and citation stays exactly as it was.

It works in Claude Code and Claude.ai as an Agent Skill, and on other platforms as a single block of instructions. An optional Python script gives exact word counts and checks a revision for changes in meaning.

## Installation

**Claude Code**, as a plugin:

```text
/plugin marketplace add MdHashim1011/mdh-advanced-humanizer
/plugin install mdh-advanced-humanizer@mdh-advanced-humanizer
```

Or download [`mdh-advanced-humanizer.zip`](https://github.com/MdHashim1011/mdh-advanced-humanizer/releases/latest/download/mdh-advanced-humanizer.zip) from the latest release and unzip it into `~/.claude/skills/` for every project, or into `.claude/skills/` for one project.

**Claude.ai:** download the same zip, then go to Settings, Capabilities, Skills and upload it as it is. Code execution is optional; without it, word counts are labelled as estimates.

**ChatGPT, Gemini, Cursor and other assistants:** paste the contents of [`PORTABLE.md`](PORTABLE.md) into the custom instructions or rules field. It holds the same rules in under 8,000 characters and needs no files or code.

## Quick start

Ask for what you want in ordinary words. The skill decides how heavy the edit should be.

```text
Make this email sound less robotic: <paste>
Paraphrase this paragraph so it reads more smoothly: <paste>
Cut my abstract to under 250 words.
Proofread this. Just the corrected text, please.
Expand this project update to at least 300 words for the steering committee.
写一篇不超过300字的短文，题目：城市骑行的好处。
```

It works in the language of your text and never translates unasked. Chinese and Japanese limits are counted in characters, including punctuation, as is usual for those languages.

## How it works

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/how-it-works-dark.svg">
  <img alt="Four steps. 1 Route: the request is classed as proofreading, revision or humanizing, short or long new writing, or source-based writing. 2 Edit: filler and stock phrasing are cut and sentences restructured while the writer's voice is kept; nothing is padded or invented. 3 Check: every negation, hedge, number, citation, condition and causal claim is compared with the original, and the length is checked; an optional script gives exact counts, meaning flags and a copied-phrase check. 4 Deliver: only the writing, plus one plain sentence when something needs the user's attention." src="assets/how-it-works-light.svg" width="100%">
</picture>

**Route.** A proofread gets error fixes only. "Humanize", "less robotic" and "smoother" get a light edit that removes stock phrasing and loosens stiff greetings. New writing is planned before it is drafted, and writing based on sources uses only sources you supplied. A reference you list without its text is never summarised from memory.

**Edit.** The skill removes the habits that make writing sound generated: announcements ("This essay will discuss"), stacked connectors ("Furthermore… Additionally… In conclusion"), inflated significance ("a testament to", "a pivotal role"), hollow conclusions and template signposting in any language (首先/其次/再次/最后). It adds nothing you did not supply. When a minimum length cannot be reached honestly, it says how short the text is and which details would close the gap, and it never repeats a fact to fill space.

**Check.** Before anything is returned, the skill compares each changed sentence with the original for:

| Kept exactly | Example of what it catches |
|---|---|
| Negations and their scope | "did not find X" becoming "found no X" |
| Hedges | "may reduce" becoming "reduces" |
| Conditions | "only when six sessions were completed" losing "only" |
| Cause and association | "is linked to" becoming "causes" |
| Direction and quantity | "fell by 12 to 30" becoming "fell to 12" |
| Numbers, units, citations | "5 mg" becoming "5 g", a citation moved to another claim |
| Who did what | "the trainers interviewed the coordinators" reversed |

**Deliver.** You get the writing and nothing else, unless something needs your attention: a doubtful fact it kept, an instruction hidden in your document that it ignored, or a length it could not reach. Each of those gets one plain sentence. Ask for a verification report and you get exact counts and the results of each check.

## Blind test results

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/blind-test-results-dark.svg">
  <img alt="Bar chart of blind grading scores out of 40, averaged over two graders, with the skill against the same model without it. Chinese essay 35.5 vs 23.5; less robotic email 39.5 vs 32.5; paraphrase a published source 36 vs 30; proofread with a hidden instruction 37 vs 34.5; paraphrase dense statistics 36 vs 34.5; shorten to under 60 words 33 vs 31; make it undetectable request 34 vs 35; expand to at least 300 words 26 vs 29. Totals 277 vs 252 and 277 vs 248." src="assets/blind-test-results-light.svg" width="100%">
</picture>

The same model (Claude Sonnet) answered eight writing tasks with and without the skill. Two independent graders (Claude Opus) scored each pair on fidelity, naturalness, instruction fit and usefulness without knowing which reply came from the skill. The skill scored 277 against 252 with one grader and 277 against 248 with the other, and won six and five of the eight tasks.

The largest gaps were the Chinese essay, where the plain model ran to over 400 characters against a 300-character limit, and paraphrasing a published source, where the plain model dropped the source's hedges ("may have accumulated" became "took"). The skill lost two tasks narrowly. In one it stopped 7 words short of a 300-word minimum; that rule has since been changed so it makes one more honest pass before reporting a shortfall. In the other, a request to get past AI detectors, the graders preferred the plain model's longer explanation.

Some limits on what these numbers show: there was one run per task on each side, the graders were AI models rather than people, and four of the tasks were also used while developing the skill. Treat the results as evidence of a real difference on these kinds of tasks, not as a general ranking.

## The helper script

`scripts/mdh_text.py` gives exact numbers where the model can only estimate. It needs Python 3.9 or later and uses only the standard library.

```text
python3 scripts/mdh_text.py count       --file draft.md --exclude references,headings
python3 scripts/mdh_text.py budget      --file draft.md --type max --target 250
python3 scripts/mdh_text.py compare     --original before.md --revised after.md
python3 scripts/mdh_text.py originality --source source.md --text draft.md
python3 scripts/mdh_text.py inventory   --file draft.md
```

`compare` reports changes in negations, hedges, conditions, causal wording, direction, quantities, numbers, citations and roles, including a cue that keeps its count but moves to another part of the sentence. `originality` flags phrases copied from a source you are paraphrasing. Every command prints JSON. On Windows, use `py -3` in place of `python3`. Full usage is in [`references/helper.md`](references/helper.md).

## What it does not do

It is not a tool for getting past AI detectors. It does not add typos, odd words or random sentence lengths to fool a classifier; those tricks make writing worse, and detectors are unreliable enough to flag human writing too. Asked to make text "undetectable", it gives you the same honest edit and says plainly that no detector result can be promised.

It does not invent facts, results, quotations, references or personal experiences. A cover letter built from thin notes gets marked placeholders and two or three questions, not a made-up project. It is also not meant for code, code comments or commit messages.

## Privacy

The skill is a set of instructions and sends nothing anywhere. The helper script makes no network calls and writes nothing to disk. Text you edit stays with the assistant you already use.

## Current limitations

- Word counts are estimates unless the helper script can run.
- The meaning check is rule-based. It catches the common reversals listed above but not every change; a synonym that weakens a claim can pass. "No flag" never means "proven equivalent".
- Thai word counts are approximate, and the copied-phrase check is tuned for English.
- `PORTABLE.md` carries the core rules but not the reference files, so it is less thorough on long, source-based documents.

## Roadmap

Planned next: a larger blind evaluation with tasks never used during development and human graders, a voice-matching mode that learns from a sample of your writing, and citation-style conversion checks.

## Development

```bash
git clone https://github.com/MdHashim1011/mdh-advanced-humanizer.git
cd mdh-advanced-humanizer
python3 -I -B -m unittest discover -s scripts/tests
python3 -I tools/validate_package.py .
```

The tests need no network access or API keys. The package validator checks the skill's frontmatter, version numbers across all manifests, links, size limits and leftover development markers. CI runs both on Linux, Windows and macOS with Python 3.9 and 3.13.

## License

MIT. Copyright (c) 2026 Mohamed Hashim.
