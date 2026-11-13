# mdh_text.py 0.4.1 — false-positive fixes from user testing

- **Spelling fixes no longer count as new meaning cues.** This covers every cue class, including negation.
  - A cue that appears in the revision counts as already present when the aligned original sentence has a near-miss spelling of it.
  - A near miss means Damerau-Levenshtein distance ≤ 2, the same first letter, and a cue word of 5+ letters.
  - Example: "becuase" → "because" no longer raises `CAUSAL_ADDED`.
  - Cue words shorter than 5 letters (not, may, if, no) are never absorbed this way.
- **"when compared with/to/against"** is no longer read as a condition cue.
- **Number role words:**
  - Prepositions, comparatives and function words (versus, vs, relative, compared, against, than, over, per, from, to, by, at, in, on, with, within, across, among, after, before, during, since, until and similar) are skipped.
  - The search now looks further for the first content word: up to 7 tokens within 80 characters of the number.
  - This removes the "relative to" → "versus" noise.
- **CJK character counts in `count` and `budget`:** when Chinese, Japanese or Korean text is present, the output adds three fields:
  - `cjk_characters`: Han, Kana and Hangul characters.
  - `cjk_characters_with_punctuation`: the same, plus CJK and fullwidth punctuation and the curly quotes, ellipsis and em dash that Chinese text uses.
  - `cjk_note`: says that 字数 limits conventionally include punctuation.
- **New `budget --count-mode words|cjk_chars_with_punct`** (default `words`) checks the limit against that character count.
  - The output includes `count_mode`. In character mode, `count_words` keeps the word count.
  - If no CJK characters are found, `budget` returns `NOT_RUN`.
- Tests: 71 (6 new regression tests).

# mdh_text.py 0.4.0 — changes from 0.1.3-dev

## Interface (breaking)
- `--file` is required for `count`, `budget` and `inventory`; pass `-` to read stdin explicitly.
- `budget` `verification_state` is now `VERIFIED` (PASS), `FAILED` (FAIL) or `NOT_RUN` (could not check: zero words counted or a requested section is missing). `delivered_verification` was removed.
- `budget` rejects arguments that do not apply to the chosen `--type`:
  - `--target` with `range`;
  - `--min`/`--max` with any other type.
- Markdown is stripped before counting by default. Use `--keep-markdown` to count it as written. `--strip-markdown` is still accepted and does nothing.
- `--authorized` now takes `{"authorized": [{"from": "...", "to": "..."}]}`. Rules for entries:
  - Whitespace-only entries, entries with both sides empty, and entries with identical sides are rejected.
  - `""` on one side authorises a pure deletion or addition.
  - Only literal protected-item findings can be authorised, and only when both sides match.
  - Cue findings (negation, hedge, direction, condition, and so on) can never be authorised.
- New command: `originality --source <file> --text <file> [--n 6]`. Status is `CLOSE_PARAPHRASE_FLAG` or `NO_CLOSE_COPY_DETECTED`.
  - Text inside double quotation marks is reported separately and does not count toward the flag.
  - Flags when a shared span reaches 12 words or more, or when the shared n-gram ratio reaches 0.15 or more.
- Every JSON error now includes `"command"`. Version is `0.4.0`.

- `compare --protect <terms.txt|.md>`:
  - Takes one term per line; blank lines and duplicates are ignored.
  - Counts exact, case-sensitive, whole-word occurrences in each version.
  - Any difference produces `PROTECTED_TERM_CHANGED`: a `DETECTED_CHANGE` with `literal` true that can never be authorised.
  - The output reports `protected_terms_checked`.
- `originality` also reports `reordered_close_sentences`: text sentences with at least 8 content words whose content-word overlap with one source sentence is Dice ≥ 0.8 in any order. Any such sentence triggers `CLOSE_PARAPHRASE_FLAG`.
  - It also reports `lcs_words`, the longest common subsequence of content words over best-matching sentence pairs with Dice ≥ 0.5.
  - Mostly-quoted sentences are skipped.
- `inventory` reports `repeated_openers`: runs of 3 or more consecutive sentences that start with the same word, ignoring the/a/an, with their sentence indexes. This is informational only.

## Security
- Only `.txt .md .markdown .text .rst` files are read (`.json` for `--authorized`).
- Paths containing `.ssh`, `.aws`, `.gnupg`, `.git`, `.netrc`, `.env*`, `id_rsa*` or `credentials` are refused (exit 3).

