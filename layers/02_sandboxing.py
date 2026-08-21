"""LAYER 2: sandboxing.

Start from zero and add back what the job needs. An allowlist cannot be talked
around, because anything you did not name is already unreachable.

Run:  python3 layers/02_sandboxing.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.fake_agent import FakeAgent, ToolCall, agent_loop

DISK = {"work/notes.md": "fine", "secrets/api_key": "sk-live-DO-NOT-LEAK"}
ALLOW_ROOTS = ["work"]


def resolve(path):
    """Normalise FIRST, then check. Checking the raw string is the whole bug above."""
    real = os.path.normpath(path)
    if not any(real == r or real.startswith(r + os.sep) for r in ALLOW_ROOTS):
        return None
    return real


def execute(call):
    real = resolve(call.args["path"])
    if real is None:
        return "OUTSIDE SANDBOX: not reachable from this process"
    return DISK.get(real, "not found")


if __name__ == "__main__":
    agent = FakeAgent([ToolCall("read", {"path": "work/notes.md"}),
                       ToolCall("read", {"path": "secrets/api_key"}),
                       ToolCall("read", {"path": "work/../secrets/api_key"})])
    for call, result in agent_loop(agent, execute):
        print(f"  read({call.args['path']!r}) -> {result}")
    print("\nThe traversal resolves to the same place and is refused there.")
    print("In production this is the process boundary, not a function. The shape is identical.")
