"""FAILURE 5: no context pipeline.

The agent searches, and every result goes into the main thread verbatim. The
answers are fine. The bill is not, and this is the layer the 40x lives in.

Run:  python3 failures/05_no_context_pipeline.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.fake_agent import FakeAgent, ToolCall, agent_loop

CORPUS = {f"doc_{i}.md": ("lorem ipsum " * 400) + ("ANSWER: 42" if i == 7 else "")
          for i in range(12)}
context_tokens = 0


def execute(call):
    global context_tokens
    if call.name == "search":
        hits = {k: v for k, v in CORPUS.items()}          # everything, verbatim
        context_tokens += sum(len(v.split()) for v in hits.values())
        return f"{len(hits)} documents, full text"
    if call.name == "answer":
        return call.args["value"]
    return f"unknown tool {call.name}"


if __name__ == "__main__":
    agent = FakeAgent([ToolCall("search", {"q": "the answer"}),
                       ToolCall("answer", {"value": "42"})])
    for call, result in agent_loop(agent, execute):
        print(f"  {call.name}({call.args}) -> {result}")
    print(f"\ncontext consumed: ~{context_tokens:,} tokens")
    print("Correct answer. The main thread read the entire corpus to get it.")
