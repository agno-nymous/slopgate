import json
import os
import re
from pathlib import Path

from bench import pages, showcase

SECRETS = [
    r"eyJ[A-Za-z0-9_-]{10,}",
    r"\bv1\.[A-Za-z0-9_-]{20,}",
    r"project-[a-z0-9]{16,}",
    r"(?i)(?:api[_-]?key|secret|password)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}",
]
NETWORK = ["fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "<img", "<iframe", "@import", "url(http"]
HOSTS = {"api.tokenfactory.nebius.com", "cdn.jsdelivr.net", "tokenfactory.nebius.com", "github.com", "docs.astral.sh"}
TRY = showcase.DEMO / "try.js"
TEXT = {".html", ".css", ".js", ".json", ".txt"}


def html_files() -> list[Path]:
    return sorted(showcase.DEMO.rglob("*.html"))


def test_every_example_has_a_recording_and_its_meta_matches_it():
    for name in showcase.SPEC:
        result = json.loads((showcase.RECORDINGS / f"{name}.json").read_text())
        assert set(result) == {"suggestions", "followup", "rejected", "notes"}
        meta = json.loads((showcase.RECORDINGS / f"{name}.meta.json").read_text())
        proven = [re.search(r"rewrite of `([^`]+)`", e["body"])[1] for e in result["suggestions"]] + [e["function"] for e in result["followup"]]
        assert sorted(item["function"] for item in meta["items"]) == sorted(proven)
        assert meta["rejected"] == sum("function" in e for e in result["rejected"])


def secret_values() -> list[str]:
    values = {name: os.environ.get(name, "") for name in ("NEBIUS_API_KEY", "NEBIUS_PROJECT_ID")}
    for folder in [showcase.ROOT, *showcase.ROOT.parents[:3]]:
        env = folder / ".env"
        if env.is_file():
            for line in env.read_text().splitlines():
                name, _, value = line.partition("=")
                if name in values and not values[name]:
                    values[name] = value.strip().strip("\"'")
    return [value for value in values.values() if len(value) > 8]


def test_demo_files_hold_no_key():
    values = secret_values()
    for path in showcase.DEMO.rglob("*"):
        if path.suffix in TEXT:
            text = path.read_text()
            assert not any(re.search(pattern, text) for pattern in SECRETS), path
            assert not any(value in text for value in values), path


def test_pages_on_disk_are_current():
    built = pages.pages(showcase.data())
    assert sorted(str(p.relative_to(showcase.DEMO)) for p in html_files()) == sorted(built)
    for file, text in built.items():
        assert (showcase.DEMO / file).read_text() == text, file


def test_every_page_has_the_same_five_links_and_marks_the_current_one():
    for path in html_files():
        text = path.read_text()
        nav = re.search(r"<nav[^>]*>(.*?)</nav>", text, re.S)[1]
        assert [label for _, label in pages.NAV] == re.findall(r">([^<]+)</a>", nav), path
        assert len(re.findall(r"aria-current", nav)) == 1, path


def test_every_local_link_and_asset_resolves_to_a_file():
    for path in html_files() + [showcase.DEMO / "style.css"]:
        text = path.read_text()
        refs = re.findall(r'(?:href|src)="([^"]+)"', text) + re.findall(r"url\(([^)]+)\)", text)
        for ref in refs:
            if re.match(r"(https?:|#)", ref):
                continue
            assert (path.parent / ref.split("#")[0]).is_file(), (path, ref)


def test_pages_make_no_request_before_the_user_runs_the_gate():
    for path in html_files():
        text = path.read_text()
        assert [word for word in NETWORK if word in text] == [], path
        assert re.findall(r"<link[^>]*>", text) == [f'<link rel="stylesheet" href="{"../" if path.parent.name == "reviews" else ""}style.css">'], path
        scripts = re.findall(r'<script src="([^"]+)"', text)
        assert scripts == (["try.js"] if path.name == "try.html" else []), path
    assert "http" not in re.sub(r"https?://", "", (showcase.DEMO / "style.css").read_text())


def test_live_panel_sends_the_key_to_token_factory_only_and_stores_nothing():
    code = TRY.read_text()
    assert {re.match(r"https?://([^/\"'`\s)]+)", url)[1] for url in re.findall(r"https?://[^\"'`\s)]+", code)} <= HOSTS
    assert [word for word in ("localStorage", "sessionStorage", "document.cookie", "indexedDB", "console.") if word in code] == []
    assert "enable_thinking: false" in code


def test_fonts_are_self_hosted_and_swap():
    css = (showcase.DEMO / "style.css").read_text()
    assert len(re.findall(r"@font-face", css)) == 4
    assert len(re.findall(r"font-display: swap", css)) == 4
    assert "font-variant-ligatures: none" in css


def test_headline_equals_benchmark_report():
    total = json.loads((showcase.RESULTS / "swebench" / "swebench.json").read_text())["total"]
    head = showcase.data()["headline"]
    assert (head["items"], head["detected"], head["accepted"], head["silent_breaks"]) == (total["items"], total["detected"], total["accepted"], total["silent_breaks"])
    assert sum(len(k["cells"]) for k in head["kinds"]) == total["items"]
    assert sum(k["cells"].count("proven") for k in head["kinds"]) == total["accepted"]
    assert sum(k["cells"].count("missed") for k in head["kinds"]) == total["items"] - total["detected"]
    table = (showcase.RESULTS / "swebench" / "swebench.md").read_text()
    row = next(line for line in table.splitlines() if line.startswith("| total |"))
    assert [int(cell) for cell in row.split("|")[2:5]] == [head["items"], head["detected"], head["accepted"]]
    for page in ("index.html", "benchmark.html"):
        text = (showcase.DEMO / page).read_text()
        assert f'<b class="num">{head["detected"]} of {head["items"]}</b>' in text
        assert f'<b class="num">{head["accepted"]}</b>' in text
        assert f"The other {head['detected'] - head['accepted']} found items" in text


def test_reviews_show_only_proven_fixes_of_two_kinds():
    reviews = showcase.data()["reviews"]
    items = [item for review in reviews for item in review["items"]]
    assert len(reviews) >= 3
    assert len({kind for item in items for kind in item["kinds"]}) >= 2
    assert all(item["diff"] and item["summary"] for item in items)
    for review in reviews:
        page = (showcase.DEMO / "reviews" / f"{review['slug']}.html").read_text()
        assert page.count('class="diff') >= len(review["items"])
        assert "<details open" not in page and page.count("<details") <= len(review["items"]) + 1
        result = json.loads((showcase.RECORDINGS / f"{review['slug']}.json").read_text())
        rejected = [entry["function"] for entry in result["rejected"] if "function" in entry]
        assert rejected and not any(name in page for name in rejected)


def test_diff_rows_keeps_lines_that_start_with_dashes_and_marks_hunks():
    assert showcase.diff_rows("a\n--x\nb", "a\nb", 1) == [[" ", "a"], ["-", "--x"], [" ", "b"]]
    before = [str(i) for i in range(30)]
    after = before.copy()
    after[2], after[27] = "x", "y"
    rows = showcase.diff_rows("\n".join(before), "\n".join(after), 1)
    assert ["@", ""] in rows
