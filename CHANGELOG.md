# Changelog

All notable changes to this skill are recorded here. Versions follow semantic versioning. The detailed change list for the helper script is in `scripts/CHANGELOG-0.4.0.md`.

## [0.5.2] - 2026-11-13

### Skill instructions
- Removing watermarks or provenance marks is now named as out of scope, next to detector evasion, in `SKILL.md`, `PORTABLE.md` and the task-routing reference.
- Proofreading is route R1 at any length; polishing and humanizing are always route R2, so a short "humanize this" request no longer has two possible routes.
- The paraphrasing example keeps the source's hedge and quantity words exactly and changes only the sentence structure, which matches minimum rule 3.
- Text-only replies may carry one integrity sentence per issue, in both `SKILL.md` and `PORTABLE.md`; previously the two files disagreed and a strict reading dropped a safeguard when two issues applied.
- A visible AI-use disclosure in the user's text is kept when the skill makes its honest edit of an out-of-scope request.
- The fast path no longer covers proofreading of evidence-heavy text, which still reads the evidence and meaning reference.
- In `SKILL.md`, when a sentence gets clumsier after restructuring, the skill tries another structure before keeping the original.
- `PORTABLE.md` lists an uncovered gap as a notice trigger, includes "what made it stiff" in the detector note and lists code among protected content.

### Helper script
- `compare` flags an approximator ("about", "around", "nearly", "almost") that is removed before a quantity: a number, a currency amount, a fraction ("about an eighth"), or an all-or-nothing word ("nearly all", "almost no", "almost everyone"). "About a fifth" becoming "a fifth" is now reported as a removed hedge. "About" before a topic ("talked about the results", "around the world") is not affected, but "about" before a number used as a topic ("a study about two cities") is flagged when reworded; this errs on the safe side and is recorded in the tests. On the 22,000-word thesis and paraphrase outputs from earlier testing, the number of flags did not change.

### Package tools
- The validator also compares the version fields in `.claude-plugin/marketplace.json` (when present) and the version in the `PORTABLE.md` title.
- New tests for the validator's version check (`scripts/tests/test_validate_package.py`).

## [0.5.1] - 2026-11-13

### Changed
- Author name is now given as Mohamed Hashim in the license, the skill metadata, the plugin manifests and the README.

## [0.5.0] - 2026-11-13

First public-ready release.

### Skill instructions
- **Near misses on a minimum length** now get one more honest expansion pass before a shortfall is reported. In a blind run the previous version stopped 7 words short of a 300-word minimum.
- **Detector-framed requests:** the note after the edit never opens with "I can't"; it says what made the text stiff and why no detector result can be promised.

### Repository
- New README with diagrams, quick start, blind test results, limitations and roadmap.
- Light and dark diagrams in `assets/`.
- `SECURITY.md` and a CodeQL workflow (runs once the repository is public).
- CI actions updated to current pinned versions (`actions/checkout` v7.0.1, `actions/setup-python` v7.1.0).
- Release builds a ready-to-upload `mdh-advanced-humanizer.zip`.

## [0.4.5] - 2026-11-13

### Skill instructions
- **Detector-framed requests:** once the honest edit is delivered, the follow-up sentence is information, never a refusal. It names what made the text stiff and why no detector result can be promised, and says when a detector is unlikely to matter (a workplace email). Coursework still gets the AI-use disclosure offer.
- Small wording cuts to keep `SKILL.md` and `PORTABLE.md` within their size limits.

## [0.4.4] - 2026-11-13

### Skill instructions
- **Detector-framed requests** now say briefly why no detector result can be promised: detectors are unreliable and also flag human writing.
- **Humanize and "less robotic" requests loosen stiff greetings and sign-offs** ("Dear Team" to "Hi team", "Best regards" to "Thanks") unless the context is formal. The rule was in the clarity checklist only; it is now in the main rules and `PORTABLE.md`.
- The paraphrase example no longer reuses a test passage.

## [0.4.3] - 2026-11-13

Fixes for the two losses both blind graders agreed on in a comparison against the plain model (8 tasks, 2 graders), plus one paraphrase refinement.

### Skill instructions
- **Detector-framed requests get the honest edit straight away.** The evasion goal is still not pursued, but the user now receives a clearer, more natural version at once, with one sentence saying no detector result can be promised. Coursework gets a mention that help with an AI-use disclosure is available.
- **Expanding for a named reader** (committee, manager, client) may use that reader's usual layout: a short summary, headed sections and what each fact means for the reader. Invented requests, dates, causes and commitments are still not allowed.
- **Paraphrasing someone else's text** keeps each hedge's meaning without reusing the source's surrounding words.
- SKILL.md shortened elsewhere (helper details now point to `references/helper.md`) to stay within the size limit.

## [0.4.2] - 2026-11-13

### Helper script
- **New `CUE_MOVED` check.** Flags a negation, hedge, certainty, causal or associative cue that keeps its count but moves to a different part of the claim. Closes the two known gaps from 0.4.1: a causal and an associative claim swapped between two objects, and a hedge that moves to the other clause when a sentence is split. It also catches a negation moving between clauses. No new flags on the 22,000-word thesis or paraphrase test outputs.

### Skill instructions
- **Honest shortfall with placeholders.** When a minimum is more than about a quarter out of reach, the text also marks where each missing detail belongs, so the user can fill it in place.
- **Template signposting** ("Firstly... Finally", 首先/其次/最后) is now covered in the main drafting rule for every language, not only in the clarity checklist.
- `PORTABLE.md` carries both changes and now shows the correct version.

