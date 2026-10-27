import re
from html import escape as esc

from bench import showcase

NAV = [("index.html", "Home"), ("how.html", "How it works"), ("reviews.html", "Reviews"), ("benchmark.html", "Benchmark"), ("try.html", "Try it")]
STEP_LABEL = {
    "gate.index": "Index the base commit",
    "sandbox.prepare": "Set up the sandbox",
    "gate.collect": "Find the changed functions",
    "gate.baseline": "Run the repo tests on the old code",
    "gate.characterize": "Write tests",
    "gate.rewrite": "Rewrite",
    "gate.proof": "Check the rewrite",
    "gate.repo_suite": "Run the repo tests on the rewrites",
}
GLOSS = {
    "lookup_table": "long if/elif chain",
    "dead": "unused or unreachable code",
    "nesting": "deep nesting",
    "swallowed_error": "error hidden by except",
    "redundant_check": "same check twice",
    "wrapper": "function that only calls another",
    "duplicate": "copy of an existing function",
}
FLOW = [
    ("Find changed functions", "Slopgate lists the Python functions that the pull request adds or changes."),
    ("Name the problem", "Ruff, vulture, and syntax-tree checks label long if/elif chains, dead code, and deep nesting. To find a copy of an existing function, Slopgate matches its words against the repository, and Nemotron Super judges the close matches."),
    ("Write tests for the old code", "Nemotron Super writes tests that record what the old code does. The tests must pass on the old code."),
    ("Rewrite", "Nemotron Super rewrites the function. If the rewrite fails, Nemotron Ultra tries once more."),
    ("Check", "The rewrite must pass those tests and the repository's own tests. If it fails, the pull request gets a comment and no code change."),
    ("Post", "A rewrite that passes appears as a suggested change on the pull request. You decide whether to merge it."),
]
REPO = "https://github.com/agno-nymous/slopgate"
MOUNT = '<script src="try.js"></script>\n<script>if (window.SlopgateTry) SlopgateTry.mount(document.getElementById("live"));</script>'


