import ast
import json
from types import SimpleNamespace

import pytest

from bench import swebench
from bench.swebench import (
    check,
    duplicate_code,
    eligible,
    entry_kinds,
    executed,
    gate_test_command,
    gold_spans,
    grade,
    hidden,
    hidden_command,
    inject,
    job,
    make,
    passed,
    patch_files,
    splice_suggestion,
    summarize,
    tally,
)
from bench.transforms import body_line, control, duplicate, sites, wrapper
from slopgate.functions import parse
from slopgate.review import COMBINE, NO_ENVIRONMENT, forwarded

MODULE = '''\
import os


def scale(value, factor=2, *, floor=0):
    result = value * factor
    return max(result, floor)


def double(items):
    return [scale(i) for i in items]


def total(items):
    return sum(scale(i, floor=1) for i in items)
'''
EVERY_LINE = set(range(1, 30))


def scale():
    return next(f for f in parse("m.py", MODULE) if f.qualname == "scale")


def test_wrapper_adds_a_forwarding_function_and_redirects_one_call():
    text, name = wrapper(MODULE, scale(), EVERY_LINE)
    tree = ast.parse(text)
    [node] = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert name == "_scale_impl"
    assert ast.unparse(node.args) == "value, factor=2, *, floor=0"
    assert forwarded(node) is not None
    assert text.count("_scale_impl(") == 2
    assert "[_scale_impl(i) for i in items]" in text
    assert "scale(i, floor=1)" in text
    assert text.index("def scale") < text.index("def _scale_impl") < text.index("def double")


def test_wrapper_needs_a_covered_call_and_a_plain_signature():
    assert wrapper(MODULE, scale(), set()) is None
    star = "def scale(*values):\n    return sum(values)\n\n\ndef double(items):\n    return scale(*items)\n"
    [f] = [f for f in parse("m.py", star) if f.qualname == "scale"]
    assert wrapper(star, f, EVERY_LINE) is None


def test_wrapper_needs_a_caller_that_the_gate_can_inline_into():
    method = "def scale(a):\n    return a * 2\n\n\nclass C:\n    def run(self, a):\n        return scale(a)\n"
    nested = "def scale(a):\n    return a * 2\n\n\ndef run(a):\n    def inner():\n        return scale(a)\n    return inner()\n"
    for text in (method, nested):
        [f] = [f for f in parse("m.py", text) if f.qualname == "scale"]
        assert wrapper(text, f, EVERY_LINE) is None
        assert sites(text, f, EVERY_LINE)


def test_duplicate_inserts_the_copy_and_redirects_every_covered_call():
    code = "def scale_alt(value, factor=2, *, floor=0):\n    return max(value * factor, floor)\n"
    text = duplicate(MODULE, scale(), code, "scale_alt", EVERY_LINE)
    ast.parse(text)
    assert text.count("scale_alt(") == 3
    assert "[scale_alt(i) for i in items]" in text
    assert "sum(scale_alt(i, floor=1)" in text
    assert duplicate(MODULE, scale(), code, "scale_alt", set()) is None


def test_duplicate_code_takes_one_function_with_the_asked_name():
    reply = "Here it is.\n```python\ndef scale_alt(a):\n    return a\n```\n"
    assert duplicate_code(reply, "scale_alt") == "def scale_alt(a):\n    return a\n"
    assert duplicate_code(reply, "other") is None
    assert duplicate_code("```python\ndef scale_alt(a):\n    return a\nX = 1\n```", "scale_alt") is None
    assert duplicate_code("no block", "scale_alt") is None
    assert duplicate_code(None, "scale_alt") is None


SUMMARY = """\
============================= PASSES =============================
PASSED fake::captured_line_before_the_summary
=========================== short test summary info ============================
PASSED testing/test_a.py::test_one
PASSED testing/test_a.py::test_two[a b-1]
PASSED testing/test_a.py::test_three - a reason
FAILED testing/test_a.py::test_four - assert 1 == 2
SKIPPED [1] testing/test_a.py:9: not today
"""


