# agent-harness

[![tests](https://github.com/paoloap-py/agent-harness/actions/workflows/test.yml/badge.svg)](https://github.com/paoloap-py/agent-harness/actions/workflows/test.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

The companion code for **[The Complete Guide to Agent Harnesses (With Code)](https://medium.com/data-science-collective)**.

A coding agent loop is six lines, twenty with error handling. Everything else is the harness: the code that decides what the model is allowed to do, what it can
reach, what it remembers, who checks its work, and what it gets to see.

This repo ships five layers. For each one you can run the layer with its guard on,
and the same agent with it off. Same agent, same script, same system prompt, both times.
The only thing that changes is where the rule lives.

Every demo runs with **no API key**. The model is replaced by a scripted stand-in,
because a difference you can run beats a claim you have to trust.

```bash
git clone https://github.com/paoloap-py/agent-harness-guide
cd agent-harness-guide

python3 failures/01_no_execution_boundary.py   # guard off: deletes the client file
python3 layers/01_execution_boundary.py        # same agent, nothing deleted
```

## The five layers

| # | Layer | The question it answers | Status |
|---|-------|-------------------------|--------|
| 1 | **Execution boundary** | What is the agent allowed to do? | deletes the wrong file → denied |
| 2 | **Sandboxing** | What can it reach? | leaks a key via `../` → unreachable |
| 3 | **Memory persistence** | What survives a context reset? | forgets a decision → survives |
| 4 | **Verification loops** | Who checks the work, and can it silently fix things? | reviewer rewrites code → read-only |
| 5 | **Context pipelines** | What does the model see, and what does that cost? | 9,602 tokens → 2 |

## Run it

```bash
python3 run_all.py        # all five layers, guard off then on, side by side
python3 test_harness.py   # asserts every difference above, 10 checks
```

No dependencies and no API key. `shared/fake_agent.py` replaces the model with a
scripted stand-in that emits a fixed sequence of tool calls, so the only thing
that changes between the two columns is the harness. Lift that file on its own if
you want deterministic harness tests without paying a provider for them; it is
about forty lines and it is the reason this repo's CI can assert behaviour rather
than smoke-test it.

`test_harness.py` checks both directions: each failure script must still fail, and
each layer script must still prevent it. Remove a guard and the suite goes red.

## Use it in your own agent

One file, no dependencies. Copy `harness.py` into your project and wrap the `execute` your loop already calls. Sync or async — `boundary()` detects
a coroutine function, because handing an async loop an un-awaited coroutine is a
guard that silently does nothing.

```python
from harness import boundary, allowlist, Store, read_only, dry_run, Distiller

execute = boundary([("delete-needs-approval",
                     lambda c: c.name == "delete_file"
                               and not c.args.get("approved_by_human"),
                     "deletion requires an explicit human approval flag")])(execute)

result = execute(call)
if isinstance(result, Denied):        # a type, not a string you match on
    log.warning("refused by %s", result.rule)

execute.denials                       # {"delete-needs-approval": 3}
```

`Denied` subclasses `str`, so it drops into the same slot a tool result goes and
existing loops keep working unchanged.

`allowlist(["work"])` guards paths. `host_allowlist(["api.openai.com"])` guards
the network, comparing the parsed hostname rather than the string, so
`api.openai.com.evil.com` and `evil.com/?x=api.openai.com` are both refused.

The demos teach each layer. This is the part you keep.

`examples/real_loop.py` is all five wrapped around a real provider loop. It runs
with no API key: without one it prints the request it would have sent and uses a
canned tool call, which is the same dry-run-by-default idea Layer 4 teaches.

```bash
python3 examples/real_loop.py                  # canned, runs anywhere
OPENAI_API_KEY=sk-... python3 examples/real_loop.py
```

## What bites first

Six things that catch people, in the order they hit:

0. **These guards only see calls that go through the `execute` you wrapped.**
   A shell tool, a subprocess, or a second client reaches the same file without
   ever touching them. That is Layer 2's job, and it is why a check inside your
   own program is workflow control rather than a security boundary. See
   [SECURITY.md](SECURITY.md).
1. **Your loop must be able to read a refusal.** `boundary` returns a `Denied`
   in the same slot a tool result goes. If your loop treats any string as
   success, the agent sails past the guard believing it worked.
2. **A rule that matches too broadly deadlocks.** Same call, same deterministic
   refusal, forever, at full token price. `boundary(rules, max_repeats=3)`
   detects identical consecutive denials and changes the message so the loop has
   something new to react to. Tune it; do not remove it.
3. **`allowlist` returns `None`, not a path.** That is the refusal. Handle it
   before it reaches `open()`, or you trade a security bug for a `TypeError`.
4. **`dry_run` consumes a `dry_run` kwarg.** If your real function already takes
   a parameter by that name, rename one of them.
5. **`Store.reset()` clears only the conversation.** That is the point, and it
   will surprise you the first time disk state outlives a reset you meant as a
   wipe.
6. **`Distiller` counts words, not tokens.** The ratio is honest, the absolute
   is not. Swap in your provider's tokenizer before quoting a number.

## The principle underneath all five

Move enforcement out of the prompt and into deterministic code.

A rule in a system prompt is a bet that the model remembers it, interprets it the way
you meant, and follows it under context pressure. The model wins that bet most of the time, which is
the reason you stop checking.

Layer 1 is the generalised form of a real gate. The rule "never apply an edit the
human has not approved" lived in a skill file as prose for two weeks and was violated
eleven times in a single session. Rewritten as a pre-execution hook that denies the
call, it has been wrong twice since, both times because the rule was written too
narrowly. Both times there was a line to open and point at.

## Audit your own setup

For each layer, ask: **is this enforced by code, or by a sentence in a prompt?**

- [ ] Every irreversible action passes a check that runs before the tool does
- [ ] The agent can only reach paths and services you listed, and the list is code
- [ ] A context reset loses the conversation and keeps the committed work
- [ ] Something reviews the output that is not the thing that produced it
- [ ] The reviewer is read-only, so its critique cannot quietly become a fix
- [ ] You know what a turn costs, and what fraction of it is context you chose to send

Any box you cannot tick with a file path is a rule you are hoping for.

---

If this saved you an afternoon, star it. It is how other people find it before
their agent deletes the wrong file.
