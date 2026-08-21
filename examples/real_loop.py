"""All five layers wrapped around a real API loop.

Runs with no API key. Without OPENAI_API_KEY it uses a canned response and
prints the request it would have sent, which is the same dry-run-by-default
principle Layer 4 teaches: the safe path is what you get for free.

    python3 examples/real_loop.py                 # canned, runs anywhere
    OPENAI_API_KEY=sk-... python3 examples/real_loop.py

The point of this file is the WIRING, not the model. Six lines of loop, five
wraps around it, and the guards are the same objects from harness.py.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness import boundary, allowlist, Store, read_only, dry_run, Distiller

DISK = {"work/report.md": "Q3 numbers, still rough",
        "secrets/api_key": "sk-live-DO-NOT-LEAK"}

TOOLS = [{"type": "function", "function": {
    "name": "read_file",
    "description": "Read a file from the project",
    "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                   "required": ["path"]}}}]


class Call:
    """Whatever your provider returns, normalise it to this before the guards
    see it. The guards do not know or care which API you are on."""
    def __init__(self, name, args):
        self.name, self.args = name, args


# ---- layer 2: the process may only reach work/ ----------------------------
resolve = allowlist(["work"])

# ---- layer 3: three destinations, named at write time ---------------------
store = Store()

# ---- layer 5: the subagent reads, the main thread pays for the answer -----
distiller = Distiller()


def raw_execute(call):
    if call.name != "read_file":
        return f"unknown tool {call.name}"
    real = resolve(call.args["path"])
    if real is None:
        return "OUTSIDE SANDBOX: not reachable from this process"
    body = DISK.get(real, "not found")
    # layer 5: distil before it ever enters the context window
    return distiller.run(lambda: body, lambda b: b[:120])


# ---- layer 1: refuse before the tool runs ---------------------------------
RULES = [(
    "reads-need-a-path-inside-work",
    lambda c: c.name == "read_file" and not str(c.args.get("path", "")).startswith("work"),
    "this agent may only read under work/",
)]
execute = boundary(RULES)(raw_execute)


def next_call(observations):
    """The only provider-specific function in this file."""
    key = os.environ.get("OPENAI_API_KEY")
    messages = [{"role": "system", "content": "Read the Q3 report."},
                {"role": "user", "content": json.dumps(observations)}]
    if not key:
        print("  (no OPENAI_API_KEY: using a canned tool call)")
        print(f"  would POST {len(messages)} messages + {len(TOOLS)} tool schema")
        canned = ["work/report.md", "secrets/api_key", None]
        i = len(observations)
        return Call("read_file", {"path": canned[i]}) if i < 2 and canned[i] else None
    from openai import OpenAI                      # only imported when used
    r = OpenAI(api_key=key).chat.completions.create(
        model="gpt-4o-mini", messages=messages, tools=TOOLS)
    tc = r.choices[0].message.tool_calls
    if not tc:
        return None
    return Call(tc[0].function.name, json.loads(tc[0].function.arguments))


def main():
    observations, turns = [], 0
    while turns < 8:                               # the six lines, plus a cap
        call = next_call(observations)
        if call is None:
            break
        result = execute(call)
        observations.append(result)
        print(f"  read({call.args['path']!r}) -> {result}")
        turns += 1

    # layer 4: the reviewer gets a copy and cannot change anything
    snapshot = read_only(observations)
    snapshot.append("reviewer scribbled here")
    store.put("disk", "runs/last.json", json.dumps(observations))
    store.put("config", "agent_may_only_read_work", True)
    store.put("chat", None, "chatter that dies with the session")
    store.reset()

    print(f"\n  observations untouched by the reviewer: {len(observations)} entries")
    print(f"  main thread paid for {distiller.main_tokens} words, "
          f"subagent read {distiller.subagent_tokens}")
    print(f"  after reset -> chat {store.chat}, disk {list(store.disk)}, "
          f"config {list(store.config)}")


if __name__ == "__main__":
    main()
