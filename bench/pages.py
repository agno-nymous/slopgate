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
    "gate.proof": "Prove the rewrite",
    "gate.repo_suite": "Run the repo tests on the rewrites",
}
REPO = "https://github.com/agno-nymous/slopgate"
MOUNT = '<script src="try.js"></script>\n<script>if (window.SlopgateTry) SlopgateTry.mount(document.getElementById("live"));</script>'


def shell(file: str, title: str, body: str, nxt: tuple[str, str], scripts: str = "") -> str:
    up = "../" if "/" in file else ""
    current = file.split("/")[0] + ".html" if "/" in file else file
    links = "".join(f'<a href="{up}{href}"{" aria-current=" + chr(34) + ("page" if href == file else "true") + chr(34) if href == current else ""}>{label}</a>' for href, label in NAV)
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
{body}
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


def home(data: dict) -> str:
    review = next(r for r in data["reviews"] if r["slug"] == "pylint-7993")
    item = review["items"][0]
    rows = [row for row in item["diff"] if row[0] != "@"]
    head = data["headline"]
    flagged = round(100 * head["detected"] / head["items"])
    proven = round(100 * head["accepted"] / head["detected"])
    before, after = (int(n) for n in re.search(r"complexity (\d+) -> (\d+)", item["summary"]).groups())
    body = f"""<h1>Slopgate rewrites agent slop and proves the rewrite still works.</h1>
<div class="wide pair">
<figure><figcaption><span class="tag">before</span> <code>{esc(item['function'])}</code> in pylint, complexity {before}</figcaption>{diff(trimmed(rows, '-'))}</figure>
<figure><figcaption><span class="tag">after</span> the same function as a lookup table, complexity {after}</figcaption>{diff(trimmed(rows, '+'))}</figure>
</div>
<p class="wide verdict ok">Proof passed. {item['tests_passed']} tests that pin the old behavior pass on the old code and on the rewrite.</p>
<ul class="wide figures">
<li><b class="num">{flagged}%</b><span>Slopgate flags {flagged}% of injected slop on real SWE-bench repos ({head['detected']} of {head['items']} items).</span></li>
<li><b class="num">{proven}%</b><span>of the flagged items get a proven one-click fix ({head['accepted']} of {head['detected']}). {head['silent_breaks']} of these fixes broke a hidden test.</span></li>
<li><b class="num">${head['usd']:.2f}</b><span>for the whole run on {head['instances']} SWE-bench instances of {head['repositories']} repositories.</span></li>
</ul>"""
    return shell("index.html", "Slopgate", body, ("how.html", "Next: how a review works"))


def how(data: dict) -> str:
    sentences = [
        "Find the Python functions that the pull request adds or changes.",
        "Ruff, vulture, and AST checks name the slop kind. Only duplicates need a model.",
        "Nemotron Super writes tests that pin the behavior of the old code. It runs them on the old code to check them.",
        "Nemotron Super rewrites the function. Nemotron Ultra tries again when a rewrite fails.",
        "The rewrite must pass the same tests and the tests of the repository. A rewrite that fails gets a review note, not a change.",
    ]
    items = [f'<li><span class="n">{i + 1}</span><div><h2>{esc(step["name"])}</h2><p>{esc(sentences[i])}</p></div></li>' for i, step in enumerate(data["steps"])]
    sandbox = "".join(items[2:])
    body = f"""<h1>How a review works</h1>
<ol class="flow">
{''.join(items[:2])}
</ol>
<div class="sandbox"><p class="label">Nebius ConTree sandbox: steps 3 to 5</p>
<ol class="flow" start="3">
{sandbox}
</ol></div>
<p>The gate posts a proven rewrite as a suggested change on the pull request. When the function is not all inside the diff, it posts a follow-up pull request. Nothing is merged for you.</p>"""
    return shell("how.html", "How Slopgate works", body, ("reviews.html", "Next: recorded reviews"))


def kinds_of(review: dict) -> str:
    return ", ".join(sorted({kind for item in review["items"] for kind in item["kinds"]}))


def reviews(data: dict) -> str:
    rows = []
    for review in data["reviews"]:
        name = review["slug"]
        n = len(review["items"])
        rows.append(f"""<li><h2><a href="reviews/{name}.html">{esc(review['title'])}</a></h2>
<p class="meta"><code>{esc(kinds_of(review))}</code>. <span class="ok">{n} proven</span>. {review['rejected']} other flagged {'function' if review['rejected'] == 1 else 'functions'} got a note. {review['seconds']} s, {money(review['usd'])}.</p></li>""")
    body = f"""<h1>Recorded reviews</h1>
<p>Each review is the unedited output of <code>slopgate review --dry-run</code> on a real repository from SWE-bench. Open one to read the diff and the tests.</p>
<ul class="list">
{''.join(rows)}
</ul>"""
    return shell("reviews.html", "Recorded reviews", body, ("benchmark.html", "Next: the benchmark"))


