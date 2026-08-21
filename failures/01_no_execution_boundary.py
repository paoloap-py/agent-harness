"""FAILURE 1: no execution boundary.

The rule "always ask before deleting anything" lives in the system prompt. The
agent has it, acknowledges it, and deletes anyway on turn 3, because a rule in
a prompt is a bet that the model applies it under pressure.

Run:  python3 failures/01_no_execution_boundary.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.fake_agent import FakeAgent, ToolCall, agent_loop

SYSTEM_PROMPT = "IMPORTANT: never delete a file without asking the user first."

FILES = {"notes.md": "keep", "cache.tmp": "junk", "draft.md": "keep"}


def execute(call):
    """No boundary. Whatever the agent asks for, the tool does."""
    if call.name == "list_files":
        return sorted(FILES)
    if call.name == "delete_file":
        FILES.pop(call.args["path"], None)
        return f"deleted {call.args['path']}"
    return f"unknown tool {call.name}"


if __name__ == "__main__":
    agent = FakeAgent([
        ToolCall("list_files"),
        ToolCall("delete_file", {"path": "cache.tmp"}),
        ToolCall("delete_file", {"path": "draft.md"}),   # not junk. not asked.
    ])
    print(f"system prompt: {SYSTEM_PROMPT!r}\n")
    for call, result in agent_loop(agent, execute):
        print(f"  {call.name}({call.args}) -> {result}")
    print(f"\nfiles remaining: {sorted(FILES)}")
    print("draft.md is gone. The agent never asked. The rule was in the prompt the whole time.")
