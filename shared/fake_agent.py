"""A scripted stand-in for a model, so every demo here runs with no API key.

The point of this repo is to show what an agent does WITHOUT each harness
layer. That only lands if you can run it. A real model would need a key, cost
money, and produce a different transcript every time, so the failures would be
anecdotes instead of demonstrations. This replays a fixed list of tool calls
instead: same input, same output, every time, on any machine.

It is deliberately dumb. The model is not the subject of this repo.
"""
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    name: str
    args: dict = field(default_factory=dict)


class FakeAgent:
    """Emits a fixed sequence of tool calls, the way a model would."""

    def __init__(self, script):
        self._script = list(script)
        self.turns = 0

    def next_call(self, _observations=None):
        """None means the agent considers itself finished."""
        if not self._script:
            return None
        self.turns += 1
        return self._script.pop(0)


def agent_loop(agent, execute, max_turns=25):
    """The whole loop. It really is about twenty lines.

    Everything anyone values sits in `execute`, which is the harness.
    """
    observations, transcript = [], []
    while agent.turns < max_turns:
        call = agent.next_call(observations)
        if call is None:
            break
        result = execute(call)
        observations.append(result)
        transcript.append((call, result))
    return transcript
