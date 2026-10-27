(function () {
  var API = "https://api.tokenfactory.nebius.com/v1/chat/completions";
  var MODEL = "nvidia/nemotron-3-super-120b-a12b";
  var PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
  var RETRY_WAITS = [5000, 15000, 45000];
  var RUN_LIMIT_MS = 20000;
  var MAX_LINES = 300;
  var FENCE = "`".repeat(3);
  var STEPS = [
    "Rewrite with Nemotron Super",
    "Write tests for the old behavior",
    "Run the tests on the old code",
    "Run the tests on the rewrite",
    "Verdict",
  ];
  var SAMPLES = [
    {
      name: "Nested checks",
      code: [
        "def can_checkout(user_active, has_items, address_ok, paid):",
        "    if user_active:",
        "        if has_items:",
        "            if address_ok:",
        "                if paid:",
        "                    return True",
        "                else:",
        "                    return False",
        "            else:",
        "                return False",
        "        else:",
        "            return False",
        "    else:",
        "        return False",
      ].join("\n"),
    },
    {
      name: "Swallowed error",
      code: [
        "def parse_port(text):",
        "    try:",
        "        try:",
        "            value = int(text)",
        "        except Exception:",
        "            return None",
        "        if value < 0:",
        "            return None",
        "        if value > 65535:",
        "            return None",
        "        return value",
        "    except Exception:",
        "        return None",
      ].join("\n"),
    },
    {
      name: "Long if/elif chain",
      code: [
        "def shipping_label(code):",
        '    if code == "ST":',
        '        return "Standard"',
        '    elif code == "EX":',
        '        return "Express"',
        '    elif code == "ON":',
        '        return "Overnight"',
        '    elif code == "PU":',
        '        return "Pickup"',
        '    elif code == "IN":',
        '        return "International"',
        "    else:",
        '        return "Unknown"',
      ].join("\n"),
    },
  ];

  var CSS = [
    ".live{min-width:0}",
    ".live *{box-sizing:border-box}",
    ".live h2{margin:0 0 8px;font:600 1.25rem/1.3 var(--sans)}",
    ".live h3{margin:0 0 8px;font:600 1rem/1.3 var(--sans)}",
    ".live label{display:block;margin:14px 0 6px;font:600 0.85rem var(--sans)}",
    ".live .note{margin:6px 0 0;font-size:0.85rem;color:var(--muted)}",
    ".live a{color:var(--link)}",
    ".live input,.live select,.live textarea{background:var(--paper);color:var(--ink);border:1px solid var(--rule);padding:10px 12px;font:inherit;width:100%;border-radius:0}",
    ".live textarea{font:0.85rem/1.5 var(--mono);overflow-x:auto;white-space:pre;resize:vertical}",
    ".live button{background:var(--ink);color:var(--ground);border:0;padding:12px 18px;font:600 0.95rem var(--sans);cursor:pointer;border-radius:0}",
    ".live button:disabled{opacity:0.5;cursor:default}",
    ".live button.quiet{background:transparent;color:var(--ink);border:1px solid var(--rule);padding:10px 14px}",
    ".live :focus-visible{outline:3px solid var(--link);outline-offset:2px}",
    ".live .bar{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}",
    ".live .steps{list-style:none;margin:18px 0 0;padding:0}",
    ".live .steps li{display:grid;grid-template-columns:5.5rem 1fr;gap:2px 10px;padding:6px 0;border-top:1px solid var(--rule)}",
    ".live .steps .st{font:600 0.78rem/1.6 var(--mono);color:var(--muted)}",
    ".live .steps li[data-state=running] .st{color:var(--link)}",
    ".live .steps li[data-state=done] .st{color:var(--keep)}",
    ".live .steps li[data-state=failed] .st{color:var(--drop)}",
    ".live .steps .dt{grid-column:2;font-size:0.85rem;color:var(--muted);overflow-wrap:anywhere}",
    ".live .steps .dt:empty{display:none}",
    ".live .steps .nm{grid-column:2}",
    ".live .steps .st{grid-column:1;grid-row:1}",
    ".live .steps .nm{grid-row:1}",
    ".live pre{margin:8px 0 0;padding:10px 0;font:0.82rem/1.5 var(--mono);overflow-x:auto;max-width:100%;background:var(--paper);border:1px solid var(--rule);tab-size:4}",
    ".live pre.text{padding:10px 12px}",
    ".live pre .l{display:block;padding:0 12px;min-width:max-content;white-space:pre}",
    ".live pre .add{background:var(--keep-wash);color:var(--keep)}",
    ".live pre .del{background:var(--drop-wash);color:var(--drop)}",
    ".live pre .ctx{color:var(--ink)}",
    ".live .verdict{margin:18px 0 0;padding:12px;font-weight:600;overflow-wrap:anywhere}",
    ".live .verdict.ok{background:var(--keep-wash);color:var(--keep)}",
    ".live .verdict.no{background:var(--drop-wash);color:var(--drop)}",
    ".live .verdict.err{background:var(--note-wash);color:var(--note)}",
    ".live details{margin-top:14px}",
    ".live summary{cursor:pointer;font-weight:600}",
    "@media (prefers-reduced-motion:reduce){.live *{animation:none!important;transition:none!important}}",
  ].join("\n");

  var worker = null;
  var workerReady = null;
  var jobs = {};
  var nextId = 1;

  var WORKER_SRC = [
    'importScripts("' + PYODIDE + 'pyodide.js");',
    "var ready = null;",
    "function load() {",
    '  if (!ready) ready = loadPyodide({ indexURL: "' + PYODIDE + '" }).catch(function (e) { ready = null; throw e; });',
    "  return ready;",
    "}",
    "load().then(function () { postMessage({ loaded: true }); }, function (e) { postMessage({ loadError: String(e && e.message || e) }); });",
    "onmessage = async function (ev) {",
    "  var id = ev.data.id;",
    "  var out = '';",
    "  try {",
    "    var py = await load();",
    "    py.setStdout({ batched: function (s) { out += s + '\\n'; } });",
    "    py.setStderr({ batched: function (s) { out += s + '\\n'; } });",
    "    var ns = py.globals.get('dict')();",
    "    await py.runPythonAsync(ev.data.code, { globals: ns });",
    "    ns.destroy();",
    "    postMessage({ id: id, ok: true, output: out });",
    "  } catch (e) {",
    "    var tb = String(e && e.message || e).trim().split('\\n').slice(-20).join('\\n');",
    "    postMessage({ id: id, ok: false, output: out + tb });",
    "  }",
    "};",
  ].join("\n");

  function startWorker() {
    var url = URL.createObjectURL(new Blob([WORKER_SRC], { type: "text/javascript" }));
    var w = new Worker(url);
    URL.revokeObjectURL(url);
    worker = w;
    workerReady = new Promise(function (resolve, reject) {
      w.onmessage = function (ev) {
        var d = ev.data;
        if (d.loaded) return resolve(w);
        if (d.loadError) {
          dropWorker(w);
          return reject(new Error("Could not load Python in the browser: " + d.loadError));
        }
        if (jobs[d.id]) jobs[d.id](d);
      };
      w.onerror = function () {
        dropWorker(w);
        reject(new Error("Could not start the Python worker in this browser."));
      };
    });
    return workerReady;
  }

  function dropWorker(w) {
    w.terminate();
    if (worker === w) {
      worker = null;
      workerReady = null;
    }
  }

  function defaultRunPython(code) {
    return (workerReady || startWorker()).then(function (w) {
      return new Promise(function (resolve) {
        var id = nextId++;
        var timer = setTimeout(function () {
          delete jobs[id];
          dropWorker(w);
          resolve({ ok: false, output: "", timeout: true });
        }, RUN_LIMIT_MS);
        jobs[id] = function (d) {
          clearTimeout(timer);
          delete jobs[id];
          resolve({ ok: d.ok, output: d.output });
        };
        w.postMessage({ id: id, code: code });
      });
    });
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function sleep(ms) {
    return new Promise(function (r) { setTimeout(r, ms); });
  }

  function extractPython(reply) {
    var m = /```python[^\n]*\n([\s\S]*?)```/.exec(reply);
    return m ? m[1].trim() : null;
  }

  function diffLines(a, b) {
    var x = a.split("\n");
    var y = b.split("\n");
    var t = [];
    var i, j;
    for (i = 0; i <= x.length; i++) t.push(new Array(y.length + 1).fill(0));
    for (i = x.length - 1; i >= 0; i--) {
      for (j = y.length - 1; j >= 0; j--) {
        t[i][j] = x[i] === y[j] ? t[i + 1][j + 1] + 1 : Math.max(t[i + 1][j], t[i][j + 1]);
      }
    }
    var out = [];
    i = 0;
    j = 0;
    while (i < x.length && j < y.length) {
      if (x[i] === y[j]) { out.push([" ", x[i]]); i++; j++; }
      else if (t[i + 1][j] >= t[i][j + 1]) out.push(["-", x[i++]]);
      else out.push(["+", y[j++]]);
    }
    while (i < x.length) out.push(["-", x[i++]]);
    while (j < y.length) out.push(["+", y[j++]]);
    return out;
  }

  function diffHtml(a, b) {
    var cls = { "+": "add", "-": "del", " ": "ctx" };
    return diffLines(a, b).map(function (p) {
      return '<span class="l ' + cls[p[0]] + '">' + esc(p[0] + p[1]) + "</span>";
    }).join("");
  }

  function rewritePrompt(source) {
    return [
      "Rewrite the Python function below. Fix these problems:",
      "",
      "- It nests blocks deeply. Flatten it with guard clauses or a single boolean expression.",
      "- It repeats a check that an earlier check already guarantees. Remove the repeated check.",
      "- It catches broad exceptions or wraps code that cannot raise in a try block. Narrow each except to the exceptions that the code in its try block raises, and remove try blocks around code that cannot raise. Every input must still give the same result.",
      "- It maps values to results with a long if/elif chain. Replace the chain with a dict lookup.",
      "- It has unreachable code or unused variables. Remove them.",
      "",
      "Rules:",
      "- Keep the exact signature, the decorators, and the behavior, bugs included.",
      "- Add no new functions, no lambdas, and no new classes.",
      "- If every return gives True or False, keep it that way: `a and b` returns `a` itself when `a` is falsy, so wrap such a chain in bool().",
      "- Reply with one ```python block that holds the full rewritten function, decorators included. Put no text outside the block.",
      "",
      FENCE + "python",
      source,
      FENCE,
    ].join("\n");
  }

  function testsPrompt(source) {
    return "Write characterization tests for the Python function below. The tests must pin down what it does today, bugs included. " +
      "Use only plain assert statements at module level (no pytest, no unittest, no imports other than the standard library, no network, no files, no randomness). " +
      "Call the function by its name; the function is already defined when the tests run. Cover every branch with at least 6 asserts. " +
      "Reply with one ```python block and no other text.\n\n" + FENCE + "python\n" + source + "\n" + FENCE;
  }

  function lastLine(output) {
    var lines = output.trim().split("\n");
    return lines[lines.length - 1] || "";
  }

  function checkTests(source, tests) {
    var m = /^\s*def\s+(\w+)/m.exec(source);
    if (m && new RegExp("^(?:async\\s+)?(?:def|class)\\s+" + m[1] + "\\b", "m").test(tests)) {
      throw new Error("The tests define " + m[1] + " again, so they would not test the rewrite.");
    }
  }

  function Reject(message) {
    this.message = message;
  }

  function mount(el, options) {
    options = options || {};
    var key = "";
    var running = false;
    var current = 0;

    if (!document.getElementById("slopgate-try-style")) {
      var style = document.createElement("style");
      style.id = "slopgate-try-style";
      style.textContent = CSS;
      document.head.appendChild(style);
    }
    el.classList.add("live");
    el.innerHTML = [
      "<section>",
      "<h2>Try the gate on your own function</h2>",
      '<label for="sg-key">Nebius Token Factory key</label>',
      '<input id="sg-key" type="password" autocomplete="off" spellcheck="false">',
      '<p class="note">Sent only to api.tokenfactory.nebius.com, from your browser. Not stored. ',
      '<a href="https://tokenfactory.nebius.com/project/api-keys" target="_blank" rel="noopener noreferrer">Get a key</a></p>',
      '<label for="sg-sample">Sample</label>',
      '<select id="sg-sample">',
      SAMPLES.map(function (s, i) { return '<option value="' + i + '">' + esc(s.name) + "</option>"; }).join(""),
      "</select>",
      '<label for="sg-code">Python function (one top-level function, standard library only, no I/O)</label>',
      '<textarea id="sg-code" rows="14" spellcheck="false" wrap="off"></textarea>',
      '<div class="bar"><button type="button" id="sg-run">Run the gate</button>',
      '<button type="button" class="quiet" id="sg-forget">Forget key</button></div>',
      '<ol class="steps" aria-live="polite" hidden></ol>',
      '<div class="result" role="status"></div>',
      "</section>",
    ].join("");

    function $(sel) { return el.querySelector(sel); }
    var keyInput = $("#sg-key");
    var sample = $("#sg-sample");
    var code = $("#sg-code");
    var runBtn = $("#sg-run");
    var stepsEl = $(".steps");
    var resultEl = $(".result");
    code.value = SAMPLES[0].code;

    sample.addEventListener("change", function () { code.value = SAMPLES[+sample.value].code; });
    keyInput.addEventListener("input", function () { key = keyInput.value.trim(); });
    $("#sg-forget").addEventListener("click", function () { key = ""; keyInput.value = ""; });

    function setStep(i, state, text) {
      var li = stepsEl.children[i];
      li.dataset.state = state;
      li.querySelector(".st").textContent = state;
      li.querySelector(".dt").textContent = text || "";
    }

    function scrub(text) {
      return key ? String(text).split(key).join("[key]") : String(text);
    }

    async function request(messages) {
      for (var n = 0; ; n++) {
        var res;
        try {
          res = await fetch(API, {
            method: "POST",
            headers: { Authorization: "Bearer " + key, "Content-Type": "application/json" },
            body: JSON.stringify({
              model: MODEL,
              messages: messages,
              max_tokens: 4096,
              temperature: 0,
              chat_template_kwargs: { enable_thinking: false },
            }),
          });
        } catch (e) {
          throw new Error("Network error. Check the connection and try again.");
        }
        if (res.status === 401 || res.status === 403) throw new Error("The key was refused. Check the key.");
        if ((res.status === 429 || res.status >= 500) && n < RETRY_WAITS.length) {
          setStep(current, "running", "Server busy (HTTP " + res.status + "). Retrying in " + RETRY_WAITS[n] / 1000 + " s.");
          await sleep(RETRY_WAITS[n]);
          setStep(current, "running", "");
          continue;
        }
        if (!res.ok) {
          var body = "";
          try { body = (await res.text()).slice(0, 300); } catch (e) { body = ""; }
          throw new Error(scrub("The API returned HTTP " + res.status + (body ? ": " + body : ".")));
        }
        var data = await res.json();
        var choice = data && data.choices && data.choices[0];
        if (choice && choice.finish_reason === "length") throw new Error("The model reply was cut off (token limit); try a shorter function.");
        var text = choice && choice.message && choice.message.content;
        if (typeof text !== "string") throw new Error("The API reply had no text.");
        return text;
      }
    }

    function complete(messages) {
      if (options.complete) return options.complete(messages);
      if (!key) return Promise.reject(new Error("Enter your Nebius Token Factory key first."));
      return request(messages);
    }

    var runPython = options.runPython || defaultRunPython;

    function render(res, verdict, kind) {
      var html = "";
      if (res.neu) {
        html += "<h3>Diff</h3><pre>" + diffHtml(res.old, res.neu) + "</pre>";
      }
      if (res.tests) {
        html += "<details><summary>Generated tests</summary><pre class=\"text\">" + esc(res.tests) + "</pre></details>";
      }
      [["Test output on the old code", res.runOld], ["Test output on the rewrite", res.runNew]].forEach(function (p) {
        if (!p[1]) return;
        html += "<h3>" + p[0] + " (" + (p[1].ok ? "passed" : "failed") + ")</h3><pre class=\"text\">" +
          esc(p[1].output.trim() || "(no output)") + "</pre>";
      });
      resultEl.innerHTML = html + '<p class="verdict ' + kind + '">' + esc(verdict) + "</p>";
    }

    async function execute(program, res, field) {
      var r = await runPython(program);
      res[field] = r;
      if (r.timeout) throw new Reject("a run took longer than " + RUN_LIMIT_MS / 1000 + " s.");
      return r;
    }

    async function runGate() {
      var source = code.value.replace(/\s+$/, "");
      resultEl.textContent = "";
      if (!source.trim()) {
        resultEl.innerHTML = '<p class="verdict err">Paste a Python function first.</p>';
        return;
      }
      if (source.split("\n").length > MAX_LINES) {
        resultEl.innerHTML = '<p class="verdict err">Paste one function of at most ' + MAX_LINES + " lines.</p>";
        return;
      }
      running = true;
      runBtn.disabled = true;
      stepsEl.hidden = false;
      stepsEl.innerHTML = STEPS.map(function (s) {
        return '<li data-state="pending"><span class="st">pending</span><span class="nm">' + esc(s) + '</span><span class="dt"></span></li>';
      }).join("");
      var res = { old: source };
      try {
        current = 0;
        setStep(0, "running");
        var reply = await complete([{ role: "user", content: rewritePrompt(source) }]);
        var rewrite = extractPython(reply);
        if (rewrite === null) throw new Reject("the model reply had no Python code block.");
        res.neu = rewrite;
        if (rewrite === source.trim()) throw new Reject("the rewrite is the same code.");
        setStep(0, "done");

        current = 1;
        setStep(1, "running");
        var testsMessages = [{ role: "user", content: testsPrompt(source) }];
        var testsReply = await complete(testsMessages);
        var tests = extractPython(testsReply);
        if (tests === null) throw new Reject("the model reply had no test code block.");
        checkTests(source, tests);
        res.tests = tests;
        setStep(1, "done");

        current = 2;
        setStep(2, "running", options.runPython || worker ? "" : "Loading Python in your browser (about 10 MB, once)");
        var oldRun = await execute(source + "\n\n" + tests, res, "runOld");
        if (!oldRun.ok) {
          setStep(2, "running", "Tests failed on the old code. Asking the model to fix them once.");
          var fixed = extractPython(await complete(testsMessages.concat([
            { role: "assistant", content: testsReply },
            { role: "user", content: "These tests failed on the original code: " + oldRun.output + ". Fix the tests. Reply with one ```python block." },
          ])));
          if (fixed === null) throw new Reject("the tests do not pass on the old code, so they cannot prove anything.");
          checkTests(source, fixed);
          tests = fixed;
          res.tests = tests;
          oldRun = await execute(source + "\n\n" + tests, res, "runOld");
          if (!oldRun.ok) throw new Reject("the tests do not pass on the old code, so they cannot prove anything.");
        }
        var count = (tests.match(/^assert\b/gm) || []).length;
        if (!count) throw new Reject("the tests contain no assert statements.");
        setStep(2, "done", count + " tests passed");

        current = 3;
        setStep(3, "running");
        var newRun = await execute(rewrite + "\n\n" + tests, res, "runNew");
        if (!newRun.ok) {
          var last = lastLine(newRun.output);
          throw new Reject(/^AssertionError/.test(last) ? "the rewrite fails a test." : "Python error in the rewrite: " + last);
        }
        setStep(3, "done");
        setStep(4, "done");
        render(res, "Passed: the rewrite passes the same " + count + " tests as the old code.", "ok");
      } catch (e) {
        if (e instanceof Reject) {
          setStep(current, "failed");
          setStep(4, "failed");
          render(res, "Rejected: " + e.message, "no");
        } else {
          setStep(current, "failed");
          render(res, scrub(e && e.message || e), "err");
        }
      } finally {
        running = false;
        runBtn.disabled = false;
      }
    }

    runBtn.addEventListener("click", function () { if (!running) runGate(); });
  }

  window.SlopgateTry = { mount: mount };
})();