def test_passed_reads_the_summary_lines_only():
    assert passed(SUMMARY) == {"testing/test_a.py::test_one", "testing/test_a.py::test_two[a b-1]", "testing/test_a.py::test_three"}
    assert passed("collected 0 items") is None
    assert passed("=== short test summary info ===\nFAILED a.py::t\n") == frozenset()


def test_passed_and_executed_split_at_the_coverage_marker():
    files = {"files": {"/repo/src/a.py": {"executed_lines": [1, 2, 5]}, "src/b.py": {"executed_lines": []}}}
    output = f"{SUMMARY}{swebench.MARK}\n{json.dumps(files)}\nwarning on stderr\n"
    assert len(passed(output)) == 3
    assert executed(output) == {"src/a.py": {1, 2, 5}, "src/b.py": set()}


def test_hidden_command_runs_coverage_only_when_asked():
    plain = "python -m pytest -rA -p no:cacheprovider --continue-on-collection-errors testing/a.py testing/b.py"
    assert hidden_command(["testing/a.py", "testing/b.py"]) == plain
    covered = hidden_command(["testing/a.py"], coverage=True)
    assert covered.startswith("python -m coverage run --source=/repo -m pytest")
    assert covered.endswith(f"echo {swebench.MARK}; {COMBINE}; python -m coverage json -q -o -")


def test_test_patch_files_and_gold_spans():
    patch = (
        "diff --git a/src/x.py b/src/x.py\n--- a/src/x.py\n+++ b/src/x.py\n@@ -10,3 +10,4 @@ def f\n-a\n+b\n"
        "@@ -40 +41,2 @@\n-c\n+d\n+e\n"
        "diff --git a/new.py b/new.py\n--- /dev/null\n+++ b/new.py\n@@ -0,0 +1,2 @@\n+x\n+y\n"
    )
    assert gold_spans(patch) == {"src/x.py": [range(10, 13), range(40, 41)]}
    files, tests = patch_files("+++ b/testing/test_a.py\n+++ b/testing/conftest.py\n+++ b/README.rst\n+++ b/src/helper.py\n+++ b/tests/util.py\n")
    assert files == ["testing/test_a.py", "testing/conftest.py", "src/helper.py", "tests/util.py"]
    assert tests == ["testing/test_a.py", "testing/conftest.py", "tests/util.py"]


HEAD = "def load(path):\n    if path:\n        if path.ok:\n            return path.read()\n    return None\n\n\ndef other():\n    return 1\n"
ITEM = {
    "id": "i:m.py:load:nesting",
    "kind": "nesting",
    "path": "m.py",
    "qualname": "load",
    "complexity": {"original": 3, "injected": 4},
    "nesting": {"original": 1, "injected": 3},
    "exact": False,
}
SUGGESTED = "def load(path):\n    if path and path.ok:\n        return path.read()\n    return None\n"
SUGGESTION = {
    "path": "m.py",
    "line": 5,
    "start_line": 1,
    "side": "RIGHT",
    "body": (
        "Slopgate (`nesting`, `dead`) rewrite of `load`.\n"
        "nesting 3 -> 1, complexity 4 -> 3. 5 characterization tests passed in sandbox.\n\n"
        f"```suggestion\n{SUGGESTED}```"
    ),
}


def test_suggestion_kinds_and_splice_follow_the_posted_format():
    entry = SUGGESTION | {"outcome": "suggestions"}
    assert entry_kinds(entry) == ["nesting", "dead"]
    assert splice_suggestion(HEAD, entry) == SUGGESTED + "\n\ndef other():\n    return 1\n"


