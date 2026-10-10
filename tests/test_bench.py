import ast
from collections import Counter

import pytest

from bench.detect import Item, accept, from_reply, function, measured, splice
from bench.score import compare, outcomes, score, split
from bench.transforms import after_return, negate, transform, unused_local
from slopgate import kinds
from slopgate.functions import parse

NESTED = '''\
def load(path, strict):
    if not path:
        return None
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text()
    if strict and not text:
        raise ValueError(path)
    return text
'''

REDUNDANT = '''\
def total(prices):
    if prices is None:
        return 0
    result = sum(prices)
    return result
'''

SWALLOWED = '''\
class Store:
    def get(self, key):
        """Return the value."""
        value = self.data[key]
        return value.strip()
'''

LOOKUP = '''\
COLORS = {"red": 1, "green": 2, "blue": 3}


def color(name):
    name = name.lower()
    return COLORS[name]
'''

LOOKUP_GET = '''\
SIZES = {"s": 1, "m": 2, "l": 3, "xl": 4}


class Shirt:
    def size(self):
        self.check()
        return SIZES.get(self.label, 0)
'''

SCALE = '''\
def scale(value, factor):
    result = value * factor
    return result
'''


def source_item(text: str, qualname: str) -> Item:
    f = next(f for f in parse("m.py", text) if f.qualname == qualname)
    return Item(f"r:m.py:{qualname}", "r", "c", f.path, qualname, f.start, f.end, f.source, "source")


def injected(kind: str, text: str, qualname: str, new: str | None = None) -> Item:
    source = source_item(text, qualname)
    new = new or transform(kind, source.source, text)
    item = accept(source, text, new, [kind], "transform")
    assert item is not None
    assert item.changed_lines
    before = measured(source.path, source.start, source.source, text)
    after = kinds.measured(function(source, item.source), splice(source, item.source, text))
    assert after.keys() - before == {kind}
    return item


@pytest.mark.parametrize(
    ("kind", "text", "qualname"),
    [
        ("nesting", NESTED, "load"),
        ("swallowed_error", SWALLOWED, "Store.get"),
        ("lookup_table", LOOKUP, "color"),
        ("lookup_table", LOOKUP_GET, "Shirt.size"),
        ("dead", SCALE, "scale"),
    ],
)
def test_measured_transforms_add_only_their_kind(kind, text, qualname):
    injected(kind, text, qualname)


@pytest.mark.parametrize("variant", [unused_local, after_return])
def test_both_dead_forms_are_measured(variant):
    injected("dead", SCALE, "scale", variant(SCALE, SCALE))


def test_indenting_keeps_multiline_strings():
    text = 'def query(db):\n    sql = """\nSELECT 1\n"""\n    rows = db.run(sql)\n    return rows\n'
    item = injected("swallowed_error", text, "query")
    assert '    try:\n        sql = """\nSELECT 1\n"""\n' in item.source


def test_redundant_check_inserts_a_check_that_repeats_the_guard():
    item = injected("redundant_check", REDUNDANT, "total")
    assert item.changed_lines == ["if prices is not None:"]
    assert kinds.repeated_checks(item.source) == ["if prices is not None:"]


NOT_GUARD = '''\
def first(items, strict):
    if not items:
        return None
    if not isinstance(items[0], str):
        raise TypeError(items[0])
    if strict not in (True, False):
        raise ValueError(strict)
    return items[0].upper()
'''


def call(text: str, name: str, *args):
    namespace = {}
    exec(text, namespace)
    try:
        return namespace[name](*args)
    except Exception as error:
        return type(error)


def same_behavior(kind: str, text: str, name: str, inputs) -> str:
    item = injected(kind, text, name)
    new = splice(source_item(text, name), item.source, text)
    for args in inputs:
        assert call(new, name, *args) == call(text, name, *args), args
    return item.source


def test_transforms_keep_behavior(tmp_path):
    empty, full = tmp_path / "empty", tmp_path / "full"
    empty.write_text("")
    full.write_text("data")
    same_behavior("nesting", NESTED, "load", [(None, True), (tmp_path / "missing", False), (empty, True), (empty, False), (full, True)])
    same_behavior("redundant_check", REDUNDANT, "total", [(None,), ([],), ([1, 2],)])
    same_behavior("lookup_table", LOOKUP, "color", [("Red",), ("blue",), ("pink",)])


@pytest.mark.parametrize("kind", ["nesting", "redundant_check"])
def test_not_guards_lose_the_not(kind):
    new = same_behavior(kind, NOT_GUARD, "first", [([], True), ([1], True), (["a"], None), (["a"], False)])
    assert "if items:" in new
    assert "not (not" not in new


@pytest.mark.parametrize(
    ("test", "expected"),
    [
        ("not x", "x"),
        ("x is None", "x is not None"),
        ("a == b", "a != b"),
        ("k in d", "k not in d"),
        ("a < b", "not (a < b)"),
        ("(x := f()) is None", "(x := f()) is not None"),
    ],
)
def test_negate(test, expected):
    assert negate(ast.parse(test, mode="eval").body, test) == expected


