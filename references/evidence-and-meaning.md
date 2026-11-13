# Evidence and meaning

Read this for R5 tasks, for revisions of evidence-heavy or technical text, and whenever sources, statistics or citations are involved. It covers source modes, gaps in the supplied material, claim tracking and meaning protection.

## Source modes
Decide the mode before writing anything that cites, summarises or reports research.
- **Source-locked:** the user limits you to supplied material ("use only my articles", "do not add references", "summarise these documents").
  - Cite only that material.
  - Never add outside studies, and never fill missing findings, numbers or details from memory.
  - Keep attributions and uncertainty.
- **Citations only:** the user lists references but does not supply their text. Treat this as source-locked with the content unavailable.
  - You may format and cite the references.
  - You may not describe their findings, samples, effect sizes or conclusions.
  - Ask for the abstracts, full texts or the user's own notes on each one.
  - You may offer a skeleton with marked gaps, clearly labelled as containing no findings.
- **Research-authorized:** the user asks you to find or use published research, including a request for peer-reviewed citations when no sources are supplied.
  - Use only research tools that are available and permitted in this session.
  - Rely on a specific finding, statistic, sample size or bibliographic detail only after reading it in a retrieved source.
  - Distinguish primary studies from secondary summaries.
  - Never present a citation recalled from memory as verified.
  - If no tool is available, or a call is denied, treat the sources as unavailable. Do not retry denied tools or look for another way around the restriction.
- **Sources unavailable:** required sources were not supplied, cannot be accessed, or cannot be verified.
  - Do not write a review or evidence paragraph built on remembered references, placeholder values or guessed details (authors, years, journals, pages, sample sizes, statistics, quotations).
  - Ask for the sources, or explain the limitation briefly.
  - Offer an outline or search terms when useful, labelled as not evidence.

These rules govern source-specific claims. Ordinary explanatory writing may use well-established general knowledge without citations; do not refuse a task only because no documents were supplied.

## Gaps in the supplied information
Write only what the user's requirements, documents and sources support. Never invent an operational rule, condition, threshold, exception, fallback or required action for a case the material does not cover. Never turn an uncertain point into a definite one. Judge each gap by its effect on the requested deliverable:
- **Nonblocking:** the deliverable can be completed fully and accurately, and the unspecified case lies outside it. Complete the task, leave that case out, and add no notice.
- **Material:** the deliverable must address the case to be correct, safe or faithful, but the material does not say what to do.
  - Keep everything that is supported and describe nothing beyond it.
  - Name the unspecified case in one integrity sentence after the writing, for example "The requirements do not say what to do when X happens."
  - Do not resolve it with a rule of your own.
- **Blocking:** the deliverable cannot be produced accurately without essential missing information. Ask for it in one short message, or state the limitation. Never produce a complete-looking answer built on invented facts, findings or sources.
- **Procedures:** when turning supplied requirements into instructions, add no step, condition, threshold, approval, exception or escalation that the material does not contain. You may reword, order and explain supplied steps. Anything illustrative must be clearly optional ("for example").

## Sources and claims
A source that is about the same topic does not support a claim. Support means a passage, table, figure or value in the supplied material states or entails the claim.

Before drafting R5 work, list the sources with short IDs (S1, S2...) and note what each one actually reports, with a locator where possible (page, section, table). For R5-lite tasks a mental check is enough.

Track every factual claim with one of these statuses:
| Status | Meaning | What to do |
| --- | --- | --- |
| SUPPORTED | Found in supplied material (locator noted) | Cite it as the user's style requires |
| USER-SUPPLIED | Asserted by the user, not checked | Keep it, attributed to the user's material if relevant |
| GENERAL BACKGROUND | Common knowledge at the target level | No citation needed |
| UNVERIFIED | Plausible, but its source was not available | Hedge it as unconfirmed, ask, or omit |
| UNSUPPORTED | No support, or the source contradicts it | Remove it, and give an integrity notice if the user asked for it |

Any UNVERIFIED or UNSUPPORTED claim the user asked you to include gets a one-sentence integrity notice. Show the full claim list only on request (Case C).

Copy statistics exactly: value, unit, denominator, interval, test and direction. Apply the same care to interpretation:
- A non-significant result is not evidence of no effect or of equivalence.
- Association is not causation.
- Keep the strength the source permits.

## Protected content in revisions
Keep exactly, unless the user authorises a change: numbers and units, statistics, equations, citations and their placement, quotations, technical identifiers, code, URLs and defined terms. Then keep the meaning of every claim. For each sentence you changed, confirm:
- **Polarity** - it still asserts or still denies the same thing.
- **Negation scope** - "did not establish an effect" is not "established no effect"; "found no evidence of X" is not "found evidence of no X"; "not all" is not "all ... not".
- **Strength** - "suggests", "may" and "appears" were not turned into "shows", "is" or "proves".
- **Conditions** - "only if", "unless" and "when" survive with the same force.
- **Causal status** - "associated with" did not become "caused", "led to" or "reduced".
- **Direction** - "increased", "higher", "more than", "before" and "better" did not become their opposites.
- **Quantity** - "some", "most", "few" and "about 40%" are unchanged; percent and percentage points are not swapped.
- **Roles** - who did what to whom, and which group each number belongs to. Which value is a change and which is a level: "fell by 30" versus "fell to 30".
- **Attribution** - each finding stays with the same source.

## Using the helper's comparison
When execution is available, run `compare` on the original and the revision (see `helper.md`). For every finding decide one of:
- **keep** - the meaning is truly unchanged;
- **restore** - revert the span;
- **authorised** - the user asked for this change.

Read the result codes like this:
- `DETERMINISTIC_LITERAL_FAILURE` means a protected item changed: fix it unless authorised.
- `SEMANTIC_RISK_FLAG` means review the flagged sentences.
- `NO_FLAG_DETECTED` means only that no listed cue changed. The helper still misses some synonyms and complex sentences, so your own claim-by-claim check is required.

## Facts you doubt
If the user's text contains something that looks wrong, do not silently correct it. Keep it, and flag the concern in one integrity sentence after the writing.
