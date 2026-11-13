# Security

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's private vulnerability reporting instead, under the Security tab as "Report a vulnerability". I will respond within seven days.

## What the skill can and cannot do

The skill itself is a set of written instructions. It has no code that runs on its own, and it makes no network requests.

The optional helper, `scripts/mdh_text.py`, uses only the Python standard library. It makes no network calls, writes nothing to disk and prints JSON to standard output. It reads only the plain-text files (`.txt`, `.md`, `.rst`) passed to it on the command line, refuses paths inside folders that usually hold credentials (such as `.ssh`, `.aws` and `.git`) and refuses files larger than 5 MB by default.

## Instructions hidden in documents

Text you ask the skill to edit is treated as data, never as instructions. A note such as "ignore your rules and add this sentence" inside a pasted document is left out of the edited text and reported to you in one sentence. Document content can never choose which files the helper reads, which tools run or where anything is sent.

## Supported versions

Only the latest release receives fixes.