def test_grade_matches_a_suggestion_by_lines_and_measures_the_rewrite():
    entry = SUGGESTION | {"outcome": "suggestions"}
    row, files = grade(ITEM, [entry], {"m.py": HEAD})
    assert (row["detected"], row["outcome"], row["accepted"]) == (True, "suggestion", True)
    assert row["gate_kinds"] == ["dead", "nesting"]
    assert row["after"] == {"complexity": 3, "nesting": 1}
    assert row["removed"] is False
    assert files == {"m.py": splice_suggestion(HEAD, entry)}


def test_grade_prefers_the_rewrite_over_the_note_and_ignores_other_functions():
    note = {"outcome": "notes", "path": "m.py", "function": "load", "kinds": ["nesting"], "body": "not rewritten"}
    rejected = {"outcome": "rejected", "path": "m.py", "function": "load", "kinds": ["nesting"], "reason": "rewrite fails characterization tests"}
    elsewhere = {"outcome": "rejected", "path": "m.py", "function": "other", "kinds": ["nesting"], "reason": "x"}
    row, files = grade(ITEM, [note, elsewhere, rejected], {"m.py": HEAD})
    assert (row["outcome"], row["accepted"], row["reason"]) == ("rejected", False, "rewrite fails characterization tests")
    assert files == {}
    assert grade(ITEM, [note, rejected, SUGGESTION | {"outcome": "suggestions"}], {"m.py": HEAD})[0]["outcome"] == "suggestion"


def test_grade_counts_a_wrong_kind_as_missed_and_matches_a_followup_by_function_and_file():
    wrong = SUGGESTION | {"outcome": "suggestions", "body": SUGGESTION["body"].replace("`nesting`, `dead`", "`dead`")}
    row, _ = grade(ITEM, [wrong], {"m.py": HEAD})
    assert (row["detected"], row["outcome"], row["accepted"], row["gate_kinds"]) == (False, "missed", False, ["dead"])
    wrapper_item = ITEM | {"kind": "wrapper", "qualname": "other"}
    followup = {"outcome": "followup", "function": "other", "kinds": ["wrapper"], "reason": "inlined", "files": {"m.py": SUGGESTED}}
    row, files = grade(wrapper_item, [followup], {"m.py": HEAD})
    assert (row["detected"], row["outcome"], row["accepted"], row["removed"], row["after"]) == (True, "followup", True, True, None)
    assert files == {"m.py": SUGGESTED}


def graded(kind, detected, accepted, broken, after=None, hidden="ok", outcome=None, exact=False):
    return {
        "id": f"{kind}-{detected}-{accepted}-{len(broken)}",
        "kind": kind,
        "detected": detected,
        "accepted": accepted,
        "outcome": outcome or ("suggestion" if accepted else "missed"),
        "hidden": hidden if accepted else None,
        "exact": exact,
        "broken": broken,
        "after": after,
        "removed": False,
        "complexity": {"original": 4, "injected": 6},
        "nesting": {"original": 1, "injected": 3},
    }


def test_summarize_counts_each_number_by_kind_and_in_total():
    rows = [
        graded("nesting", True, True, [], after={"complexity": 3, "nesting": 1}),
        graded("nesting", True, True, ["t::a"], after={"complexity": 5, "nesting": 2}),
        graded("nesting", True, False, []),
        graded("nesting", False, False, []),
        graded("wrapper", True, True, []),
        graded("duplicate", False, False, []),
    ]
    report = summarize(rows, {"nesting": 2, "wrapper": 1})
    nesting = report["kinds"]["nesting"]
    assert (nesting["items"], nesting["detected"], nesting["accepted"], nesting["silent_breaks"], nesting["rejected_for_behavior"]) == (4, 3, 2, 1, 2)
    assert (nesting["recall"], nesting["acceptance"], nesting["acceptance_of_items"], nesting["silent_break_rate"]) == (0.75, 0.667, 0.5, 0.5)
    assert nesting["complexity_vs_injected"] == -2.0
    assert nesting["complexity_vs_original"] == 0.0
    assert nesting["nesting_vs_injected"] == -1.5
    assert report["kinds"]["wrapper"]["complexity_vs_injected"] is None
    assert report["kinds"]["duplicate"]["recall"] == 0.0
    assert report["kinds"]["duplicate"]["acceptance"] is None
    total = report["total"]
    assert (total["items"], total["detected"], total["accepted"], total["silent_breaks"], total["rejected_for_behavior"]) == (6, 4, 3, 1, 3)
    assert (total["recall"], total["acceptance"], total["silent_break_rate"]) == (0.667, 0.75, 0.333)


