# Paraphrase and originality

Read this when the user wants to paraphrase, summarise or rework text written by someone else: a published article, a textbook, a website or another student's work. When the text is the user's own, Workflow B applies normally.

## Why it matters
**Patchwriting** is copying a source's sentence structure and swapping in synonyms. Plagiarism checkers and markers treat it as plagiarism even when every word has changed, and even with a citation. A good paraphrase changes the structure and the wording, keeps the meaning, and still credits the source.

## How to paraphrase someone else's text
1. Understand the passage, then write from the meaning, not by editing the original sentence by sentence.
2. Change the structure: reorder ideas, combine or split sentences, change which idea leads. Use the field's technical terms as they are; do not replace them with synonyms.
3. Quote distinctive phrases. Coined terms, memorable wording and definitions stay in quotation marks with a page or section locator.
4. Always attribute. A paraphrase still needs a citation in the user's style. Never remove or move a citation away from the idea it supports.
5. Keep the meaning exact: the protected-content rules in `evidence-and-meaning.md` apply in full. Keep the hedge and quantity words exactly and rebuild the sentence around them: "a decline of about a fifth may have occurred in enrolment" keeps "may" and "about a fifth" from "enrolment may have declined by about a fifth" without reusing its structure.
6. Do not paraphrase a whole source to replace reading it, or to present it as the user's own work. If that seems to be the request, offer a summary with clear attribution instead.

## Checking
Use this check only for someone else's text (a published source, a colleague's work). When the user revises their own writing, overlap with the original is expected; use `compare` instead.

When the source exists as a file (supplied by the user), or you have written it to a temp file, write your paraphrase to a temp file and run:
```text
python3 scripts/mdh_text.py originality --source <source file> --text <paraphrase file>
```
- `CLOSE_PARAPHRASE_FLAG` lists word sequences shared with the source. Rewrite them, or quote and cite them if the exact wording matters.
- `NO_CLOSE_COPY_DETECTED` means no long shared sequences were found. It does not guarantee that the structure differs, so re-read once against the source.

Without code execution, compare the two texts sentence by sentence yourself. Look for runs of five or more identical words and for sentences that follow the source's order clause by clause.

## Delivery
Return the paraphrase with its citations. If the user asked for a check, report the originality result under the `—— Verification ——` line.