def review_page(review: dict) -> str:
    items = []
    for item in review["items"]:
        tests = f'<details><summary>Tests the agent wrote for the old behavior ({item["tests_passed"]} passed on the rewrite)</summary>{plain(item["tests"], " tests")}</details>' if item["tests"] else ""
        items.append(f"""<section class="wide">
<h2><code>{esc(item['function'])}</code> <span class="kind"><code>{esc(', '.join(item['kinds']))}</code></span></h2>
<p>{esc(item['summary'].replace(' -> ', ' to '))} Posted as a {esc(item['where'])}.</p>
{diff(trimmed(item['diff'], '-+'))}
{tests}
</section>""")
    longest = max(s["seconds"] for s in review["steps"])
    table = "".join(f'<tr><td>{esc(STEP_LABEL[s["name"]])}{" x" + str(s["count"]) if s["count"] > 1 else ""}</td><td class="r">{s["seconds"]} s</td><td class="bar"><i style="width:{max(1, round(100 * s["seconds"] / longest))}%"></i></td></tr>' for s in review["steps"])
    body = f"""<h1>{esc(review['title'])}</h1>
<p class="facts"><a href="{esc(review['source']['url'])}">{esc(review['source']['label'])}</a>. <b>{review['seconds']} s</b> wall time, <b>{money(review['usd'])}</b>, {esc(review['tokens'])}. {review['rejected']} other flagged {'function' if review['rejected'] == 1 else 'functions'} got a note.</p>
<p>{esc(review['why'])}</p>
{''.join(items)}
<details class="times"><summary>Where the time went</summary><table><thead><tr><th scope="col">Step</th><th scope="col" class="r">Time</th><th scope="col"><span class="sr">Share of the longest step</span></th></tr></thead><tbody>{table}</tbody></table>
<p class="note">Step times add up across functions that run at the same time, so they can exceed the wall time. Several reviews ran together and shared Token Factory, so one review alone is faster. The step times and the token counts come from the Phoenix trace of the same run.</p></details>"""
    return shell(f"reviews/{review['slug']}.html", review["source"]["label"].split(",")[0] + " review", body, ("reviews.html", "All reviews"))


def benchmark(data: dict) -> str:
    head = data["headline"]
    words = {"proven": "proven fix", "note": "flagged, review note only", "missed": "not flagged"}
    rows = []
    for k in head["kinds"]:
        counts = {c: k["cells"].count(c) for c in words}
        cells = "".join(f'<span class="cell {c}" title="{esc(k["kind"])}: {words[c]}"></span>' for c in k["cells"])
        rows.append(f'<div class="row" role="group" aria-label="{esc(k["kind"])}: {counts["proven"]} proven, {counts["note"]} note only, {counts["missed"]} not flagged"><code class="kind">{esc(k["kind"])}</code><span class="cells">{cells}</span><span class="count">{counts["proven"]} of {len(k["cells"])}</span></div>')
    flagged = round(100 * head["detected"] / head["items"])
    proven = round(100 * head["accepted"] / head["detected"])
    low = ", ".join(f'<code>{esc(k["kind"])}</code> has {k["cells"].count("proven")} of {len(k["cells"])}' for k in head["kinds"] if k["cells"].count("proven") / len(k["cells"]) < 0.2)
    body = f"""<h1>The benchmark</h1>
<p>Nemotron Super injected one kind of slop into each of {head['items']} functions. The functions come from {head['instances']} SWE-bench Lite instances of {head['repositories']} repositories. Hidden tests run all of them, and the gate never sees those tests. The whole run cost ${head['usd']:.2f}.</p>
<ul class="figures">
<li><b class="num">{flagged}%</b> flagged: {head['detected']} of {head['items']} injected items.</li>
<li><b class="num">{proven}%</b> of the flagged items got a proven fix: {head['accepted']} of {head['detected']}.</li>
<li><b class="num">{head['silent_breaks']}</b> of the proven fixes broke a hidden test.</li>
</ul>
<h2>Every function, one square each</h2>
<div class="waffle">
{''.join(rows)}
</div>
<p class="legend"><span><i class="cell proven"></i> proven fix</span> <span><i class="cell note"></i> flagged, review note only</span> <span><i class="cell missed"></i> not flagged</span></p>
<p>Some kinds get few fixes yet: {low}. The gate flags them and writes a review note.</p>"""
    return shell("benchmark.html", "Slopgate benchmark", body, ("try.html", "Next: try it"))


def try_page(data: dict) -> str:
    costs = [r["usd"] for r in data["reviews"]]
    commands = "".join(f'<li>{s["text"]}{plain(s["cmd"], " cmd") if s.get("cmd") else ""}</li>' for s in data["how"])
    body = f"""<h1>Try Slopgate</h1>
<p>Paste a Python function and a Nebius Token Factory key. The page rewrites the function, writes tests, and runs both versions in your browser. The key stays in this tab and goes only to Token Factory.</p>
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