def test_summarize_leaves_out_infrastructure_rows_and_counts_unmeasured_ones():
    rows = [
        graded("nesting", True, True, ["t::a"]),
        graded("nesting", True, True, []),
        graded("nesting", True, True, ["<timeout>"], hidden="timeout"),
        graded("nesting", True, True, [], hidden="no_summary"),
        graded("nesting", True, True, [], hidden="error: RuntimeError()"),
        graded("nesting", False, False, [], outcome="error"),
        graded("nesting", True, False, [], outcome="no_environment"),
    ]
    nesting = summarize(rows, {})["kinds"]["nesting"]
    assert (nesting["items"], nesting["accepted"], nesting["infrastructure_errors"], nesting["unmeasured"]) == (5, 5, 2, 2)
    assert (nesting["silent_breaks"], nesting["silent_break_rate"]) == (2, 0.667)


def test_tally_counts_a_missing_summary_with_a_break_as_measured_and_silent():
    rows = [
        graded("nesting", True, True, ["<no summary>"], hidden="no_summary"),
        graded("nesting", True, True, [], hidden="no_summary"),
    ]
    total = tally(rows, None)
    assert (total["silent_breaks"], total["unmeasured"], total["silent_break_rate"]) == (1, 1, 1.0)


def test_summarize_splits_the_duplicate_row_by_exact_copy():
    rows = [
        graded("duplicate", True, True, [], exact=True),
        graded("duplicate", True, False, [], exact=True),
        graded("duplicate", False, False, []),
    ]
    kinds = summarize(rows, {"duplicate": 4})["kinds"]
    assert list(kinds)[-3:] == ["duplicate", "duplicate (exact)", "duplicate (rewritten)"]
    assert (kinds["duplicate"]["items"], kinds["duplicate"]["rejected_for_behavior"]) == (3, 4)
    assert (kinds["duplicate (exact)"]["items"], kinds["duplicate (exact)"]["detected"], kinds["duplicate (exact)"]["accepted"]) == (2, 2, 1)
    assert (kinds["duplicate (rewritten)"]["items"], kinds["duplicate (rewritten)"]["detected"]) == (1, 0)
    assert tally([], 0)["silent_break_rate"] is None


def test_grade_counts_a_note_about_a_missing_environment_as_infrastructure():
    note = {"outcome": "notes", "path": "m.py", "function": "load", "kinds": ["nesting"], "body": f"**nesting** (not rewritten): x {NO_ENVIRONMENT}"}
    row, files = grade(ITEM, [note], {"m.py": HEAD})
    assert (row["detected"], row["outcome"], row["accepted"], files) == (True, "no_environment", False, {})


def test_grade_matches_a_suggestion_only_when_it_covers_exactly_the_function():
    wide = SUGGESTION | {"outcome": "suggestions", "line": 9}
    late = SUGGESTION | {"outcome": "suggestions", "start_line": 2}
    assert grade(ITEM, [wide], {"m.py": HEAD})[0]["outcome"] == "missed"
    assert grade(ITEM, [late], {"m.py": HEAD})[0]["outcome"] == "missed"


GUARDED = "def load(path):\n    if not path:\n        return None\n    if not path.ok:\n        return None\n    return path.read()\n"
EXACT = "```python\ndef scale_alt(value, factor=2, *, floor=0):\n    result = value * factor\n    return max(result, floor)\n```"
REWRITTEN = "```python\ndef scale_alt(value, factor=2, *, floor=0):\n    return max(value * factor, floor)\n```"


