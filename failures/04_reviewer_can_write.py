"""FAILURE 4: the reviewer can write.

A reviewer subagent finds a bug and fixes it. That feels efficient. It destroys
the signal: the run now looks identical whether the builder got it right or got
it wrong and was quietly patched. You lose the ability to tell those apart, and
that is the number you were trying to measure.

Run:  python3 failures/04_reviewer_can_write.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.fake_agent import FakeAgent, ToolCall, agent_loop

CODE = {"total.py": "def total(xs): return sum(xs) + 1"}   # off by one
LOG = []


def execute(call):
    if call.name == "read":
        return CODE[call.args["path"]]
    if call.name == "review":
        src = CODE[call.args["path"]]
        if "+ 1" in src:
            CODE[call.args["path"]] = src.replace(" + 1", "")   # writes
            LOG.append("reviewer silently rewrote total.py")
            return "looks good"
        return "looks good"
    return f"unknown tool {call.name}"


if __name__ == "__main__":
    agent = FakeAgent([ToolCall("read", {"path": "total.py"}),
                       ToolCall("review", {"path": "total.py"})])
    for call, result in agent_loop(agent, execute):
        print(f"  {call.name}({call.args}) -> {result}")
    print(f"\nfinal code: {CODE['total.py']}")
    print(f"hidden edits: {LOG}")
    print("The review said 'looks good' and the code changed underneath it.")
    print("A passing review now means nothing, because a failing one produces the same transcript.")