def make(item_id: str, origin: str, injected_kinds=(), source_id=None) -> Item:
    return Item(item_id, "r", "c", "m.py", item_id, 1, 2, "", origin, source_id, list(injected_kinds))


MEASURE = {"seconds": 1.0}


def test_score_counts_tp_fp_fn_and_unlabelled():
    items = [make("c1", "clean"), make("c2", "clean"), make("s1", "source"), make("t1", "transform", ["dead"], "s1")]
    labels = {"c1": {"swallowed_error": {"decision": "slop"}, "nesting": {"decision": "false_positive"}}}
    runs = {
        "c1": [{"kinds": {"swallowed_error": [], "nesting": []}} | MEASURE],
        "c2": [{"kinds": {"dead": []}} | MEASURE, {"error": "boom"} | MEASURE],
        "s1": [{"kinds": {}} | MEASURE],
        "t1": [{"kinds": {"redundant_check": ["if x:"]}} | MEASURE],
    }

    report = score(items, runs, {"labels": labels, "injections": {}})

    assert report["groups"]["all"]["total"] == {"items": 2, "tp": 1, "fp": 2, "fn": 1, "precision": 0.333, "recall": 0.5}
    assert report["groups"]["transform"]["dead"] == {"items": 1, "tp": 0, "fp": 0, "fn": 1, "precision": None, "recall": 0.0}
    assert report["unlabelled"] == [{"id": "c2", "kind": "dead", "runs": 1}]
    assert report["clean"]["fp_rate"]["total"] == 0.5
    assert report["clean"]["any_kind_rate"] == 1.0
    assert report["errors"] == [{"id": "c2", "error": "boom"}]
    assert report["stability"]["clean"] == 0.5


def test_injected_item_scores_only_what_its_source_does_not():
    item = make("t1", "transform", ["swallowed_error"], "s1")
    labels = {"s1": {"redundant_check": {"decision": "false_positive"}, "nesting": {"decision": "slop"}}}
    run = {"kinds": {"swallowed_error": [], "redundant_check": ["if x:"], "nesting": [], "dead": []}}

    assert sorted(outcomes(item, run, labels, {})) == [("dead", "fp"), ("swallowed_error", "tp")]
    assert outcomes(item, {"kinds": {}}, labels, {}) == [("swallowed_error", "fn")]


def test_new_kind_on_an_injected_item_is_a_false_positive():
    item = make("t2", "transform", ["dead"], "s2")

    assert sorted(outcomes(item, {"kinds": {"redundant_check": ["if y:"], "dead": []}}, {}, {})) == [("dead", "tp"), ("redundant_check", "fp")]


def test_kind_found_on_the_source_is_scored_on_the_source_only():
    item = make("t3", "transform", ["dead"], "s3")
    run = {"kinds": {"redundant_check": ["if y:"], "nesting": [], "dead": []}}
    runs = {"s3": [{"kinds": {}}, {"kinds": {"redundant_check": ["if y:"]}}], "s4": [{"kinds": {"nesting": []}}]}

    assert sorted(outcomes(item, run, {}, runs)) == [("dead", "tp"), ("nesting", "fp")]


