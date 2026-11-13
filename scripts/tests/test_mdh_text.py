"""Regression and interface tests for mdh_text.py 0.5.1 (standard library only).

Run:  py -I -m unittest discover -s "<skill>/scripts/tests"   (or python3 -I -m unittest ...)
"""
import importlib.util
import io
import json
import os
import random
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "mdh_text.py")
_spec = importlib.util.spec_from_file_location("mdh_text", SCRIPT)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

PERF_LIMIT = float(os.environ.get("MDH_PERF_LIMIT", "8"))  # CPU seconds; target is < 5 on a desktop


def run_cli(args, stdin_bytes=None):
    out = io.BytesIO()
    old_out, old_in = sys.stdout, sys.stdin
    wrapper = io.TextIOWrapper(out, encoding="utf-8")
    in_wrapper = io.TextIOWrapper(io.BytesIO(stdin_bytes or b""), encoding="utf-8")
    sys.stdout = wrapper
    if stdin_bytes is not None:
        sys.stdin = in_wrapper
    try:
        code = m.main(args)
        wrapper.flush()
        data = out.getvalue()
    finally:
        sys.stdout, sys.stdin = old_out, old_in
        wrapper.detach()
        in_wrapper.detach()
    return code, json.loads(data.decode("utf-8"))


def status(o, r, auth=()):
    return m.compare_texts(o, r, auth)


def codes(res):
    return [f["code"] for f in res["findings"]]


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="mdh-test-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, name, content, binary=False):
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(content if binary else content.encode("utf-8"))
        return path


# ----------------------------------------------------------------------------- counting

class Counting(unittest.TestCase):
    def w(self, text, conv="word2019_approx"):
        return m.count_words(text, conv)

    def test_cjk_counts_characters(self):
        self.assertEqual(self.w("我们研究了气候变化的影响。"), 12)
        self.assertEqual(self.w("私は学生です。"), 6)
        self.assertEqual(self.w("한국어 문장"), 5)

    def test_cjk_essay_cannot_pass_small_limit(self):
        essay = "我们研究了气候变化的影响。" * 40  # 480 characters, previously counted as 1 word per run
        self.assertGreater(self.w(essay), 250)

    def test_thai_estimate_and_warning(self):
        r = m.measure("ฉันรักภาษาไทย", "word2019_approx")
        self.assertEqual(r["count"], 3)
        self.assertTrue(any("thai_estimate" in w for w in r["warnings"]))

    def test_dash_variants(self):
        for ch in ("—", "–", "‒", "―"):
            self.assertEqual(self.w("a%sb" % ch), 2, repr(ch))
        self.assertEqual(self.w("a − b"), 2)
        self.assertEqual(self.w("—"), 0)

    def test_spaced_ellipsis(self):
        self.assertEqual(self.w("wait . . . what"), 2)
        self.assertEqual(self.w("wait... what"), 2)

    def test_markdown_stripped_by_default(self):
        self.assertEqual(m.measure("- one\n- two", "word2019_approx")["count"], 2)
        self.assertEqual(m.measure("| a | b |\n|---|---|\n| c | d |", "word2019_approx")["count"], 4)
        self.assertEqual(m.measure("text[^1]\n\n[^1]: note here", "word2019_approx")["count"], 3)
        self.assertEqual(m.measure("- one\n- two", "word2019_approx", markdown=False)["count"], 4)

    def test_thematic_breaks_and_setext(self):
        self.assertEqual(m.strip_markdown("* * *").strip(), "")
        self.assertEqual(m.measure("* * *\n\n- - -\n\n***\n", "word2019_approx")["count"], 0)
        self.assertEqual(m.measure("Title\n=====\n\nBody here.", "word2019_approx")["count"], 3)

    def test_html_comment_not_counted(self):
        self.assertEqual(m.measure("Body text.\n<!-- mdh-status -->\n", "word2019_approx")["count"], 2)

    def test_approx_exact_arithmetic(self):
        self.assertEqual(m.evaluate_constraint(115, "approx", 100, tolerance_pct=15)[0], "PASS")
        self.assertEqual(m.evaluate_constraint(230, "approx", 200, tolerance_pct=15)[0], "PASS")
        self.assertEqual(m.evaluate_constraint(460, "approx", 400, tolerance_pct=15)[0], "PASS")
        self.assertEqual(m.evaluate_constraint(116, "approx", 100, tolerance_pct=15)[0], "FAIL")
        bad = [(t, p) for t in range(1, 2001, 7) for p in (5, 10, 15, 20, 7.5)
               if m.evaluate_constraint(int(round(t * (1 + p / 100.0))), "approx", t, tolerance_pct=p)[0] == "FAIL"
               and (t * (100 + p)) % 100 == 0]
        self.assertEqual(bad, [])


# --------------------------------------------------------------------------- exclusions