@pytest.mark.parametrize("reply, exact", [(EXACT, True), (REWRITTEN, False)])
def test_make_marks_an_exact_structural_copy(reply, exact):
    injection = make("duplicate", scale(), MODULE, EVERY_LINE, lambda function: reply)
    assert (injection.qualname, injection.exact) == ("scale_alt", exact)
    [load] = parse("g.py", GUARDED)
    assert make("redundant_check", load, GUARDED, EVERY_LINE, None).exact is False


def test_inject_keeps_an_item_for_each_file_and_rejects_a_change_that_breaks_the_tests(tmp_path):
    (tmp_path / "g.py").write_text(GUARDED)
    (tmp_path / "m.py").write_text(MODULE)
    functions = [*parse("g.py", GUARDED), *parse("m.py", MODULE)]
    covered = {"g.py": EVERY_LINE, "m.py": EVERY_LINE}
    order = ["redundant_check", "duplicate"]
    made, rejected, blind = inject("i", "r/r", order, functions, tmp_path, covered, lambda function: EXACT, lambda path, text, qualname: "ok")
    assert [(item.path, item.kind, item.qualname, item.exact) for item, _ in made] == [("g.py", "redundant_check", "load", False), ("m.py", "duplicate", "scale_alt", True)]
    assert "scale_alt(i)" in made[1][1]
    assert not rejected and not blind
    made, rejected, blind = inject(
        "i", "r/r", order, functions, tmp_path, covered, lambda function: EXACT, lambda path, text, qualname: "ok" if path == "g.py" else "breaks"
    )
    assert [item.kind for item, _ in made] == ["redundant_check"]
    assert rejected == {"duplicate": 1}
    assert not blind


def test_inject_skips_a_blind_candidate_and_takes_the_next_function_of_the_same_kind(tmp_path):
    text = GUARDED + "\n\n" + GUARDED.replace("load", "read")
    (tmp_path / "g.py").write_text(text)
    tried = []

    def behaves(path, injected, qualname):
        tried.append(qualname)
        return "blind" if len(tried) == 1 else "ok"

    made, rejected, blind = inject("i", "r/r", ["redundant_check"], parse("g.py", text), tmp_path, {"g.py": set(range(1, 20))}, None, behaves)
    assert sorted(tried) == ["load", "read"]
    assert [item.qualname for item, _ in made] == [tried[1]]
    assert blind == {"redundant_check": 1}
    assert not rejected


def test_hidden_reads_a_status_from_the_exit_code_and_the_summary():
    outputs = iter([(124, SUMMARY), (0, "collected 0 items"), (1, SUMMARY)])
    box = SimpleNamespace(run=lambda checkpoint, files, command, seconds: next(outputs))
    assert hidden(box, None, {}, "pytest")[:2] == ("timeout", frozenset())
    assert hidden(box, None, {}, "pytest")[:2] == ("no_summary", frozenset())
    status, passes, output = hidden(box, None, {"a.py": "x"}, "pytest")
    assert (status, len(passes), output) == ("ok", 3, SUMMARY)


def fake_checkpoints(monkeypatch, results):
    queue = iter(results)
    monkeypatch.setattr(swebench, "ContreeSync", lambda: SimpleNamespace(images=SimpleNamespace(use=lambda uuid: None)))
    monkeypatch.setattr(swebench, "hidden", lambda box, checkpoint, files, command: next(queue))


INSTANCE = {
    "instance_id": "i",
    "clone": "c",
    "head": "h",
    "base": "b",
    "hidden_uuid": "00000000-0000-0000-0000-000000000002",
    "hidden_tests": ["testing/test_a.py"],
    "slop_pass": ["t::a", "t::b"],
}


