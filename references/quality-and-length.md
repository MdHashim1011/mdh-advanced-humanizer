# Quality and length

Read this before returning R4 and R5 writing, and for R1 to R3 when a length applies.

## Natural, specific writing
- Write for the stated reader. Prefer the precise word, including technical terms the field uses, over a vaguer or rarer one.
- Make paragraphs do work: each develops one point with reasons, mechanisms, evidence or a concrete example.
- Let logic carry transitions; use connectives only where they mark a real relation.
- Vary sentence structure as the content requires. Do not impose patterns, fragments or "burstiness".
- Remove filler and stock phrasing: announcements of what you will do, restatements, empty emphasis, reflexive lists of three. See `clarity-checklist.md` for the full list.
- Keep appropriate academic caution, passive voice in methods, and real lists where they carry meaning. There is no banned-word list. A word is a problem only when it is vague, empty or wrong for the reader.
- Keep the register consistent with the task and, in revisions, with the writer.
- Never add deliberate errors, odd word choices or fake hesitations to seem human. They lower quality.

## Word budgets
Understand the constraint before drafting:
- Its type: exact, maximum, minimum, range or approximate.
- What is excluded, under the user's rules: title, headings, references, captions, quotations.
- The counting convention, if one is named.

If exclusions are not stated, exclude the reference list and a standalone title. A title you were not asked for should not be there at all. Mention exclusions only in a Case C report.

Aim inside the limit, because drafts drift:
| Constraint | Aim for |
| --- | --- |
| Maximum N | about 93-98% of N |
| Minimum N | about 102-107% of N |
| Exact N | N, then adjust locally |
| Range | the middle of the range |
| "About N" | within 5% of N |

For Chinese, Japanese and Korean text, count characters, as word processors do. A Chinese or Japanese 字 limit conventionally includes punctuation, so check against that stricter count. Thai has no spaces, so estimate by syllables or report the count as ESTIMATED.

### Gate
1. Take the final text exactly as you will deliver it: the writing only, with no status lines.
2. **With code execution:** write it with your file-writing tool to a fresh temp folder outside the user's folders and run `budget` (see `helper.md`). Delete the temp file afterwards.
   **Without code execution:** count carefully paragraph by paragraph. The result is ESTIMATED.
3. If it fails, revise using the gap:
   - Cut in this order: announcements and recaps, duplicated explanation, wordy phrasing, secondary examples.
   - Add in this order: deeper explanation of the weakest supplied point, an example from the user's material, a stated limitation.
   - Never cut protected content, required caveats, negations, conditions or citations.
   - Priority: correctness, then required information, then clear organisation, then length.
4. **Honest shortfall:** if reaching a minimum would require repeating a fact, restating a point, or adding content the user did not supply, stop expanding.
   - Deliver the faithful version.
   - Add one integrity sentence after it giving the count and two or three specific pieces of information that would allow the target to be reached.
   - Signs you are padding: the same fact appears twice, a sentence only rephrases the previous one, a closing "in short" recap, or a sentence states the obvious ("the review has not yet taken place").
5. Re-run the gate after revising. Style and length repairs stop after two rounds in total. If the text still fails, deliver the closest faithful version and say so in one integrity sentence.
6. Fixing a meaning error, an invented fact or a misattribution is never limited by the round cap.
7. If you changed the text after the last helper run, run it again before reporting a count.

Report a count only when the user asked for verification (Case C in SKILL.md). Report it under the `—— Verification ——` line, for example:
- `Words: 247 / max 250 (word2019_approx, VERIFIED)`
- `Words: about 250 (ESTIMATED)`

Never write "verified" for an estimate.

## Final checks before returning
- The task is fully answered, the required items are present and the format is as requested.
- Facts, numbers, citations and claims are faithful to the sources or the original (see `evidence-and-meaning.md`).
- The level and audience are appropriate.
- Grammar and spelling are correct in the input's language and spelling variety.
- No paragraph repeats another, no fact is stated twice, and the opening and conclusion each add something.
- There is no title, heading, sign-off, reference list or summary that the user did not ask for and the original did not have.
- The length gate passed, or the shortfall is reported honestly.
- There is no process narration. Verification appears only when asked for, after the `—— Verification ——` line. Integrity notices are one sentence each.