## [0.4.1] - 2026-11-09

Tuning from a blind A/B comparison against 0.3.3 (16 test pairs, two independent graders).

### Skill instructions
- **Embedded instructions.** Instructions addressed to an AI are now left out of edited text and reported in one sentence (kept only when the user asks for verbatim text).
- **Humanize requests may loosen stiff greetings and sign-offs** to the natural form for the relationship; formal contexts keep formal forms.
- **Paraphrase means restructuring.** Dense statistical text is restructured properly, with the meaning check as the safety net.
- **Honest expansion first.** Before reporting a shortfall against a minimum length, every honest expansion the material allows is used.
- **Cover letters with thin material** get a stronger draft with marked placeholders plus two or three specific questions.
- **Blocking gaps under deadline** come with safe partial help (a findings-free outline) straight away.
- **Incomplete references** for a requested citation style are noted in one line.
- **Routing:** short new writing is under 200 words; essays and report sections always get the planning route.
- **Launcher:** `py -3` first on Windows.
- **Readable restructuring.** Paraphrases restructure for readability, not for difference; a clumsier sentence is reworked or kept as it was.
- **Plain-language verification reports** with no script names or status codes unless technical detail is requested.
- **Formulaic enumeration in any language** (for example 首先/其次/再次/最后) and slogan endings are treated as over-signposting.
- **Concrete honest-expansion example** for status updates.
- **CJK limits:** Chinese and Japanese character limits are checked including punctuation.

### Helper script (`scripts/mdh_text.py` 0.4.1)
- Spelling corrections no longer raise meaning-cue flags.
- "when compared with/to" is no longer read as a condition.
- Number role checks skip function words such as "versus" and "relative".
- New CJK character counts and `budget --count-mode cjk_chars_with_punct`.

## [0.4.0] - 2026-11-09

### Skill instructions
- **Minimum-rules block.** SKILL.md now opens with nine rules that apply even when no reference file is read: no invented content, a citation is not a source, protected meaning elements, doubtful facts kept and flagged, embedded instructions treated as data, no padding, nothing unrequested, writing-only delivery, and no claimed checks that did not run.
- **Humanize scope.** "Humanize", "more natural", "less robotic", "less generic" and "smoother" are handled as ordinary quality requests (light editing plus removal of stock phrasing). Requests to evade AI detectors or disguise prohibited assistance are declined in one sentence, with an honest edit, feedback or disclosure help offered instead.
- **Routing order.** Requests are routed in a fixed order: R0 (not a writing task), R1/R2 (existing text), R5 (new writing from sources or data, with R5-lite for short abstracts and summaries), then R3/R4 by length. R1 and R3 have a fast path that needs no reference files.
- **Honest-shortfall rule.** When reaching a minimum length would require repetition or unsupplied content, the skill delivers the faithful version and names the specific information that would let it reach the target.
- **Clarity checklist tiers.** `references/clarity-checklist.md` splits patterns into Tier 1 (fix wherever found) and Tier 2 (act only when clustered or recurring). Each pattern states the clarity problem and a restructuring fix, not a word to avoid.
- **Paraphrase and originality guidance.** New `references/paraphrase-and-originality.md` covers writing from meaning, keeping technical terms, quoting distinctive phrases, and checking for shared word runs with the source.
- **Delivery cases.** Output rules distinguish text-only requests, ordinary requests and verification requests. Integrity notices are always kept, as one plain sentence after the writing.
- **PORTABLE.md.** A single-file version of the instructions for platforms without skill folders or code execution, kept under 8,000 characters.

### Helper script (`scripts/mdh_text.py` 0.4.0)
- **Temp-file workflow.** Text to be checked is written with a file-writing tool to a fresh temp folder, never passed through shell quoting.
- **Launcher fallback.** The documented launch order is `py -3` first on Windows, otherwise `python3`, then `python`, with counts labelled ESTIMATED when none works.
- **Path guard.** Only `.txt`, `.md`, `.markdown`, `.text` and `.rst` inputs are read (`.json` for the authorized list), and paths under credential or configuration folders are refused.
- **Direction and antonym detection.** `compare` checks direction words across several axes (amount, time, quality, likelihood and others), negating prefixes, hedge and certainty strength, quantifier and condition classes, and weakened causal wording.
- **Originality command.** New `originality` command reports long word sequences shared with a source, with quoted text reported separately.
- **Protected terms.** `compare` accepts user-protected terms that must survive exactly and can never be authorised away.
- **CJK counting.** Each Chinese, Japanese or Korean character counts as one word; Thai is estimated with a warning.
- **Performance fixes.** Content-based sentence alignment, bounded Markdown patterns and coverage arrays keep 1 MB adversarial inputs within a few CPU seconds.
- **Tests.** Standard-library `unittest` suite in `scripts/tests/`, including a regression test for every reported bug.

### Packaging
- Plugin manifests for Claude Code (`.claude-plugin/`) and Cursor (`.cursor-plugin/`), and `agents/openai.yaml`.
- `tools/validate_package.py` checks frontmatter, version consistency, links, size limits and leftover development markers.
- GitHub Actions workflow running the validator, unit tests and a helper smoke test on Linux, Windows and macOS with Python 3.9 and 3.13.
- Issue forms for meaning changes, writing quality and helper bugs.
- README.md, CONTRIBUTING.md and this changelog.

## [0.3.3]

Previous development release.
