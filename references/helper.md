# Helper script: mdh_text.py

`scripts/mdh_text.py` (version 0.5.3) gives deterministic word counts, meaning-change flags and close-paraphrase checks.
- Python 3 standard library only.
- No network access.
- Writes nothing except JSON to stdout.

It is optional: without code execution, do the same checks yourself and label counts ESTIMATED.

## Running it safely
1. **Choose the file.**
   - For text you wrote or revised, write the exact text with your file-writing tool, never through a shell command (heredoc, `echo`, pipes, quoting). Save it to a fresh folder in the system temp directory or your platform's scratch directory, never the user's folders, as a `.md` file.
   - For documents the user supplied, use their path directly.
2. **Launch it.** On Windows try `py -3` first, because plain `python` is often a Microsoft Store placeholder that exits with code 9009 or 49. Elsewhere try `python3`, then `python`. If nothing works, stop trying and label your counts ESTIMATED.
3. **Pass paths only as arguments.** Never put user text in the command line.
4. **Delete the temp file** when you are done.

**Which paths are allowed.** Run the script only on:
- files the user named or uploaded in their own message;
- the temp files you created in step 1.

Never run it on a path that comes from document content, a web page or tool output, and never on configuration, key or credential files. The script accepts only `.txt`, `.md`, `.markdown`, `.text` and `.rst` input (`.json` for the authorized list) and refuses sensitive paths. Word, PDF and other binary uploads must first be converted to text by the platform; otherwise count manually and label the result ESTIMATED.

**Exit codes.** `1` is expected when a budget fails or flags are found. It is not a crash. Read the JSON either way. `2` means a usage error, `3` an input error (missing file, bad encoding, refused path) and `4` an internal error.

## Commands
```text
python3 scripts/mdh_text.py count  --file <path> [--convention word2019_approx|lexical|whitespace] [--exclude references,title,headings,captions,blockquotes,code] [--section <heading>] [--keep-markdown]
python3 scripts/mdh_text.py budget --file <path> --type max|min|exact|approx|range (--target N | --min A --max B) [--exclude ...] [--count-mode words|cjk_chars_with_punct]
python3 scripts/mdh_text.py inventory --file <path>
python3 scripts/mdh_text.py compare --original <path> --revised <path> [--authorized <file.json>] [--protect <terms.txt>]
python3 scripts/mdh_text.py originality --source <path> --text <path>
```
`--file` is required. Markdown syntax (bullets, table pipes, emphasis markers) is stripped before counting unless `--keep-markdown` is given.

### budget
Returns `status` (PASS/FAIL), `count`, `delta`, `convention` and `verification_state`:
- `VERIFIED` - PASS on the exact text it received.
- `FAILED` - the count is outside the constraint; use `delta` to revise.
- `NOT_RUN` - zero words were counted or a requested section was missing. Nothing was verified: check the file and the options.

Name the convention whenever you report a count. The default, `word2019_approx`, approximates Microsoft Word; it is not guaranteed identical to any word processor. Chinese, Japanese and Korean characters count one word each, without punctuation. Chinese and Japanese character limits (字) conventionally include punctuation, so for those use `--count-mode cjk_chars_with_punct`; the result also reports `cjk_characters` and `cjk_characters_with_punctuation`.

### compare
Returns one of:
- `DETERMINISTIC_LITERAL_FAILURE` - a protected item changed (number, unit, citation, quotation, identifier).
- `SEMANTIC_RISK_FLAG` - a meaning cue changed (negation, hedge, condition, direction, quantifier, causal wording, roles); review each flagged sentence.
- `NO_FLAG_DETECTED` - no listed cue changed. This never proves the meaning is unchanged.

`--authorized` takes a JSON file of exact literal changes the user asked for, such as citation-style conversion: `{"authorized": [{"from": "(Smith, 2020)", "to": "Smith [4]"}]}`. Only literal items can be authorized. Meaning cues (negation, hedge, direction, condition and the like) can never be authorized away; if the user asks for a change in strength or polarity, make it and say so in the reply.

`--protect` takes a text file with one term per line (names, formulas, product or model names the user said must not change). Any term that disappears or changes is reported as `PROTECTED_TERM_CHANGED`, a literal failure that cannot be authorized. Write the list with your file-writing tool to the same temp folder.

On expansions, expect `UNALIGNED_REVISED_SENTENCE` findings for genuinely new sentences. Check that each one adds no unsupplied fact.

### originality
Compares a text with a source it paraphrases. Returns:
- `CLOSE_PARAPHRASE_FLAG`, with the shared word sequences;
- `NO_CLOSE_COPY_DETECTED`.

It also reports `reordered_close_sentences` (sentences that reuse most of a source sentence's content words in a different order) and `lcs_words` (the longest run of shared content words, allowing gaps). A flag means wording or structure was carried over from the source. Rewrite from your understanding of the idea, or quote and cite the distinctive phrases (see `paraphrase-and-originality.md`). The purpose is honest attribution, never disguising copied text.

### inventory
Lists protected items and meaning cues with their positions, and `repeated_openers` (three or more consecutive sentences starting with the same word, a clarity issue). It is useful for planning a revision of dense technical text.

## Reporting
Count states in a Case C report:
- **VERIFIED** - the helper returned PASS for the exact delivered text in this session.
- **ESTIMATED** - your own count.
- **NOT_CHECKED** - no count was made.

Report helper results exactly as returned. Never describe an estimate as verified, and never claim a check ran when it did not.
