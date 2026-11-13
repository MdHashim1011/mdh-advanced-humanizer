# Clarity checklist

Read this for humanize, "less robotic", "more natural" and polish requests, and as a final pass on new writing.

Generic prose reads as robotic because it says little: it takes the safest, most average option at every turn. The cure is to make each sentence carry something specific to this writer, this reader and this material. Cutting filler and stating things directly is most of the work.

This is **not** a device for evading AI detectors. Do not swap in rare words, add typos, break grammar or vary sentences at random. Those habits make writing worse and are outside this skill.

## How to use it
1. **Read the whole text first**, then mark problems at three scales: phrase, sentence and paragraph. Some patterns are only visible across a paragraph (every paragraph ends on the same kind of line; three parallel examples in a row; a contrast split over two sentences).
2. **Weigh before editing.** Tier 1 patterns justify an edit wherever they appear. Tier 2 patterns are normal in good writing; act only when they cluster or recur. One "crucial" in a page is fine; five is a pattern.
3. **Rewrite the sentence or paragraph, not the word.** Swapping a listed word for a synonym keeps the emptiness. Ask what the sentence is for, then say that.
4. **Re-scan the result.** Rewrites often reintroduce the same habits in new clothes, most often a new tidy closer, a new triplet or a new "not X but Y". Check once more for those.
5. **Check meaning** with the minimum rules in SKILL.md: every fact, number, hedge, condition and name survives.

## Tier 1 - fix wherever found
| Pattern | Looks like | Fix |
| --- | --- | --- |
| Chat residue | "Certainly!", "Great question", "I hope this helps", "Let me know if you'd like..." in the deliverable | Remove; it belongs to the conversation, not the text |
| Knowledge-cutoff talk | "As of my last update...", "information may have changed", followed by a guess | Remove the disclaimer; if the fact is uncertain, say what is unknown or ask |
| Unfilled placeholder | "[Insert example]", "2026-XX-XX", example.com links | Fill from the user's material or mark clearly as missing; never ship silently |
| Self-description | "This essay will explore...", "In this section, we will discuss...", "I am writing to inform you that..." | Say the thing itself |
| Heading echo | First sentence restates the heading ("Benefits. There are several benefits...") | Start with the first real point |
| Empty importance flag | "It is important to note that", "It is worth mentioning", "It is crucial to highlight" | Delete; if the point matters, the content shows it |
| Stock opener and closer | "In today's fast-paced world", "I hope this finds you well", "I would like to express my gratitude for your attention to this matter" | Start with the point; end with a short real close or none |
| Inflated significance | "stands as a testament to", "plays a pivotal role", "an evolving landscape", "enduring legacy", "marks a turning point" | Say what the thing did, for whom, with what result |
| Hollow conclusion | "In conclusion, X is a complex and important topic" | End on an implication, decision, judgement or answer |
| Vague attribution | "experts argue", "observers note", "many studies show" | Name the source, or drop the attribution and state the claim at the strength the evidence allows |
| Trailing commentary | "..., highlighting its importance", "..., reflecting a broader trend" bolted onto a fact | Delete, or make it a supported claim of its own |
| Staged contrast | "It's not just X, it's Y", "not merely X but Y" when nobody claimed X; a fake alternative set up to be knocked down | State Y directly |
| Rebutting the unraised | "Some may think..., but..." with no one actually thinking it | Delete the strawman; make the point |
| Staged candour | "Honestly?", "Here's the thing:", "Let's be real" as a run-up | Start with the point |