def test_invalid_nemotron_items_leave_the_scoring():
    items = [make("n1", "nemotron", ["redundant_check"], "s1"), make("n2", "nemotron", ["dead"], "s1")]
    runs = {"n1": [{"kinds": {}} | MEASURE], "n2": [{"kinds": {"dead": []}} | MEASURE]}
    injections = {"n1": {"valid": False, "reason": "no earlier check"}, "n2": {"valid": True, "reason": "vulture"}}

    report = score(items, runs, {"labels": {}, "injections": injections})

    assert report["groups"]["nemotron"]["total"] == {"items": 1, "tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0}
    assert report["invalid_injections"] == {"n1": "no earlier check"}
    assert report["counts"]["origin"] == {"nemotron": 1}
    with pytest.raises(SystemExit, match="n2"):
        score(items, runs, {"labels": {}, "injections": {"n1": injections["n1"]}})


def test_score_ignores_the_removed_filler_comment_kind():
    items = [
        make("c1", "clean"),
        make("s1", "source"),
        make("t1", "transform", ["filler_comment"], "s1"),
        make("t2", "transform", ["dead", "filler_comment"], "s1"),
    ]
    labels = {"c1": {"filler_comment": {"decision": "slop"}}, "s1": {"filler_comment": {"decision": "false_positive"}}}
    runs = {
        "c1": [{"kinds": {"filler_comment": ["# x"]}} | MEASURE],
        "s1": [{"kinds": {"filler_comment": ["# x"]}} | MEASURE],
        "t1": [{"kinds": {"filler_comment": ["# x"]}} | MEASURE],
        "t2": [{"kinds": {"dead": [], "filler_comment": ["# x"]}} | MEASURE],
    }

    report = score(items, runs, {"labels": labels, "injections": {}})

    assert "filler_comment" not in report["groups"]["all"]
    assert report["groups"]["all"]["total"] == {"items": 1, "tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0}
    assert report["groups"]["two_kinds"]["total"]["items"] == 0
    assert report["unlabelled"] == [] and report["false_positives"] == []
    assert report["clean"]["any_kind_rate"] == 0.0
    assert report["counts"]["origin"] == {"clean": 1, "source": 1, "transform": 1}


def functions(count: int) -> list[Item]:
    sources = [make(f"s{n}", "source") for n in range(count)]
    return sources + [make(f"t{n}", "transform", ["dead"], f"s{n}") for n in range(count)] + [make(f"c{n}", "clean") for n in range(count)]


def test_split_keeps_each_function_in_one_set_and_is_deterministic():
    items = functions(10)

    sets = split(items)

    assert all(sets[f"t{n}"] == sets[f"s{n}"] for n in range(10))
    assert split(items[::-1]) == sets
    assert Counter(sets[i.id] for i in items if i.source_id is None) == {"tuning": 12, "held_out": 8}


def test_compare_finds_a_clear_improvement_and_no_change_between_equal_runs():
    items = functions(20)
    labels = {f"c{n}": {"nesting": {"decision": "false_positive"}} for n in range(20)}
    review = {"labels": labels, "injections": {}}
    # the gate before finds the injected kind in half of the items and flags half of the clean functions
    base = {f"t{n}": [{"kinds": {"dead": []} if n % 2 else {}}] for n in range(20)} | {f"c{n}": [{"kinds": {"nesting": []} if n % 2 else {}}] for n in range(20)}
    new = {f"t{n}": [{"kinds": {"dead": []}}] for n in range(20)} | {f"c{n}": [{"kinds": {}}] for n in range(20)}

    better = compare(items, review, base, new)
    same = compare(items, review, base, base)

    assert better["dead"]["recall"]["base"]["value"] == 0.5 and better["dead"]["recall"]["new"]["value"] == 1.0
    assert better["dead"]["recall"]["difference"]["low"] > 0
    assert better["nesting"]["fp_rate"]["difference"]["high"] < 0
    assert better["total"]["fp_rate"]["new"] == {"value": 0.0, "low": 0.0, "high": 0.0}
    differences = [entry["difference"] for kind in same.values() for entry in kind.values() if entry["difference"]["value"] is not None]
    assert differences and all(d["value"] == d["low"] == d["high"] == 0 for d in differences)


def test_compare_resamples_a_source_and_its_injected_items_together():
    items = [make("s1", "source"), make("t1", "transform", ["dead"], "s1"), make("c2", "clean")]
    review = {"labels": {"s1": {"nesting": {"decision": "slop"}}}, "injections": {}}
    runs = {"s1": [{"kinds": {"nesting": []}}], "t1": [{"kinds": {}}], "c2": [{"kinds": {}}]}

    recall = compare(items, review, runs, runs)["total"]["recall"]["base"]

    # by item, a draw could hold s1 without t1 (recall 1.0) or t1 without s1 (0.0); by function, s1 and t1 always come as a pair
    assert (recall["value"], recall["low"], recall["high"]) == (0.5, 0.5, 0.5)
    assert 600 < recall["resamples"] < 900


def test_compare_scores_both_arms_against_the_same_source_flags():
    items = [make("s1", "source"), make("t1", "transform", ["dead"], "s1")]
    review = {"labels": {}, "injections": {}}
    flagged = [{"kinds": {"dead": [], "nesting": []}}]
    # only the base arm flags nesting on the unlabelled source; both arms flag it on the injected item
    base = {"s1": [{"kinds": {"nesting": []}}], "t1": flagged}
    new = {"s1": [{"kinds": {}}], "t1": flagged}

    precision = compare(items, review, base, new)["total"]["precision"]

    assert precision["base"]["value"] == precision["new"]["value"] == 1.0
    assert precision["difference"]["value"] == 0


METHOD = Item("r:m.py:Store.get", "r", "c", "m.py", "Store.get", 2, 4, "    def get(self, key):\n        value = self.data[key]\n        return value\n", "source")


def reply(code: str) -> str:
    return f"Here it is.\n\n```python\n{code}```\n"


def test_from_reply_accepts_and_reindents_a_valid_reply():
    code = "def get(self, key):\n    unused = key\n    value = self.data[key]\n    return value\n"

    assert from_reply(METHOD, reply(code), "dead") == "    def get(self, key):\n        unused = key\n        value = self.data[key]\n        return value\n"


@pytest.mark.parametrize(
    "code",
    [
        "def get(self, key):\n    slop_value = 1\n    return self.data[key]\n",
        "def get(self, key):\n    unused = 1  # never used\n    return self.data[key]\n",
        "def fetch(self, key):\n    unused = 1\n    return self.data[key]\n",
    ],
)
def test_from_reply_rejects_a_labelled_or_renamed_reply(code):
    assert from_reply(METHOD, reply(code), "dead") is None