class Exclusions(unittest.TestCase):
    BODY = "Body text has five words.\n\n"
    REFS = "Smith, J. (2020). A paper title here. Journal.\nDoe, A. (2019). Another one. Press.\n"

    def cnt(self, text, exclude, **kw):
        return m.measure(text, "word2019_approx", exclude, **kw)

    def test_reference_heading_variants(self):
        for h in ["References", "REFERENCES", "Reference List:", "Sources", "**Bibliography**", "## References",
                  "**References**", "References and Notes", "Works Cited", "Bibliography.", "Citations",
                  "REFERENCES "]:
            self.assertEqual(self.cnt(self.BODY + h + "\n" + self.REFS, ["references"])["count"], 5, h)

    def test_toc_does_not_swallow_document(self):
        doc = ("Contents\nIntroduction\nMethods\nReferences\n\nIntroduction\n\nThis essay argues many things in "
               "many words across paragraphs.\n\nMethods\n\nWe did several careful things here.\n\nReferences\n\n"
               "Smith, J. (2020). Title.\n")
        r = self.cnt(doc, ["references"])
        self.assertEqual(r["count"], 22)

    def test_stray_references_line_not_excluded(self):
        doc = "Intro para.\n\nReferences\n\nare important, as this paragraph explains in many words.\n"
        self.assertEqual(self.cnt(doc, ["references"])["excluded"], [])

    def test_appendix_after_references_counted(self):
        doc = (self.BODY + "References\n" + self.REFS +
               "\nAppendix A\n\nAppendix body has many words that should count here.\n")
        self.assertEqual(self.cnt(doc, ["references"])["count"], 16)
        doc2 = self.BODY + "## References\n" + self.REFS + "\n### Appendix A\nAppendix body has words here.\n"
        self.assertEqual(self.cnt(doc2, ["references"])["count"], 12)

    def test_excluded_share_warning(self):
        r = self.cnt(self.BODY + "References\n" + self.REFS, ["references"])
        self.assertGreater(r["excluded_share"], 0.3)
        self.assertTrue(any("exclusions removed" in w for w in r["warnings"]))

    def test_title_heuristic(self):
        def title_excluded(doc):
            return any(e["kind"] == "title" for e in self.cnt(doc, ["title"])["excluded"])
        self.assertTrue(title_excluded("The Results Were Clear\n\nMore text follows here.\n"))
        self.assertTrue(title_excluded("My Title\n========\n\nBody words here.\n"))
        self.assertFalse(title_excluded("Thanks for your help with the project last week"))
        self.assertFalse(title_excluded("Climate change is accelerating (Smith, 2020)\n\nNext para.\n"))
        self.assertFalse(title_excluded("- first bullet item\n\n- second\n"))
        self.assertFalse(title_excluded("Hi Sarah\n\nThanks for the notes.\n"))
        self.assertFalse(title_excluded("Dear team\n\nThe meeting moved.\n"))

    def test_captions(self):
        for c in ["Figure 1. Growth over time.", "Fig. 2: Map", "Table 3 - Results", "Figure S1. Supp",
                  "Figure 1.2. Detail", "*Figure 1.* Caption", "Table I. Roman", "Figure 10a: x"]:
            self.assertEqual(self.cnt("Body here.\n" + c + "\n", ["captions"])["count"], 2, c)
        self.assertEqual(self.cnt("Body here.\nFigure 1 shows growth.\n", ["captions"])["count"], 6)

    def test_unclosed_fence(self):
        doc = "Body words.\n```\ncode\nMore body words that should count.\n"
        r = self.cnt(doc, ["references"])
        self.assertEqual(r["count"], r["input_words_before_selection"])
        self.assertTrue(any("unclosed code fence" in w for w in r["warnings"]))
        r2 = self.cnt(doc, ["code"])
        self.assertLess(r2["count"], r2["input_words_before_selection"])
        self.assertTrue(any("unclosed code fence" in w for w in r2["warnings"]))

    def test_section_selection_normalises(self):
        self.assertEqual(self.cnt("## Intro:\nIntro words.\n", [], sections=["Intro"])["count"], 2)
        self.assertEqual(self.cnt("## 1. Introduction\nIntro words.\n", [], sections=["Introduction"])["count"], 2)


# ---------------------------------------------------------------------------- sentences

class Sentences(unittest.TestCase):
    def test_label_letter_ends_sentence(self):
        s = [x["text"] for x in m.split_sentences("Doses went to group A. The rest got placebo.")]
        self.assertEqual(len(s), 2)

    def test_initials_and_abbreviations_kept(self):
        self.assertEqual(len(m.split_sentences("Values: A. Smith and J. Doe wrote it. It was good.")), 2)
        self.assertEqual(len(m.split_sentences("Results are in Fig. 2. They show growth.")), 2)


# ------------------------------------------------------------------------------ compare