def shell(file: str, title: str, body: str, nxt: tuple[str, str], scripts: str = "") -> str:
    up = "../" if "/" in file else ""
    current = file.split("/")[0] + ".html" if "/" in file else file
    links = "".join(f'<a href="{up}{href}"{" aria-current=" + chr(34) + ("page" if href == file else "true") + chr(34) if href == current else ""}>{label}</a>' for href, label in NAV)
    position = next((f'<p class="pos">{i + 1} of {len(NAV)}: {label}</p>\n' for i, (href, label) in enumerate(NAV) if href == file and i), "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<header class="top"><div class="topbar"><a class="brand" href="{up}index.html">Slopgate</a><nav aria-label="Pages">{links}</nav></div></header>
<main>
{position}{body}
<p class="next"><a href="{up}{nxt[0]}">{esc(nxt[1])}</a></p>
</main>
<footer><p>Slopgate reviews pull requests for slop that coding agents write. It runs on Nemotron models on Nebius Token Factory. <a href="{REPO}">Source on GitHub</a>.</p></footer>
{scripts}
</body>
</html>
"""


def diff(rows: list, extra: str = "") -> str:
    cls = {"+": "add", "-": "del", "@": "hunk", " ": "ctx"}
    out = []
    for op, line in rows:
        text = (line or "…") if op == "@" else (op + line)
        out.append(f'<span class="l {cls[op]}">{esc(text)}</span>')
    return f'<pre class="diff{extra}" tabindex="0"><code>{"".join(out)}</code></pre>'


def plain(text: str, extra: str = "") -> str:
    lines = "".join(f'<span class="l ctx">{esc(line) or " "}</span>' for line in text.splitlines())
    return f'<pre class="diff{extra}" tabindex="0"><code>{lines}</code></pre>'


def trimmed(rows: list, keep: str) -> list:
    rows = [row for row in rows if row[0] in " @" + keep]
    while rows and rows[-1][0] == " " and not rows[-1][1].strip():
        rows.pop()
    return rows


def money(usd: float) -> str:
    return f"${usd:.3f}"


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def figures(head: dict) -> str:
    return f"""<ul class="wide figures">
<li><b class="num">{head['detected']} of {head['items']}</b><span class="what">AI slop items found</span><span class="more">Slop that the benchmark added to {head['instances']} SWE-bench tasks from {head['repositories']} repositories.</span></li>
<li><b class="num">{head['accepted']}</b><span class="what">fixes that passed every test</span><span class="more">The other {head['detected'] - head['accepted']} found items got a review comment.</span></li>
<li><b class="num">{head['silent_breaks']}</b><span class="what">fixes that broke a repository test</span><span class="more">The gate never sees those tests.</span></li>
</ul>"""


def changes(item: dict) -> str:
    m = re.search(r"nesting (\d+) -> (\d+), complexity (\d+) -> (\d+)", item["summary"])
    if not m:
        return esc(item["summary"])
    a, b, c, d = m.groups()
    parts = []
    if a != b:
        parts.append(f"Nesting goes from {a} levels to {b}.")
    if c != d:
        parts.append(f"Code paths go from {c} to {d}.")
    parts.append(f"{plural(item['tests_passed'], 'test')} of the old behavior passed on the rewrite.")
    return " ".join(parts)


def home(data: dict) -> str:
    review = next(r for r in data["reviews"] if r["slug"] == "pylint-7993")
    item = review["items"][0]
    rows = [row for row in item["diff"] if row[0] != "@"]
    head = data["headline"]
    before, after = (int(n) for n in re.search(r"complexity (\d+) -> (\d+)", item["summary"]).groups())
    body = f"""<h1>Slopgate fixes the AI slop that coding agents write in Python.</h1>
<p>It runs on each GitHub pull request. It finds long if/elif chains, unreachable code, and deep nesting. Nemotron models on Nebius Token Factory rewrite them. Slopgate posts a rewrite only when tests pass on the old code and on the new code. The whole benchmark below cost ${head['usd']:.2f}.</p>
{figures(head)}
<div class="wide pair">
<figure><figcaption><span class="tag">before</span> Slop that the benchmark added to <code>{esc(item['function'])}</code> in pylint: {before} code paths</figcaption>{diff(trimmed(rows, '-'))}</figure>
<figure><figcaption><span class="tag">after</span> The rewrite that Slopgate posted: a lookup table, {after} code paths</figcaption>{diff(trimmed(rows, '+'))}</figure>
</div>
<p class="wide verdict ok">Passed: the {item['tests_passed']} tests written for the old code also pass on the rewrite.</p>"""
    return shell("index.html", "Slopgate", body, ("how.html", "Next: the 6 steps of a review"))


def how(data: dict) -> str:
    items = [f'<li><span class="n">{i + 1}</span><div><h2>{esc(name)}</h2><p>{esc(text)}</p></div></li>' for i, (name, text) in enumerate(FLOW)]
    body = f"""<h1>How a review works</h1>
<ol class="flow">
{''.join(items[:2])}
</ol>
<div class="sandbox"><p class="label">Steps 3 to 5 run in a Nebius ConTree sandbox</p>
<ol class="flow" start="3">
{''.join(items[2:5])}
</ol></div>
<ol class="flow" start="6">
{items[5]}
</ol>"""
    return shell("how.html", "How Slopgate works", body, ("reviews.html", f"Next: see {len(data['reviews'])} real reviews"))


def reviews(data: dict) -> str:
    rows = []
    for review in data["reviews"]:
        n = len(review["items"])
        kinds = ", ".join(sorted({kind for item in review["items"] for kind in item["kinds"]}))
        rows.append(f"""<li><h2><a href="reviews/{review['slug']}.html">{esc(review['title'])}</a></h2>
<p class="meta">{n} tested {'fix' if n == 1 else 'fixes'}. {plural(review['rejected'], 'more function')} got a comment. {review['seconds']}&nbsp;s, {money(review['usd'])}. <code>{esc(kinds)}</code></p></li>""")
    body = f"""<h1>Recorded reviews</h1>
<p>Each review is the unedited output of <code>slopgate review --dry-run</code>. The benchmark added the slop to code from these repositories. Open a review to read the diff.</p>
<ul class="list">
{''.join(rows)}
</ul>"""
    return shell("reviews.html", "Recorded reviews", body, ("benchmark.html", f"Next: the numbers on {data['headline']['items']} functions"))


def review_page(review: dict) -> str:
    items = []
    for item in sorted(review["items"], key=lambda i: -len(i["diff"])):
        tests = f'<details><summary>Tests the agent wrote for the old behavior ({item["tests_passed"]} passed on the rewrite)</summary>{plain(item["tests"], " tests")}</details>' if item["tests"] else ""
        kinds = ", ".join(f'{esc(GLOSS[kind])} (<code>{esc(kind)}</code>)' for kind in item["kinds"])
        items.append(f"""<section class="wide">
<h2><code>{esc(item['function'])}</code></h2>
<p class="kind">{kinds}</p>
<p>{changes(item)}</p>
{diff(trimmed(item['diff'], '-+'))}
{tests}
</section>""")
    longest = max(s["seconds"] for s in review["steps"])
    table = "".join(f'<tr><td>{esc(STEP_LABEL[s["name"]])}{" x" + str(s["count"]) if s["count"] > 1 else ""}</td><td class="r">{s["seconds"]}&nbsp;s</td><td class="bar"><i style="width:{max(1, round(100 * s["seconds"] / longest))}%"></i></td></tr>' for s in review["steps"])
    body = f"""<h1>{esc(review['title'])}</h1>
<p>{esc(review['why'])}</p>
<p class="facts">{review['seconds']}&nbsp;s and {money(review['usd'])} for the review. {plural(review['rejected'], 'more function')} got a comment. Source: <a href="{esc(review['source']['url'])}">{esc(review['source']['label'])}</a>.</p>
{''.join(items)}
<details class="times"><summary>Where the time went</summary><table><thead><tr><th scope="col">Step</th><th scope="col" class="r">Time</th><th scope="col"><span class="sr">Share of the longest step</span></th></tr></thead><tbody>{table}</tbody></table>
<p class="note">Step times add up across functions that run at the same time, so they can exceed the wall time. Several reviews ran together and shared Token Factory, so one review alone is faster. The step times and the token counts come from the Phoenix trace of the same run: {esc(review['tokens'])}.</p></details>"""
    return shell(f"reviews/{review['slug']}.html", review["title"], body, ("reviews.html", "All reviews"))


def benchmark(data: dict) -> str:
    head = data["headline"]
    words = {"proven": "tested fix", "note": "found, review comment only", "missed": "not found"}
    rows = []
    for k in head["kinds"]:
        counts = {c: k["cells"].count(c) for c in words}
        cells = "".join(f'<span class="cell {c}" title="{esc(k["kind"])}: {words[c]}"></span>' for c in k["cells"])
        gloss = esc(GLOSS[k["kind"]])
        rows.append(f'<div class="row" role="group" aria-label="{esc(k["kind"])} ({gloss}): {counts["proven"]} tested fixes, {counts["note"]} comment only, {counts["missed"]} not found"><code class="kind" title="{gloss}">{esc(k["kind"])}</code><span class="cells">{cells}</span><span class="count">{counts["proven"]} of {len(k["cells"])} fixed</span></div>')
    low = ", ".join(f'<code>{esc(k["kind"])}</code> ({k["cells"].count("proven")} of {len(k["cells"])})' for k in head["kinds"] if k["cells"].count("proven") / len(k["cells"]) < 0.2)
    body = f"""<h1>The benchmark</h1>
<p>Nemotron Super added one kind of slop to each of {head['items']} functions from {head['instances']} SWE-bench Lite tasks. The tasks come from {head['repositories']} repositories. Hidden repository tests cover all of these functions, and the gate never sees them. The whole run cost ${head['usd']:.2f}.</p>
{figures(head)}
<h2>Every function, one square each</h2>
<div class="waffle">
{''.join(rows)}
</div>
<p class="legend"><span><i class="cell proven"></i> tested fix</span> <span><i class="cell note"></i> found, review comment only</span> <span><i class="cell missed"></i> not found</span></p>
<p>Few fixes so far for {low}. Those functions still get a review comment.</p>"""
    return shell("benchmark.html", "Slopgate benchmark", body, ("try.html", "Next: try it on your own code"))


def try_page(data: dict) -> str:
    costs = [r["usd"] for r in data["reviews"]]
    commands = "".join(f'<li>{s["text"]}{plain(s["cmd"], " cmd") if s.get("cmd") else ""}</li>' for s in data["how"])
    body = f"""<h1>Try Slopgate</h1>
<p>Paste a Python function and your Nebius Token Factory key. The page asks Nemotron Super for a rewrite and for tests, then runs both versions in your browser. The key stays in this tab and goes only to Token Factory.</p>
<div id="live" class="live"></div>
<h2>Run it on your repository</h2>
<ol class="steps">{commands}</ol>
<p>One review cost {money(min(costs))} to {money(max(costs))} in Token Factory tokens in the {len(costs)} recorded reviews.</p>"""
    return shell("try.html", "Try Slopgate", body, ("index.html", "Back to the start"), MOUNT)


def pages(data: dict) -> dict:
    out = {"index.html": home(data), "how.html": how(data), "reviews.html": reviews(data), "benchmark.html": benchmark(data), "try.html": try_page(data)}
    for review in data["reviews"]:
        out[f"reviews/{review['slug']}.html"] = review_page(review)
    return out


def build() -> None:
    for file, text in pages(showcase.data()).items():
        path = showcase.DEMO / file
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)


if __name__ == "__main__":
    build()
