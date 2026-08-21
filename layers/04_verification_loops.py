"""LAYER 4: verification loops.

Two rules. The reviewer is read-only, so its verdict stays a verdict. And any
irreversible tool defaults to describing what it would do, so forgetting the
flag is harmless.

Run:  python3 layers/04_verification_loops.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.fake_agent import FakeAgent, ToolCall, agent_loop

CODE = {"total.py": "def total(xs): return sum(xs) + 1"}


def read_only(view):
    """Hand the reviewer a copy. It cannot reach the original."""
    return dict(view)


def execute(call):
    if call.name == "read":
        return CODE[call.args["path"]]
    if call.name == "review":
        snapshot = read_only(CODE)
        src = snapshot[call.args["path"]]
        verdict = "off-by-one: sum(xs) + 1" if "+ 1" in src else "looks good"
        return f"VERDICT: {verdict}"
    if call.name == "apply_fix":
        # irreversible, so dry_run is the default and must be turned off on purpose
        if call.args.get("dry_run", True):
            return f"DRY RUN: would rewrite {call.args['path']}, nothing written"
        CODE[call.args["path"]] = call.args["new"]
        return f"wrote {call.args['path']}"
    return f"unknown tool {call.name}"


if __name__ == "__main__":
    agent = FakeAgent([
        ToolCall("read", {"path": "total.py"}),
        ToolCall("review", {"path": "total.py"}),
        ToolCall("apply_fix", {"path": "total.py", "new": "def total(xs): return sum(xs)"}),
    ])
    for call, result in agent_loop(agent, execute):
        print(f"  {call.name}({call.args}) -> {result}")
    print(f"\nfinal code: {CODE['total.py']}")
    print("The reviewer reported the bug and could not touch it.")
    print("The fix was described, not applied, because nobody passed dry_run=False.")
