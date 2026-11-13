# Task routing

Read this when the route is not obvious from a single reading of the request. Decide in order: is it a writing task at all; is existing text supplied; does new writing rest on sources; then length.

## Routes
| Route | Choose it when | Do not |
| --- | --- | --- |
| **R0 Unrelated** | The request is not about producing or improving prose: maths, code, code comments, READMEs, API docs, commit messages, trip planning, a factual question | Apply writing workflows or ask about education level |
| **R1 Proofreading** | Correct errors or lightly polish a short text: "proofread", "fix grammar", "check this" | Restructure, change wording that is already correct, or add content |
| **R2 Existing-text transformation** | The user supplies text and wants it revised, shortened, expanded, paraphrased, humanized, simplified, made more formal, or adapted to a level, audience or tone | Treat it as new writing, drop protected content, or invent material to fill an expansion |
| **R3 Short new writing** | New text under 200 words in a simple genre that does not rest on sources: email, message, notice, short answer, bio | Build an evidence ledger |
| **R4 Substantial new writing** | New text of 200 words or more, or any essay, explanation or report section whatever its limit, that does not rest on a body of supplied sources: essay, explanation, report section, cover letter, statement | Treat it as a short answer |
| **R5 Source-based writing** | New text that must rest on supplied or retrieved sources or data, at any length: literature review, synthesis, lab report, results interpretation, annotated summary, an abstract or summary of a supplied paper | Cite or describe sources that were not supplied and read |

**R5-lite:** a short abstract, summary or caption written from supplied content follows the R5 source rules (only what the material says, exact numbers, correct attribution) without building a full claim ledger.

**Mixed requests:** apply R2 rules to the parts being transformed and R4/R5 rules to the new parts. Example: "revise my introduction and add a paragraph on these two papers" is R2 for the introduction and R5 for the new paragraph.

## Editing intensity (R1/R2)
| Mode | Changes allowed | Typical wording |
| --- | --- | --- |
| Proofreading | Spelling, grammar, punctuation, agreement, obvious typos, consistency of terms | "proofread", "fix errors", "correct" |
| Light editing | + sentence clarity, flow, concision, word choice, removing filler and stock phrases, restructuring sentences | "humanize", "less robotic", "more natural", "polish" |
| Substantive revision | + paragraph development, argument order inside sections, transitions, removing repetition | "smoother", "paraphrase", "reword", "improve" |
| Structural improvement | + reordering sections, splitting or merging paragraphs, headings | "restructure", "reorganise" |

**Expansion requests:** expand only with content the user supplied, general background appropriate to the level, or clearly marked suggestions. Never expand with invented findings, and never by repeating points. If the target cannot be reached faithfully, use the honest-shortfall rule in SKILL.md.

## Asking questions
Ask only when the answer would change the result materially. Typical blocking gaps:
- The text to revise is missing.
- A source-based task has no sources, or only citations.
- Results for a lab report are missing.
- A personal statement has no real details.
- Two instructions conflict (for example "exactly 300 words" and content that cannot fit).

Ask once, briefly, with options. Do not re-ask what the user already gave. When a sensible default exists for level, citation style or length, use it silently; mention the default only in a Case C verification report.

## Preferences in the conversation
Keep the user's stated level, spelling variety, citation style, counting convention and tone for later requests in the same conversation. A request like "this one in US spelling" applies to that task only. Do not claim memory you do not have.

## Integrity conflicts
If the user asks to make text undetectable, bypass AI detectors, or disguise prohibited assistance, decline that goal in one sentence. Offer an honest quality edit (no tricks), feedback the user can apply, or help drafting an AI-use disclosure. Do not ask the user to prove what their course or employer allows, and do not lecture. Ordinary requests to humanize, sound natural or sound less robotic are not integrity conflicts.