## Counting
- Each Chinese, Japanese or Korean character counts as one word.
- Thai is estimated at one word per 5 characters, with a `thai_estimate` warning.
- The figure dash, horizontal bar and minus sign are treated like en and em dashes.
- A spaced ellipsis (". . .") no longer counts as 3 words.
- Thematic breaks, setext underlines, footnote markers and HTML comments are not counted.
- `approx` uses exact fractions, so 115 now passes 100 ±15 %.
- Empty input fails with `NOT_RUN` and the warning "no words counted".

## Exclusions
- A references block starts only when the heading is followed by a reference-like line (year, DOI, URL, "et al.", or "[n]"). It must also either sit in the second half of the document or be made up mostly of references.
  - The block ends at the next heading-like line.
- Recognised variants: bold, trailing colon or period, "Sources", "Citations", "References and Notes", "Works Cited", "Literature Cited", "Bibliography", "Reference List".
- New `excluded_share` field, with a warning when more than 30 % of the words are excluded.
- Title detection:
  - Recognises setext titles.
  - Greetings, bullets, lines ending in ")" and single-paragraph documents are not treated as titles.
- Captions: `Table 3 - x`, `Figure S1.`, `Table I.`, `*Figure 1.*`.
- An unclosed code fence produces a warning. It excludes the rest of the document only when `code` exclusion was requested.
- Section names match after removing bold markers, a trailing colon and leading numbering.

## Input handling
- UTF-16 files with a byte-order mark are read.
- Invalid UTF-8 falls back to Windows-1252, with a warning.
- A directory path gets a clear error on Windows.

## Compare
- **Cues** are compared by form, not just by count:
  - Hedge strength classes, for example `may`→`likely`→`unlikely`.
  - Certainty strength.
  - Quantifier classes (`each`=`every`, `often`=`frequently`).
  - Condition classes (`when`=`whenever`, `if`=`provided that`; `unless`, `only if` and `if` are distinct).
  - Added limiting qualifiers.
- **Direction lexicon** across these axes: amount, time, quality, likelihood, decision, outcome, significance, share and obligation.
  - Reversals on the amount axis report `DIRECTION_REVERSED`.
  - Reversals on the other axes, and negating prefixes (`un-`, `in-`, `non-`, `im-`, `ir-`, `il-`, `dis-`), report `POLARITY_OR_DIRECTION_CHANGED`.
- **Causal language**: increase and decrease verbs are now treated as direction words, not causal words. New `CAUSAL_WEAKENED` finding.
- **New relation and negation findings**: `LABEL_ROLES_SWAPPED`, `LABEL_CHANGED` and `NEGATION_SCOPE_CHANGED` ("not all" versus "all … not"). "not any" is treated the same as "no".
- **Numbers**:
  - New: spelled-out cardinals, `-fold` and `x` multipliers, scale words (thousand/million/billion) and suffixes (`k`, `bn`, `$3m`), ordinals (`ORDINAL_CHANGED`).
  - Units are canonicalised: `%` = percent = per cent; percentage points are distinct.
  - `NUMBER_MOVED` reports numbers that swapped between sentences.
  - `p = .04` and `p = 0.04` are treated as equal.
  - "Forty" and "40" are treated as equal.
- Numbers after "Figure", "Table", "Section" and similar labels no longer get a role word.
- "May" as a month is no longer treated as a hedge.
- "over" was removed from the directional cues.
- **Alignment** is content-based: identical sentences are anchored first, and only the gaps are searched.
  - Inserting 20 sentences at the top of a 2,000-sentence document now gives 40 findings instead of 1,871.
  - A single rewritten sentence between anchors is aligned even when the wording overlap is low.
- **Remaining known misses** (documented as an expected failure in the tests):
  - A cause and an association swapped between two objects in one sentence.
  - A hedge moved into the other clause when a sentence is split.

## Performance
- Overlap tracking uses a coverage array. Markdown patterns are bounded. Grouping by sentence uses dictionaries.
- Detailed number analysis stops at 50,000 numbers per text, with a warning.
- 1 MB adversarial inputs (CPU time):
  - `inventory`: under 4.3 s.
  - `strip_markdown`: under 0.3 s.
  - `compare`: 4.7 s.
  - `originality`, including the reordering check: 1.0 s.

## Tests
- `tests/test_mdh_text.py`: 65 stdlib `unittest` tests, including a regression case for every reported defect. Run:
  `py -I -B -m unittest discover -s scripts/tests` (or `python3`).
- The `MDH_PERF_LIMIT` environment variable sets the CPU-seconds limit for the speed tests. The default is 8.
