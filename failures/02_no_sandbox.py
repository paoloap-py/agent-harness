"""FAILURE 2: a deny rule instead of a sandbox.

The harness denies reads of `secrets/`. The agent asks for a path that does not
look like `secrets/` and gets the file anyway, because a deny list enumerates
the ways in it thought of.

Run:  python3 failures/02_no_sandbox.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.fake_agent import FakeAgent, ToolCall, agent_loop

DISK = {"work/notes.md": "fine", "secrets/api_key": "sk-live-DO-NOT-LEAK"}
DENY = ["secrets/"]


def execute(call):
    path = call.args["path"]
    if any(path.startswith(d) for d in DENY):          # blocks the spelling, not the file
        return "DENIED by deny-list"
    real = os.path.normpath(path)                       # ../ collapses here
    return DISK.get(real, "not found")


if __name__ == "__main__":
    agent = FakeAgent([ToolCall("read", {"path": "secrets/api_key"}),
                       ToolCall("read", {"path": "work/../secrets/api_key"})])
    for call, result in agent_loop(agent, execute):
        print(f"  read({call.args['path']!r}) -> {result}")
    print("\nThe deny rule blocked one spelling of the path and shipped the key on the next line.")
    print("A deny list is workflow control. It is not a security boundary.")