MUST_FLAG = [
    ("increased->decreased", "Treatment increased blood pressure in adults.", "Treatment decreased blood pressure in adults."),
    ("raised->lowered", "The drug raised cholesterol levels in patients.", "The drug lowered cholesterol levels in patients."),
    ("significant->insignificant", "The effect was significant in the sample.", "The effect was insignificant in the sample."),
    ("more than->less than", "More than half of participants agreed with the policy.", "Less than half of participants agreed with the policy."),
    ("more->less", "Sales were more than expected this quarter.", "Sales were less than expected this quarter."),
    ("before->after", "Symptoms appeared before the vaccination in most cases.", "Symptoms appeared after the vaccination in most cases."),
    ("inconclusive->negative", "The test results were inconclusive for the second cohort.", "The test results were negative for the second cohort."),
    ("twelve->twenty", "Twelve patients withdrew from the trial early.", "Twenty patients withdrew from the trial early."),
    ("% -> percentage points", "Unemployment rose by 5% last year.", "Unemployment rose by 5 percentage points last year."),
    ("percent -> percentage points", "Unemployment rose by 5 percent last year.", "Unemployment rose by 5 percentage points last year."),
    ("swapped groups (than)", "The control group scored higher than the treatment group.", "The treatment group scored higher than the control group."),
    ("swapped groups A/B", "Group A received the drug and group B received placebo.", "Group B received the drug and group A received placebo."),
    ("may->will", "The policy may reduce emissions in cities.", "The policy will reduce emissions in cities."),
    ("might->will likely", "The policy might reduce emissions in cities.", "The policy will likely reduce emissions in cities."),
    ("unlikely->likely", "The policy is unlikely to reduce emissions.", "The policy is likely to reduce emissions."),
    ("higher->lower", "Women reported higher stress than men.", "Women reported lower stress than men."),
    ("5 mg->5 grams", "Patients received 5 mg of the drug daily.", "Patients received 5 grams of the drug daily."),
    ("km->miles", "The trail is 5 kilometres long.", "The trail is 5 miles long."),
    ("at least->at most", "At least 40 people attended the meeting.", "At most 40 people attended the meeting."),
    ("up to->at least", "The battery lasts up to 10 hours.", "The battery lasts at least 10 hours."),
    ("some->all", "Some students passed the exam.", "All students passed the exam."),
    ("citation moved", "Smoking causes cancer (Smith, 2020). Exercise improves mood.", "Smoking causes cancer. Exercise improves mood (Smith, 2020)."),
    ("associated->responsible for", "Coffee intake was associated with longer life.", "Coffee intake was responsible for longer life."),
    ("predicts->causes", "Diet predicts weight gain.", "Diet causes weight gain."),
    ("causes->linked", "Smoking causes cancer.", "Smoking is linked to cancer."),
    ("rarely->usually", "Patients rarely reported pain.", "Patients usually reported pain."),
    ("always->never", "The system always logs errors.", "The system never logs errors."),
    ("year", "The law passed in 2019.", "The law passed in 2021."),
    ("numbers swapped between sentences", "Group A had 30 members. Group B had 50 members.", "Group A had 50 members. Group B had 30 members."),
    ("0.5->5", "The rate was 0.5 per day.", "The rate was 5 per day."),
    ("billion->million", "The project cost 3 billion dollars.", "The project cost 3 million dollars."),
    ("$3 million->$3", "Revenue was $3 million.", "Revenue was $3."),
    ("50k->50", "Salary rose to 50k.", "Salary rose to 50."),
    ("5x->5%", "Speed improved 5x.", "Speed improved 5%."),
    ("tenfold->twofold", "Risk rose tenfold.", "Risk rose twofold."),
    ("first->second", "This is the first trial of its kind.", "This is the second trial of its kind."),
    ("1st->2nd", "She finished 1st in the race.", "She finished 2nd in the race."),
    ("not all -> all not", "Not all participants completed the survey.", "All participants did not complete the survey."),
    ("no->not (scope)", "No evidence showed the drug was unsafe.", "Evidence showed the drug was not safe."),
    ("unless->if", "The alarm sounds unless the door is locked.", "The alarm sounds if the door is locked."),
    ("only if->if", "Access is granted only if the badge is valid.", "Access is granted if the badge is valid."),
    ("must->may", "Applicants must submit a form.", "Applicants may submit a form."),
    ("should->must", "Users should change passwords yearly.", "Users must change passwords yearly."),
    ("reliable->unreliable", "The reviewers found the method reliable.", "The reviewers found the method unreliable."),
    ("approved->rejected", "The committee approved the proposal.", "The committee rejected the proposal."),
    ("better->worse", "Model A performs better than model B.", "Model A performs worse than model B."),
    ("quote altered", "She said \"we will win\" at the rally.", "She said \"we shall win\" at the rally."),
    ("dropped clause", "The vaccine was effective in adults but not in children.", "The vaccine was effective in adults and children."),
    ("dropped sentence", "First claim is here. Second claim adds a caveat about safety.", "First claim is here."),
    ("p-value", "The difference was significant (p = 0.03).", "The difference was significant (p = 0.3)."),
    ("p< -> p>", "The effect held (p < .05).", "The effect held (p > .05)."),
    ("sign", "The temperature was -5 degrees.", "The temperature was 5 degrees."),
    ("unicode minus", "Change was −3 points.", "Change was 3 points."),
    ("range", "Doses ranged 10–20 mg.", "Doses ranged 10–15 mg."),
    ("hedge moved across sentences", "The drug may reduce pain. It lowers fever.", "The drug reduces pain. It may lower fever."),
    ("negation moved across sentences", "Drug A did not work. Drug B worked.", "Drug A worked. Drug B did not work."),
    ("citation year", "This was shown before (Lee, 2019).", "This was shown before (Lee, 2018)."),
    ("by->to", "Costs fell by 5% in 2020.", "Costs fell to 5% in 2020."),
    ("half->a third", "Half of users quit.", "A third of users quit."),
    ("participants swapped", "The trainers interviewed the coordinators.", "The coordinators interviewed the trainers."),
]

KNOWN_MISSES = [  # missed up to 0.4.1; caught by CUE_MOVED since 0.4.2
    # Causal and associational links swapped between two objects in one sentence keep every count equal.
    ("association/cause swapped objects", "Smoking is linked to cancer and causes heart disease.",
     "Smoking causes cancer and is linked to heart disease."),
    # A hedge that moves into the other clause when one sentence is split into two.
    ("hedge moved in split", "The drug may reduce pain, and it lowers fever.", "The drug reduces pain. It may lower fever."),
]