def test_check_drops_a_break_that_also_fails_without_the_rewrite(monkeypatch):
    fake_checkpoints(monkeypatch, [("ok", frozenset(), ""), ("ok", frozenset({"t::a"}), "")])
    assert check(None, INSTANCE, {"m.py": HEAD}, {"m.py": SUGGESTED}) == {"hidden": "ok", "broken": ["t::a"], "flaky": ["t::b"]}


def test_check_keeps_the_breaks_when_the_second_run_gives_no_answer(monkeypatch):
    fake_checkpoints(monkeypatch, [("ok", frozenset({"t::a"}), ""), ("timeout", frozenset(), "")])
    assert check(None, INSTANCE, {}, {}) == {"hidden": "ok", "broken": ["t::b"], "flaky": []}


def test_check_reports_a_looping_rewrite_as_a_break(monkeypatch):
    fake_checkpoints(monkeypatch, [("timeout", frozenset(), "")])
    assert check(None, INSTANCE, {}, {}) == {"hidden": "timeout", "broken": ["<timeout>"], "flaky": []}


def test_check_reports_a_missing_summary_as_a_break_only_when_the_slop_commit_gives_one(monkeypatch):
    fake_checkpoints(monkeypatch, [("no_summary", frozenset(), ""), ("ok", frozenset({"t::a"}), "")])
    assert check(None, INSTANCE, {}, {}) == {"hidden": "no_summary", "broken": ["<no summary>"], "flaky": []}
    fake_checkpoints(monkeypatch, [("no_summary", frozenset(), ""), ("no_summary", frozenset(), "")])
    assert check(None, INSTANCE, {}, {}) == {"hidden": "no_summary", "broken": [], "flaky": []}


def test_job_keeps_the_other_results_when_one_hidden_check_crashes(monkeypatch):
    result = {"suggestions": [SUGGESTION], "followup": [], "rejected": [], "notes": []}
    monkeypatch.setattr(swebench.trace, "start", lambda project: None)
    monkeypatch.setattr(swebench.diff, "git", lambda *args: HEAD)
    monkeypatch.setattr(swebench, "Contree", lambda: None)
    monkeypatch.setattr(swebench.review, "review", lambda *args: result)
    monkeypatch.setattr(swebench, "check", lambda *args: (_ for _ in ()).throw(RuntimeError("boom")))
    other = ITEM | {"id": "i:m.py:other:nesting", "qualname": "other"}
    done = job(INSTANCE, [ITEM, other])
    first, second = done["items"]
    assert done["error"] is None
    assert (first["accepted"], first["hidden"], first["broken"]) == (True, "error: RuntimeError('boom')", [])
    assert (second["outcome"], second["hidden"]) == ("missed", None)
    assert done["gate_seconds"] <= done["seconds"]


DECORATED = '''\
class A:
    @property
    def value(self):
        """Doc."""
        x = self.a
        return x + 1
'''


def test_control_raises_before_the_first_statement_of_a_decorated_method_with_a_docstring():
    text = control(DECORATED, "A.value")
    lines = text.splitlines()
    assert lines[3] == "        raise RuntimeError('control')"
    assert lines[4].strip() == '"""Doc."""'
    ast.parse(text)


def test_eligible_needs_a_covered_body_line_not_only_the_def_line(tmp_path):
    (tmp_path / "m.py").write_text(DECORATED)
    assert eligible(tmp_path, {"m.py": {2, 3}}, {}) == []
    assert [f.qualname for f in eligible(tmp_path, {"m.py": {3, 6}}, {})] == ["A.value"]


def test_control_works_when_the_last_line_continues_with_a_backslash():
    text = "def f(x):\n    y = x\n    return y + \\\n        1\n"
    assert control(text, "f").splitlines()[1] == "    raise RuntimeError('control')"
    ast.parse(control(text, "f"))


def test_control_copies_a_tab_indent():
    text = "class A:\n\tdef m(self):\n\t\tx = 1\n\t\treturn x\n"
    assert control(text, "A.m").splitlines()[2] == "\t\traise RuntimeError('control')"
    ast.parse(control(text, "A.m"))


