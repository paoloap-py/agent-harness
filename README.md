# The Agent Harness Checklist

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

All ten scripts run. `for f in failures/*.py layers/*.py; do python3 "$f"; done`

## The principle underneath all five

Move enforcement out of the prompt and into deterministic code.

A rule in a system prompt is a bet that the model remembers it, interprets it the way
you meant, and follows it under context pressure. That bet pays out most of the time,
which is what makes it dangerous: it fails rarely enough that you trust it and often
enough to hurt.

Layer 1 is the generalised form of a real gate. The rule "never apply an edit the
human has not approved" lived in a skill file as prose for two weeks and was violated
eleven times in a single session. Rewritten as a pre-execution hook that denies the
call, it has not been violated since, because it cannot be.

## Audit your own setup

For each layer, ask: **is this enforced by code, or by a sentence in a prompt?**

- [ ] Every irreversible action passes a check that runs before the tool does
- [ ] The agent can only reach paths and services you listed, and the list is code
- [ ] A context reset loses the conversation and keeps the committed work
- [ ] Something reviews the output that is not the thing that produced it
- [ ] The reviewer is read-only, so its critique cannot quietly become a fix
- [ ] You know what a turn costs, and what fraction of it is context you chose to send

Any box you cannot tick with a file path is a rule you are hoping for.