MUST_NOT_FLAG = [
    ("identical", "The study included 40 adults.", "The study included 40 adults."),
    ("synonym verb", "The study included 40 adults.", "The study enrolled 40 adults."),
    ("passive voice", "Researchers analysed the data in 2020.", "The data were analysed by researchers in 2020."),
    ("Forty->40", "Forty adults took part.", "40 adults took part."),
    ("contraction", "The model does not converge.", "The model doesn't converge."),
    ("can't->cannot", "We can't confirm this.", "We cannot confirm this."),
    ("no->not any", "There was no change.", "There was not any change."),
    ("thousands separator", "The sample had 1000 people.", "The sample had 1,000 people."),
    ("percent spaced", "The rate was 5%.", "The rate was 5 %."),
    ("percent spelled", "The rate was 5%.", "The rate was 5 percent."),
    ("per cent", "The rate was 5%.", "The rate was 5 per cent."),
    ("split sentence", "The team collected samples in May and analysed them in June using a new assay.",
     "The team collected samples in May. They analysed them in June using a new assay."),
    ("merge sentences", "The team collected samples. They analysed them later.", "The team collected samples and analysed them later."),
    ("fronted clause", "Method A was faster than method B in all trials.", "In all trials, method A was faster than method B."),
    ("among removed", "Among the options, the first was cheapest.", "The first option was the cheapest."),
    ("each->every", "Each participant signed a form.", "Every participant signed a form."),
    ("often->frequently", "Users often forget passwords.", "Users frequently forget passwords."),
    ("when->whenever", "Errors appear when the cache is full.", "Errors appear whenever the cache is full."),
    ("if->provided that", "It works if the key is set.", "It works provided that the key is set."),
    ("shows->reveals", "Figure 2 shows the trend.", "Figure 2 reveals the trend."),
    ("add that", "He said the plan worked.", "He said that the plan worked."),
    ("date format", "It started on 5 May 2020.", "It started on May 5, 2020."),
    ("all->every one of", "All samples passed.", "Every one of the samples passed."),
    ("improved->got better", "Results improved after tuning.", "Results got better after tuning."),
    ("typo fix", "The resluts were clear.", "The results were clear."),
    ("list merge", "We used three tools. These were A, B and C.", "We used three tools: A, B and C."),
    ("over non-directional", "Over the years, John helped Mary.", "John helped Mary over the years."),
    ("May month", "The survey ran in May 2020.", "The survey ran in spring 2020."),
    ("higher->increased", "Scores were higher in 2021.", "Scores increased in 2021."),
    ("lead metal", "Water contained lead from old pipes.", "Water contained lead from aging pipes."),
    ("rise->increase", "There was a sharp rise in prices.", "Prices saw a sharp increase."),
    ("after reorder", "After the meeting, Anna emailed Ben.", "Anna emailed Ben after the meeting."),
    ("may->might", "The rule may apply.", "The rule might apply."),
    ("show->demonstrate", "The data show a trend.", "The data demonstrate a trend."),
    ("indicate->suggest", "The data indicate a trend.", "The data suggest a trend."),
    ("p = .04 -> p = 0.04", "It was significant (p = .04).", "It was significant (p = 0.04)."),
]


class CompareFlags(unittest.TestCase):
    def test_meaning_changes_are_flagged(self):
        missed = [n for n, o, r in MUST_FLAG if status(o, r)["status"] == "NO_FLAG_DETECTED"]
        self.assertEqual(missed, [])

    def test_harmless_edits_are_not_flagged(self):
        noisy = [(n, codes(status(o, r))) for n, o, r in MUST_NOT_FLAG
                 if status(o, r)["status"] != "NO_FLAG_DETECTED"]
        self.assertEqual(noisy, [])

    def test_harmless_edits_never_literal_failure(self):
        for n, o, r in MUST_NOT_FLAG + [("role", "We recruited 40 participants.", "We recruited 40 people.")]:
            self.assertNotEqual(status(o, r)["status"], "DETERMINISTIC_LITERAL_FAILURE", n)

    def test_former_known_misses_now_flagged(self):
        missed = [n for n, o, r in KNOWN_MISSES if status(o, r)["status"] == "NO_FLAG_DETECTED"]
        self.assertEqual(missed, [])
        for n, o, r in KNOWN_MISSES:
            self.assertIn("CUE_MOVED", codes(status(o, r)), n)

    def test_cue_moved_negation_between_clauses(self):
        self.assertIn("CUE_MOVED", codes(status(
            "Exercise did not improve mood, but it reduced stress.",
            "Exercise improved mood but did not reduce stress.")))

    def test_cue_moved_not_raised_for_faithful_rewording(self):
        for o, r in [("The drug may reduce pain.", "Pain may be reduced by the drug."),
                     ("Smoking is linked to cancer.", "Cancer is linked to smoking."),
                     ("Exercise did not improve mood, but it reduced stress.",
                      "Exercise reduced stress but did not improve mood."),
                     ("The results suggest that sleep improved and anxiety declined.",
                      "Sleep improved and anxiety declined, the results suggest.")]:
            self.assertNotIn("CUE_MOVED", codes(status(o, r)), r)

    def test_specific_codes(self):
        self.assertIn("DIRECTION_REVERSED", codes(status("Costs increased.", "Costs decreased.")))
        self.assertIn("LABEL_ROLES_SWAPPED", codes(status(MUST_FLAG[11][1], MUST_FLAG[11][2])))
        self.assertIn("NEGATION_SCOPE_CHANGED", codes(status(
            "Not all participants completed the survey.", "All participants did not complete the survey.")))
        self.assertIn("POLARITY_OR_DIRECTION_CHANGED", codes(status(
            "The method was reliable.", "The method was unreliable.")))
        self.assertIn("UNIT_CHANGED", codes(status("Patients received 5 mg daily.", "Patients received 5 g daily.")))
        self.assertIn("HEDGE_CHANGED", codes(status("It is unlikely to work.", "It is likely to work.")))


