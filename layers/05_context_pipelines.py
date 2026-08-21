"""LAYER 5: context pipelines.

A subagent gets its own window, reads everything, and returns a distillation.
The main thread never sees the corpus. Same answer, and the number that changes
is the one on the invoice.

Run:  python3 layers/05_context_pipelines.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.fake_agent import FakeAgent, ToolCall, agent_loop

CORPUS = {f"doc_{i}.md": ("lorem ipsum " * 400) + ("ANSWER: 42" if i == 7 else "")
          for i in range(12)}
main_tokens = 0
subagent_tokens = 0


def subagent_search(query):
    """Its own context window. Burns tokens the main thread never pays twice for."""
    global subagent_tokens
    subagent_tokens += sum(len(v.split()) for v in CORPUS.values())
    for name, body in CORPUS.items():
        if "ANSWER:" in body:
            return f"{name}: {body.split('ANSWER:')[1].strip()}"
    return "no answer found"


def execute(call):
    global main_tokens
    if call.name == "search":
        distilled = subagent_search(call.args["q"])
        main_tokens += len(distilled.split())
        return distilled
    if call.name == "answer":
        return call.args["value"]
    return f"unknown tool {call.name}"


if __name__ == "__main__":
    agent = FakeAgent([ToolCall("search", {"q": "the answer"}),
                       ToolCall("answer", {"value": "42"})])
    for call, result in agent_loop(agent, execute):
        print(f"  {call.name}({call.args}) -> {result}")
    print(f"\nmain thread context: ~{main_tokens:,} tokens")
    print(f"subagent context:    ~{subagent_tokens:,} tokens (its own window, discarded after)")
    print("Same answer. The expensive reading happened somewhere the main thread never has to carry.")