## Tier 2 - act when clustered or recurring
| Pattern | Looks like | Fix |
| --- | --- | --- |
| Inflated vocabulary | "delve", "showcase", "underscore", "tapestry", "multifaceted", "foster", "leverage", "robust", "seamless" | Plain word where it fits ("examine", "show", "use"). Keep the technical sense ("robust standard errors") |
| Copula avoidance | "serves as", "stands as", "boasts", "features" for "is"/"has" | Use "is" or "has" |
| Reflexive triplet | "fast, efficient and reliable" when only one is supported; three examples every time | Keep what the material supports; two or four are fine |
| Tidy closer | A short punchy line ending every paragraph or section; aphorisms ("Data is the new oil") | Keep at most one where it earns its place; otherwise end on content |
| Repeated openers | Several sentences or paragraphs in a row starting the same way | Vary by restructuring around the content, not by rotating stock openers |
| Connective chain | "Furthermore... Additionally... Moreover..." opening sentence after sentence | Let logic connect; keep connectives that mark a real relation (contrast, cause, condition) |
| Over-signposting | "Firstly... Secondly... In conclusion" in a short text; the same template in any language (首先/其次/再次/最后, "En primer lugar... Por último"); a slogan as the last line | Remove unless the genre expects it; let each paragraph's topic carry the order, and end on a concrete point |
| Hedge stack | "may possibly suggest that it could" | One hedge, matched to the evidence |
| Empty intensifier | "very", "truly", "incredibly", "significantly" without statistics | Delete, or give the measure |
| Abstract nouns | "the implementation of the utilisation of resources" | Verbs and concrete subjects: "using resources" |
| Vague connection | "is associated with", "in connection with" where the actual relation is known | Name the relation (funded, wrote, preceded), keeping associative wording where the evidence is associative |
| Synonym cycling | "the study... the research... the investigation" for one paper | One consistent term |
| Generic example | "for example, in many industries" | A concrete example from the user's material, or a labelled hypothetical |
| Uniform paragraph shape | Every paragraph the same length and claim-explain-summary pattern | Let length follow content |
| Method narration | "Drawing on a range of sources, I have compiled..." | Remove unless the reader needs the method |
| Chat formatting in prose | Bold scattered through sentences, Title Case Headings, emoji bullets, headings on a short answer, horizontal rules | The formatting the genre and user expect; plain paragraphs for most prose |
| Dash habit | An em dash in most sentences | Commas, colons, brackets or a new sentence where they fit better; keep dashes that mark a real break, and keep the writer's own dash habit |

## Clarity moves that make text read as written by a person
- **Given before new.** Start a sentence with what the reader already knows and end with the new information. It makes paragraphs flow without connectives.
- **Lead with the answer** in emails, messages and replies: the decision, request or date first, then only the context the reader does not already have. Do not re-explain what they just told you.
- **Concrete subject, active verb** where the actor matters; passive where the actor is unknown or irrelevant (often in methods).
- **Define or expand a term once**, at first use, only if the reader needs it.
- **Contractions follow register:** natural in emails, messages and personal writing; usually avoided in formal academic prose unless the writer uses them.
- **Vary sentence length because the content varies**, never on a schedule.

## Do not edit
- Quotations, titles of works, proper names, product names, legal or regulatory wording, and any term the user listed as protected.
- A watched phrase that is being discussed rather than used ("the word 'leverage' is overused").
- Technical vocabulary that only looks inflated ("robust", "significant" with a test, "framework" as a named method).
- Code, URLs, file paths, math, LaTeX commands, citation keys, reference lists, block quotes and captions, unless the user asked for them to be edited.
- Details that carry the writer's voice: unusual specifics, mixed feelings, dialect and spelling variety, deliberate repetition, real asides and humour.

## Voice
- With a writing sample, match its person, register, sentence length range, punctuation habits (dashes, semicolons, exclamation marks), contractions and typical openings. The sample outranks this checklist: if the writer uses em dashes or triplets, keep using them at their rate.
- Without a sample, let the genre set the voice: personal writing keeps the writer's opinions and asides; reports and academic writing stay neutral. Never add opinions, feelings or reactions the writer did not express.

## How far to go
- Keep every fact, number, date, condition and name.
- Greetings and sign-offs: keep the writer's own choice in a plain edit. A humanize, "less robotic" or "friendlier" request is a tone change, so a stiff formula ("Dear Team", "Best regards" on a quick internal note) may become the natural form for that relationship ("Hi team", "Thanks"). Keep formal forms where the relationship needs them (a first letter to an employer, a complaint, legal or academic correspondence).
- Shorter is usually better: robotic text is mostly filler. Do not add content to replace what you cut.
- If a sentence carries a hedge or condition, rewrite around it, never through it.

These patterns are signs of weak writing, not proof of anything: people write this way too, and good writing can contain a few of them.