class Authorization(TempDirCase):
    def test_pair_authorizes_literal_change(self):
        res = status("Patients received 5 mg daily.", "Patients received 5 g daily.", [("5 mg", "5 g")])
        self.assertEqual(res["status"], "NO_FLAG_DETECTED")

    def test_pair_must_match_both_sides(self):
        res = status("Patients received 5 mg daily.", "Patients received 5 g daily.", [("5 mg", "6 g")])
        self.assertEqual(res["status"], "DETERMINISTIC_LITERAL_FAILURE")

    def test_cue_findings_cannot_be_authorized(self):
        res = status("The drug may not reduce pain.", "The drug reduces pain.", [("may not", "reduces")])
        self.assertNotEqual(res["status"], "NO_FLAG_DETECTED")

    def test_none_string_does_not_authorize(self):
        res = status("Patients received 5 mg daily.", "Patients received 5 daily.", [("None", "5")])
        self.assertEqual(res["status"], "DETERMINISTIC_LITERAL_FAILURE")

    def test_deletion_pair(self):
        res = status("This was shown (Lee, 2019). Next point.", "This was shown. Next point.", [("(Lee, 2019)", "")])
        self.assertNotIn(True, [f["literal"] and not f["authorized"] for f in res["findings"]])

    def _auth_file(self, payload):
        return self.write("auth.json", json.dumps(payload))

    def test_cli_rejects_blank_entry(self):
        o, r = self.write("o.txt", "The drug may not reduce pain."), self.write("r.txt", "The drug reduces pain.")
        for payload in ({"authorized": [{"from": " ", "to": "x"}]}, {"authorized": [{"from": "", "to": ""}]},
                        {"authorized": [" "]}, {"authorized": ["None"]}, {"authorized": [{"from": "a"}]}):
            code, out = run_cli(["compare", "--original", o, "--revised", r, "--authorized", self._auth_file(payload)])
            self.assertEqual(code, 3, payload)
            self.assertEqual(out["error"]["type"], "INPUT_ERROR")

    def test_cli_authorized_must_be_json(self):
        o, r = self.write("o.txt", "A."), self.write("r.txt", "B.")
        a = self.write("auth.txt", json.dumps({"authorized": []}))
        code, out = run_cli(["compare", "--original", o, "--revised", r, "--authorized", a])
        self.assertEqual(code, 3)


# ----------------------------------------------------------------------------- CLI / IO

