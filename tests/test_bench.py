import ast

import pytest

from bench.detect import Item, accept, from_reply, function, measured, splice
from bench.score import MEASURED, outcomes, score
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

FILLER = '''\
def report(rows):
    total = 0
    for row in rows:
        total += row.value
    print(total)
    return total
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
    if kind in MEASURED:
        before = measured(source.path, source.start, source.source, text)
        after = kinds.measured(function(source, item.source), splice(source, item.source, text))
        assert after - before == {kind}
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


def test_redundant_check_inserts_a_grounded_check():
    item = injected("redundant_check", REDUNDANT, "total")
    assert item.changed_lines == ["if prices is not None:"]
    assert kinds.grounded_line("redundant_check", item.changed_lines[0], item.source)


def test_filler_comments_restate_the_next_line():
    item = injected("filler_comment", FILLER, "report")
    assert item.changed_lines == ["# set total", "# loop over rows", "# update total"]
    assert all(kinds.grounded_line("filler_comment", line, item.source) for line in item.changed_lines)


def test_filler_skips_a_function_with_a_comment():
    assert transform("filler_comment", "def f(rows):\n    # why\n    total = 0\n    total += 1\n    return total\n", "") is None


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


MEASURE = {"seconds": 1.0, "input_tokens": 10, "output_tokens": 2}


def test_score_counts_tp_fp_fn_and_unlabelled():
    items = [make("c1", "clean"), make("c2", "clean"), make("s1", "source"), make("t1", "transform", ["dead"], "s1")]
    labels = {"c1": {"swallowed_error": {"decision": "slop"}, "nesting": {"decision": "false_positive"}}}
    runs = {
        "c1": [{"kinds": {"swallowed_error": [], "nesting": []}} | MEASURE],
        "c2": [{"kinds": {"dead": []}} | MEASURE, {"error": "boom"} | MEASURE],
        "s1": [{"kinds": {}} | MEASURE],
        "t1": [{"kinds": {"filler_comment": ["# x"]}} | MEASURE],
    }

    report = score(items, runs, {"labels": labels, "injections": {}})

    assert report["groups"]["all"]["total"] == {"items": 2, "tp": 1, "fp": 1, "fn": 1, "precision": 0.5, "recall": 0.5}
    assert report["groups"]["transform"]["dead"] == {"items": 1, "tp": 0, "fp": 0, "fn": 1, "precision": None, "recall": 0.0}
    assert report["unlabelled"] == [{"id": "c2", "kind": "dead", "runs": 1}, {"id": "t1", "kind": "filler_comment", "runs": 1}]
    assert report["clean"]["fp_rate"]["total"] == 0.5
    assert report["clean"]["any_kind_rate"] == 1.0
    assert report["errors"] == [{"id": "c2", "error": "boom"}]
    assert report["stability"]["clean"] == 0.5


def test_injected_item_scores_only_what_its_source_does_not():
    item = make("t1", "transform", ["redundant_check"], "s1")
    labels = {"s1": {"filler_comment": {"decision": "false_positive"}, "nesting": {"decision": "slop"}}}
    run = {"kinds": {"redundant_check": ["if x:"], "filler_comment": ["# x"], "nesting": [], "dead": []}}

    assert sorted(outcomes(item, run, labels)) == [("dead", "fp"), ("redundant_check", "tp")]
    assert outcomes(item, {"kinds": {}}, labels) == [("redundant_check", "fn")]


def test_unknown_llm_kind_on_an_injected_item_is_unlabelled():
    item = make("t2", "transform", ["dead"], "s2")

    assert sorted(outcomes(item, {"kinds": {"filler_comment": ["# y"], "dead": []}}, {})) == [("dead", "tp"), ("filler_comment", "unlabelled")]


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
