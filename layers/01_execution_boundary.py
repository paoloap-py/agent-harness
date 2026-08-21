"""LAYER 1: the execution boundary.

Same agent, same script, same prompt. The difference is that the rule now
lives in code that runs before the tool does, so following it is not a
decision the model gets to make.

This is the generalised form of a real hook: a PreToolUse gate that denies
`propose_fix.py apply` when the human has not answered since the proposal.
That rule sat in a skill file as prose for two weeks and was violated eleven
times in one session. As a gate it has never been violated, because it cannot be.

Run:  python3 layers/01_execution_boundary.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.fake_agent import FakeAgent, ToolCall, agent_loop

FILES = {"notes.md": "keep", "cache.tmp": "junk", "client-deliverable.md": "the thing you are paid for"}


class Denied(Exception):
    pass


def boundary(rules):
    """Wrap a tool executor so every call passes the rules first.

    A rule is (name, predicate, reason). The predicate sees the call and
    returns True to DENY. Deny is the loud path on purpose: a boundary that
    silently drops a call teaches the agent nothing and hides the failure.
    """
    def wrap(execute):
        def guarded(call):
            for name, deny_if, reason in rules:
                if deny_if(call):
                    return f"DENIED by {name}: {reason}"
            return execute(call)
        return guarded
    return wrap


def execute(call):
    if call.name == "list_files":
        return sorted(FILES)
    if call.name == "delete_file":
        FILES.pop(call.args["path"], None)
        return f"deleted {call.args['path']}"
    return f"unknown tool {call.name}"


NEEDS_APPROVAL = [(
    "delete-needs-approval",
    lambda c: c.name == "delete_file" and not c.args.get("approved_by_human"),
    "deletion requires an explicit human approval flag on the call",
)]

if __name__ == "__main__":
    agent = FakeAgent([
        ToolCall("list_files"),
        ToolCall("delete_file", {"path": "cache.tmp"}),
        ToolCall("delete_file", {"path": "client-deliverable.md"}),
    ])
    guarded = boundary(NEEDS_APPROVAL)(execute)
    for call, result in agent_loop(agent, guarded):
        print(f"  {call.name}({call.args}) -> {result}")
    print(f"\nfiles remaining: {sorted(FILES)}")
    print("Nothing was deleted. The prompt did not change. The enforcement moved.")