class Cli(TempDirCase):
    def test_version_and_envelope(self):
        self.assertEqual(m.VERSION, "0.5.1")
        f = self.write("a.md", "One two three.")
        code, out = run_cli(["count", "--file", f])
        self.assertEqual((code, out["command"], out["version"], out["count"]), (0, "count", "0.5.1", 3))

    def test_file_is_required(self):
        code, out = run_cli(["budget", "--type", "max", "--target", "5"])
        self.assertEqual(code, 2)
        self.assertEqual(out["command"], "budget")
        self.assertEqual(out["error"]["type"], "USAGE_ERROR")

    def test_explicit_stdin(self):
        code, out = run_cli(["count", "--file", "-"], stdin_bytes=b"one two")
        self.assertEqual((code, out["count"]), (0, 2))

    def test_empty_input_is_not_verified(self):
        f = self.write("empty.md", "")
        code, out = run_cli(["budget", "--type", "max", "--target", "250", "--file", f])
        self.assertEqual(code, 1)
        self.assertEqual((out["status"], out["verification_state"]), ("FAIL", "NOT_RUN"))
        self.assertIn("no words counted", out["warnings"])

    def test_budget_states(self):
        f = self.write("t.md", "one two three four five")
        code, out = run_cli(["budget", "--type", "max", "--target", "5", "--file", f])
        self.assertEqual((code, out["status"], out["verification_state"]), (0, "PASS", "VERIFIED"))
        code, out = run_cli(["budget", "--type", "max", "--target", "4", "--file", f])
        self.assertEqual((code, out["status"], out["verification_state"], out["delta"]), (1, "FAIL", "FAILED", 1))
        self.assertNotIn("delivered_verification", out)
        code, out = run_cli(["budget", "--type", "max", "--target", "4", "--section", "Nope", "--file", f])
        self.assertEqual((code, out["verification_state"]), (1, "NOT_RUN"))

    def test_budget_argument_validation(self):
        f = self.write("t.md", "one two")
        self.assertEqual(run_cli(["budget", "--type", "range", "--min", "1", "--max", "3", "--target", "2",
                                  "--file", f])[0], 2)
        self.assertEqual(run_cli(["budget", "--type", "max", "--target", "3", "--min", "1", "--file", f])[0], 2)
        self.assertEqual(run_cli(["budget", "--type", "range", "--min", "1", "--max", "3", "--file", f])[0], 0)

    def test_path_guard(self):
        refused = [self.write("doc.docx", "x"), self.write(".env", "SECRET=1"), self.write(".env.local.txt", "x"),
                   self.write("repo/.git/notes.md", "x"), self.write(".gnupg/x.txt", "x"),
                   self.write(".netrc.txt", "x"),
                   self.write(".ssh/notes.txt", "x"), self.write("credentials.txt", "x"),
                   self.write(".aws/config.md", "x"), self.write("id_rsa.txt", "x"), self.write("noext", "x")]
        for p in refused:
            code, out = run_cli(["count", "--file", p])
            self.assertEqual(code, 3, p)
            self.assertIn("refused path", out["error"]["message"])
        ok = self.write("notes/draft.markdown", "fine words")
        self.assertEqual(run_cli(["count", "--file", ok])[0], 0)

    def test_path_guard_applies_to_compare_and_originality(self):
        good = self.write("o.md", "text here")
        bad = self.write("secrets/.env", "x")
        self.assertEqual(run_cli(["compare", "--original", good, "--revised", bad])[0], 3)
        self.assertEqual(run_cli(["originality", "--source", bad, "--text", good])[0], 3)
        self.assertEqual(run_cli(["inventory", "--file", bad])[0], 3)

    def test_directory_message(self):
        d = os.path.join(self.dir, "folder.md")
        os.makedirs(d)
        code, out = run_cli(["count", "--file", d])
        self.assertEqual(code, 3)
        self.assertIn("directory", out["error"]["message"])

    def test_encodings(self):
        u16 = self.write("u16.txt", "﻿hello there world".encode("utf-16-le"), binary=True)
        u16 = self.write("u16.txt", b"\xff\xfe" + "hello there world".encode("utf-16-le"), binary=True)
        self.assertEqual(run_cli(["count", "--file", u16])[1]["count"], 3)
        cp = self.write("cp.txt", "caf\xe9 cr\xe8me br\xfbl\xe9e".encode("cp1252"), binary=True)
        code, out = run_cli(["count", "--file", cp])
        self.assertEqual((code, out["count"]), (0, 3))
        self.assertTrue(any("Windows-1252" in w for w in out["warnings"]))
        bom = self.write("bom.txt", b"\xef\xbb\xbfone two", binary=True)
        self.assertEqual(run_cli(["count", "--file", bom])[1]["count"], 2)

    def test_crlf(self):
        f = self.write("c.md", "Title\r\n\r\nBody text here.\r\n")
        self.assertEqual(run_cli(["count", "--file", f, "--exclude", "title"])[1]["count"], 3)

    def test_compare_exit_codes(self):
        a, b = self.write("a.md", "Costs increased."), self.write("b.md", "Costs decreased.")
        self.assertEqual(run_cli(["compare", "--original", a, "--revised", a])[0], 0)
        code, out = run_cli(["compare", "--original", a, "--revised", b])
        self.assertEqual((code, out["status"]), (1, "SEMANTIC_RISK_FLAG"))
        self.assertEqual(run_cli(["compare", "--original", "-", "--revised", "-"])[0], 2)


# --------------------------------------------------------------------------- originality

class Originality(TempDirCase):
    SOURCE = ("Urban heat islands form because dark impervious surfaces absorb solar radiation during the day "
              "and release it slowly at night, while the lack of vegetation reduces evaporative cooling.")

    def test_close_copy_flagged(self):
        text = ("In cities, dark impervious surfaces absorb solar radiation during the day and release it slowly "
                "at night, which warms neighbourhoods.")
        res = m.originality(self.SOURCE, text)
        self.assertEqual(res["status"], "CLOSE_PARAPHRASE_FLAG")
        self.assertGreaterEqual(res["longest_span_words"], 12)

    def test_real_paraphrase_passes(self):
        text = ("Paved, dark materials soak up sunlight and give the heat back after sunset; with few plants, "
                "there is little cooling from evaporation.")
        self.assertEqual(m.originality(self.SOURCE, text)["status"], "NO_CLOSE_COPY_DETECTED")

    def test_quoted_copy_reported_separately(self):
        text = ("As the source puts it, \"dark impervious surfaces absorb solar radiation during the day and "
                "release it slowly at night\" (Lee, 2020), which matters for planners deciding on materials.")
        res = m.originality(self.SOURCE, text)
        self.assertEqual(res["status"], "NO_CLOSE_COPY_DETECTED")
        self.assertTrue(res["quoted_spans"])

    def test_cli_and_n_validation(self):
        s, t = self.write("s.md", self.SOURCE), self.write("t.md", self.SOURCE)
        code, out = run_cli(["originality", "--source", s, "--text", t])
        self.assertEqual((code, out["command"], out["status"]), (1, "originality", "CLOSE_PARAPHRASE_FLAG"))
        self.assertEqual(run_cli(["originality", "--source", s, "--text", t, "--n", "2"])[0], 2)