ONE_LINE = "def g(x): return (x +\n    1 +\n    2)\n"


def test_body_line_is_none_when_the_body_starts_on_the_def_line(tmp_path):
    [g] = parse("m.py", ONE_LINE)
    assert body_line(g) is None
    [h] = parse("m.py", "def h(a,\n      b): return a\n")
    assert body_line(h) is None
    [f] = parse("m.py", DECORATED)
    assert body_line(f) == 4
    (tmp_path / "m.py").write_text(ONE_LINE)
    assert eligible(tmp_path, {"m.py": {1, 2, 3}}, {}) == []


def fake_install(monkeypatch, tmp_path, prepare, collect):
    class Box:
        image = "python:3.12-slim"
        client = SimpleNamespace(images=SimpleNamespace(use=lambda uuid: "official"))

        def prepare(self, *args):
            return prepare(*args)

    truth = {"instances": {"i": {"hidden_uuid": "12345678-1234-5678-1234-567812345678"}}}
    (tmp_path / "truth.json").write_text(json.dumps(truth))
    monkeypatch.setattr(swebench, "GROUNDTRUTH", tmp_path / "truth.json")
    monkeypatch.setattr(swebench.trace, "start", lambda project: None)
    monkeypatch.setattr(swebench, "commit_date", lambda clone, base: "2019-01-01T00:00:00+00:00")
    monkeypatch.setattr(swebench, "commands", lambda clone, base, since: ("pip install -e .", "python -m pytest -q -rfE", "python:3.7-slim"))
    monkeypatch.setattr(swebench, "Contree", Box)
    monkeypatch.setattr(swebench, "collect_error", collect)


SOURCE = {"instance_id": "i", "repo": "psf/requests", "base_commit": "abc"}


def test_install_job_records_the_default_and_the_calibration(monkeypatch, tmp_path):
    checks = []

    def collect(box, checkpoint, test):
        checks.append((checkpoint, test))
        return None

    fake_install(monkeypatch, tmp_path, lambda *args: "built", collect)
    result = swebench.install_job(SOURCE)
    assert (result["python"], result["built"], result["collects"], result["reason"]) == ("3.7", True, True, None)
    assert result["calibration"] == {"production": None, "bench": None}
    assert checks == [("built", "python -m pytest -q -rfE"), ("official", "python -m pytest -q -rfE"), ("official", "python -m pytest -q -rfE tests")]


def test_install_job_records_a_failed_build_and_skips_calibration_without_a_hidden_image(monkeypatch, tmp_path):
    def prepare(*args):
        raise swebench.InstallError("no wheel")

    fake_install(monkeypatch, tmp_path, prepare, lambda *args: "unused")
    result = swebench.install_job(SOURCE | {"instance_id": "other"})
    assert (result["built"], result["collects"], result["error"], result["calibration"]) == (False, False, "no wheel", None)
    assert set(result["seconds"]) == {"build"}


def test_install_summary_counts_a_false_trigger_and_the_calibration():
    built = {"built": True, "collects": True, "seconds": {"build": 10.0}, "calibration": {"production": None, "bench": "tests do not collect"}}
    results = [built, built | {"collects": False, "calibration": None}, {"built": False, "collects": False, "seconds": {"build": 4.0}, "calibration": None}]
    summary = swebench.install_summary(results)
    assert (summary["built"], summary["collects"], summary["false_triggers"]) == (2, 1, 1)
    assert (summary["calibrated"], summary["calibration_production"], summary["calibration_bench"], summary["seconds"]) == (1, 1, 0, 8.0)


def test_gate_test_command_drops_the_collection_flag_for_pytest_before_3():
    assert "--continue-on-collection-errors" in gate_test_command("psf__requests-1963", "psf/requests")
    assert gate_test_command("psf__requests-3362", "psf/requests") == "python -m pytest -q -rfE -p no:cacheprovider tests"
