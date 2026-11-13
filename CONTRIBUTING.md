# Contributing

This guide is for maintainers of the MdH Advanced Humanizer skill. It covers the three changes made most often: adding a clarity pattern, fixing a bug with a regression test, and cutting a release.

## Layout

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Main instructions. Body must stay under 1,800 words. |
| `PORTABLE.md` | Single-file instructions for platforms without skill folders. Must stay under 8,000 characters. |
| `references/` | Detail loaded on demand by the routes in `SKILL.md`. |
| `scripts/mdh_text.py` | Optional helper (Python 3 standard library only). |
| `scripts/tests/` | `unittest` suite for the helper. |
| `tools/validate_package.py` | Release checks. |
| `.claude-plugin/`, `.cursor-plugin/`, `agents/` | Platform manifests. |

## Adding a clarity pattern

Clarity patterns live in `references/clarity-checklist.md`. A pattern earns a place only when it describes a clarity problem a reader would notice, not a word that happens to be common in generated text.

Every new row must give:

1. **The clarity problem it reflects.** Say what the reader loses: the point arrives late, the claim is stronger than the evidence, the sentence announces content instead of giving it, the subject is hidden in an abstract noun. If you cannot name the problem, the pattern does not belong in the checklist.
2. **A restructuring fix.** Describe how to rebuild the sentence or paragraph so the problem goes away, for example "state Y directly", "start with the first real point", "name the source or drop the attribution". **Never give a synonym swap as the fix.** Replacing "crucial" with "key" keeps the emptiness and teaches the model to rotate vocabulary, which makes writing worse.
3. **A tier.**
   - Tier 1: the pattern is a problem wherever it appears (chat residue, self-description, unfilled placeholders).
   - Tier 2: the pattern is normal in good writing and is a problem only when it clusters or recurs (lists of three, transition words, intensifiers).
4. **An example** in the "Looks like" column, short and generic. Do not paste text from a real person's work.

Before merging:

- Check that the fix cannot change meaning. If it touches hedges, negations, numbers, conditions or attribution, it conflicts with the minimum rules in `SKILL.md`; rewrite it.
- If the pattern also matters on platforms without the reference files, add a short line to the "Natural, specific writing" list in `PORTABLE.md` and confirm the file is still under 8,000 characters.
- Run the validator.

## Fixing a bug

Every bug fix comes with a regression test. No exceptions for "small" fixes.

### Helper script bugs

1. Reproduce the bug with the smallest input you can. Keep the input in the test itself, not in an external file, unless encoding or byte order is the point of the test.
2. Add a test method to `scripts/tests/test_mdh_text.py` that fails before the fix. Name it after the behaviour, for example `test_spaced_ellipsis_is_not_three_words`, and put the issue number in the docstring.
3. Use the existing `run_cli` helper to test through the command-line interface when the bug is in argument handling, exit codes or JSON shape. Call module functions directly when the bug is in counting or comparison logic.
4. Fix the bug, then run the whole suite. A fix that breaks another test is not finished.
5. If a case cannot be fixed yet, add it with `@unittest.expectedFailure` and a comment explaining the limitation, so the gap stays visible.

### Instruction bugs

For a "Meaning changed" or "Writing quality" report against the instructions:

1. Record the original input, the request and the faulty output from the issue.
2. Find the rule that should have prevented it. If a rule exists but was missed, make it more prominent or more specific. If no rule exists, add one in the narrowest file that covers the case.
3. Re-run the reported input on at least one platform and record the before and after outputs in the pull request.
4. If the fix adds words to `SKILL.md`, check the body word count with the validator.

## Release checklist

1. Run the validator from a neutral directory and confirm `"ok": true`:
   ```text
   python3 -I tools/validate_package.py <skill-root>
   py -I tools\validate_package.py <skill-root>        (Windows)
   ```
2. Run the unit tests:
   ```text
   python3 -I -B -m unittest discover -s scripts/tests
   ```
3. Bump the version in all five places. The validator fails if any of them differ:
   - `SKILL.md` frontmatter, `metadata.version`
   - `scripts/mdh_text.py`, `VERSION` constant
   - `.claude-plugin/plugin.json`, `version` (also update the entry in `.claude-plugin/marketplace.json`)
   - `.cursor-plugin/plugin.json`, `version`
   - `CHANGELOG.md`, top entry heading
4. Update the version string in the `PORTABLE.md` title and in `references/helper.md` if the helper changed.
5. Update `CHANGELOG.md` with a dated entry describing what changed for users, grouped into skill instructions, helper script and packaging.
6. Confirm the CI workflow passes on all operating systems and Python versions.
7. Build the upload zip from a clean checkout so that ignored files (`__pycache__`, workspace folders) are not included.

## Writing style for this repository

Write in plain, specific English. Describe what a rule does and why. Avoid promotional language in documentation and changelog entries.