class ProtectedTerms(TempDirCase):
    ORIG = "We used the CRISPR-Cas9 system and the LAMP assay. CRISPR-Cas9 edits DNA. Ask the Board."

    def test_removed_or_changed_term_is_literal_and_unauthorizable(self):
        rev = "We used a gene-editing system and the LAMP assay. It edits DNA. Ask the board."
        res = m.compare_texts(self.ORIG, rev, [("CRISPR-Cas9", "gene-editing")], ["CRISPR-Cas9", "LAMP", "Board"])
        found = {f["values"]["term"]: f for f in res["findings"] if f["code"] == "PROTECTED_TERM_CHANGED"}
        self.assertEqual(set(found), {"CRISPR-Cas9", "Board"})  # case-sensitive: "board" is a change
        self.assertTrue(all(f["literal"] and not f["authorized"] for f in found.values()))
        self.assertEqual(res["status"], "DETERMINISTIC_LITERAL_FAILURE")
        self.assertEqual(res["protected_terms_checked"], 3)

    def test_kept_terms_do_not_flag_and_whole_word(self):
        rev = "The LAMP assay and the CRISPR-Cas9 system were used. CRISPR-Cas9 edits DNA. Ask the Board."
        res = m.compare_texts(self.ORIG, rev, (), ["CRISPR-Cas9", "LAMP", "Board"])
        self.assertNotIn("PROTECTED_TERM_CHANGED", codes(res))
        self.assertEqual(m._term_count("LAMPS and LAMP", "LAMP"), 1)

    def test_added_occurrence_counts_as_change(self):
        res = m.compare_texts("Use LAMP.", "Use LAMP. LAMP again.", (), ["LAMP"])
        self.assertIn("PROTECTED_TERM_CHANGED", codes(res))

    def test_cli_protect_file(self):
        o = self.write("o.md", self.ORIG)
        r = self.write("r.md", self.ORIG.replace("LAMP", "lamp"))
        p = self.write("terms.txt", "LAMP\n\n  CRISPR-Cas9  \nLAMP\n")
        code, out = run_cli(["compare", "--original", o, "--revised", r, "--protect", p])
        self.assertEqual((code, out["status"], out["protected_terms_checked"]), (1, "DETERMINISTIC_LITERAL_FAILURE", 2))
        code, out = run_cli(["compare", "--original", o, "--revised", o, "--protect", p])
        self.assertEqual((code, out["status"]), (0, "NO_FLAG_DETECTED"))
        bad = self.write("terms.docx", "LAMP")
        self.assertEqual(run_cli(["compare", "--original", o, "--revised", r, "--protect", bad])[0], 3)


class OriginalityReordered(unittest.TestCase):
    SOURCE = ("Coastal wetlands store large amounts of carbon in waterlogged soils, protect shorelines from storm "
              "surges, and provide nursery habitat for commercially important fish species. Other text follows.")

    def test_reordered_copy_flags(self):
        text = ("Commercially important fish species find nursery habitat in coastal wetlands, which protect "
                "shorelines from storm surges and store large amounts of carbon in waterlogged soils.")
        res = m.originality(self.SOURCE, text)
        self.assertEqual(res["status"], "CLOSE_PARAPHRASE_FLAG")
        self.assertTrue(res["reordered_close_sentences"])
        self.assertGreaterEqual(res["reordered_close_sentences"][0]["dice"], 0.8)
        self.assertGreater(res["lcs_words"], 0)

    def test_genuine_paraphrase_not_reordered(self):
        text = ("Marshes along the coast lock away a lot of carbon, buffer the land against storms and shelter "
                "young fish that fisheries later depend on.")
        res = m.originality(self.SOURCE, text)
        self.assertEqual(res["reordered_close_sentences"], [])
        self.assertEqual(res["status"], "NO_CLOSE_COPY_DETECTED")

    def test_short_sentences_ignored(self):
        res = m.originality("Wetlands store carbon well.", "Carbon is stored well by wetlands.")
        self.assertEqual(res["reordered_close_sentences"], [])

    def test_quoted_sentence_not_counted(self):
        text = ("\"Commercially important fish species find nursery habitat in coastal wetlands, which protect "
                "shorelines from storm surges and store large amounts of carbon in waterlogged soils.\"")
        self.assertEqual(m.originality(self.SOURCE, text)["reordered_close_sentences"], [])

    def test_lcs(self):
        self.assertEqual(m._lcs_len(list("abcde"), list("aebdc")), 3)


class RepeatedOpeners(TempDirCase):
    def test_runs_detected(self):
        text = ("The study used surveys. The study also used interviews. Study results were mixed. "
                "However, costs rose. However, staff stayed. However, sales fell. Finally, it ended.")
        runs = m.repeated_openers(m.split_sentences(text))
        self.assertEqual(runs, [{"word": "study", "sentence_indexes": [0, 1, 2]},
                                {"word": "however", "sentence_indexes": [3, 4, 5]}])

    def test_no_run_for_two(self):
        self.assertEqual(m.repeated_openers(m.split_sentences("It rained. It snowed. Then sun.")), [])

    def test_inventory_reports_it(self):
        f = self.write("t.md", "This works. This helps. This ends.")
        code, out = run_cli(["inventory", "--file", f])
        self.assertEqual((code, out["repeated_openers"][0]["sentence_indexes"]), (0, [0, 1, 2]))


class UserTestingFixes(TempDirCase):
    """Regressions found in user testing (0.4.1)."""

    def test_spelling_fix_is_not_a_new_cue(self):
        for o, r in [("Grid storage remains a bottleneck becuase batteries are expensive.",
                      "Grid storage remains a bottleneck because batteries are expensive."),
                     ("The results were possibley biased.", "The results were possibly biased."),
                     ("Outcomes were asociated with income.", "Outcomes were associated with income."),
                     ("The trial demonstated the effect.", "The trial demonstrated the effect."),
                     ("It does not work unles the key is set.", "It does not work unless the key is set.")]:
            self.assertEqual(status(o, r)["status"], "NO_FLAG_DETECTED", r)

    def test_spelling_tolerance_does_not_hide_real_additions(self):
        self.assertIn("CAUSAL_ADDED", codes(status("Batteries are expensive.", "Batteries are expensive because of lithium.")))
        self.assertIn("HEDGE_ADDED", codes(status("The results were biased.", "The results were possibly biased.")))
        # short cue words (< 5 letters) are never absorbed
        self.assertNotEqual(status("The drug is safe.", "The drug is not safe.")["status"], "NO_FLAG_DETECTED")

    def test_when_compared_is_not_a_condition(self):
        for phrase in ("when compared with", "when compared to", "when compared against"):
            res = status("Scores were higher relative to controls.", "Scores were higher %s controls." % phrase)
            self.assertNotIn("CONDITION_CHANGED", codes(res), phrase)
            self.assertNotIn("CONDITION_REMOVED", codes(res), phrase)
        self.assertIn("CONDITION_CHANGED", codes(status("It fails if the cache is full.", "It fails when the cache is full.")))

    def test_role_word_skips_function_words(self):
        res = status("Group A scored 40 relative to controls.", "Group A scored 40 versus controls.")
        self.assertNotIn("NUMBER_ROLE_CHANGED", codes(res))
        res = status("Mean scores were 40 compared with 35 in controls.", "Mean scores were 40 against 35 in controls.")
        self.assertNotIn("NUMBER_ROLE_CHANGED", codes(res))
        items = m.find_items("We saw 40 relative to the baseline group.", m.split_sentences("x"))
        self.assertEqual([it["role_word"] for it in items if it["category"] == "number"], ["baseline"])
        self.assertIn("NUMBER_ROLE_CHANGED", codes(status("We recruited 40 women.", "We recruited 40 men.")))

    def test_cjk_character_counts(self):
        text = "我们研究了气候变化的影响。结果显示，“城市”更热……"
        r = m.measure(text, "word2019_approx")
        han = len(m._CJK.findall(text))
        self.assertEqual(r["cjk_characters"], han)
        self.assertEqual(r["cjk_characters_with_punctuation"], han + 6)  # 。，“”……
        self.assertIn("punctuation", r["cjk_note"])
        self.assertNotIn("cjk_characters", m.measure("Plain English only.", "word2019_approx"))

    def test_budget_count_mode(self):
        f = self.write("zh.md", "我们研究了影响。" * 30)  # 7 Han + 1 punctuation per repeat = 240
        code, out = run_cli(["budget", "--type", "max", "--target", "230", "--count-mode", "cjk_chars_with_punct",
                             "--file", f])
        self.assertEqual((code, out["count"], out["status"], out["count_mode"]), (1, 240, "FAIL", "cjk_chars_with_punct"))
        code, out = run_cli(["budget", "--type", "max", "--target", "240", "--count-mode", "cjk_chars_with_punct",
                             "--file", f])
        self.assertEqual((code, out["verification_state"]), (0, "VERIFIED"))
        code, out = run_cli(["budget", "--type", "max", "--target", "240", "--file", f])
        self.assertEqual((out["count_mode"], out["count"]), ("words", 210))
        e = self.write("en.md", "English text only.")
        code, out = run_cli(["budget", "--type", "max", "--target", "10", "--count-mode", "cjk_chars_with_punct",
                             "--file", e])
        self.assertEqual((code, out["verification_state"]), (1, "NOT_RUN"))


# --------------------------------------------------------------------- alignment & speed

def _cpu(fn):
    a = time.process_time()
    out = fn()
    return time.process_time() - a, out


class Scale(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        random.seed(7)
        words = "the study found that patients may not improve when dose increased by 5 mg in group A".split()
        cls.sents = [" ".join(random.choice(words) for _ in range(12)).capitalize() + "." for _ in range(2000)]

    def test_insertion_at_top_does_not_flood(self):
        o = " ".join(self.sents)
        r = " ".join(["Inserted sentence number %d here." % i for i in range(20)] + self.sents)
        res = m.compare_texts(o, r)
        self.assertLessEqual(len(res["findings"]), 45)

    def test_inventory_adversarial_speed(self):
        for pat in ("1 ", "all ", "**a ", "![", "[", "`a ", "\"x ", "a=b+c ", "(Smith 2020 "):
            s = (pat * (1_000_000 // len(pat)))[:1_000_000]
            secs, _ = _cpu(lambda: m.build_inventory(s))
            self.assertLess(secs, PERF_LIMIT, pat)

    def test_strip_markdown_speed(self):
        for pat in ("[", "![", "**a ", "<!-- ", "| --- "):
            s = (pat * (1_000_000 // len(pat)))[:1_000_000]
            secs, _ = _cpu(lambda: m.strip_markdown(s))
            self.assertLess(secs, 2.0, pat)

    def test_compare_speed(self):
        o = " ".join(self.sents) * 7
        r = " ".join(["Inserted sentence number %d here." % i for i in range(20)] + self.sents) * 7
        secs, _ = _cpu(lambda: m.compare_texts(o, r))
        self.assertLess(secs, PERF_LIMIT)

    def test_number_cap_warns(self):
        res = m.compare_texts("1 " * 60000, "1 " * 60000 + "2")
        self.assertTrue(any("not analysed" in w for w in res["warnings"]))


if __name__ == "__main__":
    unittest.main()
