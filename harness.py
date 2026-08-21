"""harness.py - the five layers as things you can use, not just read.

Drop this one file in, or `pip install agent-harness`. No dependencies.
Every function wraps or guards the `execute` your agent loop already calls.

    from harness import boundary, allowlist, host_allowlist, Store
    from harness import read_only, dry_run, Distiller, Denied

Python 3.8+. Sync and async loops both supported: boundary() detects a
coroutine function and returns a coroutine wrapper, because returning an
un-awaited coroutine is a guard that silently does nothing.
"""
from __future__ import annotations

import functools
import inspect
import os
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

__version__ = "0.1.0"
__all__ = ["boundary", "allowlist", "host_allowlist", "Store",
           "read_only", "dry_run", "Distiller", "Denied", "__version__"]

Rule = Tuple[str, Callable[[Any], bool], str]


class Denied(str):
    """A refusal you can branch on, count, and log.

    Subclasses `str` on purpose: it drops into the same slot a tool result
    goes, so existing loops keep working unchanged, while
    `isinstance(result, Denied)` gives you something better than matching
    text. `.rule` names which rule refused.
    """
    rule: str

    def __new__(cls, text: str, rule: str = "") -> "Denied":
        obj = super().__new__(cls, text)
        obj.rule = rule
        return obj


# ---------------------------------------------------------------- layer 1
def boundary(rules: Sequence[Rule], max_repeats: int = 3):
    """Refuse calls before they execute. `rules` is a sequence of
    (name, predicate, reason).

        NEEDS_APPROVAL = [("delete-needs-approval",
                           lambda c: c.name == "delete_file"
                                     and not c.args.get("approved_by_human"),
                           "deletion requires an explicit human approval flag")]
        execute = boundary(NEEDS_APPROVAL)(execute)

    SCOPE, and this is the part people get wrong: this guards the calls that
    pass through the `execute` you wrapped. Nothing else. An agent that reaches
    the same file through a shell tool, a subprocess, or a second client never
    touches this function. That is Layer 2's job, and it is why a check inside
    your own program is workflow control rather than a security boundary.

    Deny loudly: the agent is told which rule and why, so it can adapt instead
    of retrying blind. A denial it cannot act on becomes a retry loop, and a
    loop against a deterministic rule never terminates on its own. After
    `max_repeats` identical consecutive denials the message changes, which
    gives the loop something new and you a greppable marker.

    The returned wrapper carries `.denials`, a dict of rule name to count, so
    a refusal is visible to your metrics instead of only to the agent.
    """
    def wrap(execute: Callable) -> Callable:
        state: Dict[str, Any] = {"last": None, "n": 0}
        denials: Dict[str, int] = {}

        def check(call: Any) -> Optional[Denied]:
            for name, deny_if, reason in rules:
                if deny_if(call):
                    key = (name, getattr(call, "name", None),
                           repr(getattr(call, "args", None)))
                    state["n"] = state["n"] + 1 if key == state["last"] else 1
                    state["last"] = key
                    denials[name] = denials.get(name, 0) + 1
                    if state["n"] > max_repeats:
                        return Denied(
                            f"DENIED by {name}, and this is attempt {state['n']}. "
                            f"The rule will not change. Stop retrying and do "
                            f"something else.", name)
                    return Denied(f"DENIED by {name}: {reason}", name)
            state["last"], state["n"] = None, 0
            return None

        if inspect.iscoroutinefunction(execute):
            @functools.wraps(execute)
            async def guarded_async(call: Any) -> Any:
                refusal = check(call)
                return refusal if refusal is not None else await execute(call)
            guarded_async.denials = denials          # type: ignore[attr-defined]
            guarded_async.rules = list(rules)        # type: ignore[attr-defined]
            return guarded_async

        @functools.wraps(execute)
        def guarded(call: Any) -> Any:
            refusal = check(call)
            return refusal if refusal is not None else execute(call)
        guarded.denials = denials                    # type: ignore[attr-defined]
        guarded.rules = list(rules)                  # type: ignore[attr-defined]
        return guarded
    return wrap


# ---------------------------------------------------------------- layer 2
def allowlist(roots: Iterable[str]) -> Callable[[str], Optional[str]]:
    """Resolve a path to its real location, then check it. Returns the
    normalised path, or None if it lands outside `roots`.

    The order is the layer: normalising AFTER the check is how
    `work/../secrets/api_key` walks past a rule that names `secrets/`.

    This is a guard, not a sandbox. A sandbox is the process boundary. Use
    both: this catches your own bugs, the process boundary catches everything
    that never went through your code.
    """
    real_roots = [os.path.normpath(r) for r in roots]

    def resolve(path: str) -> Optional[str]:
        real = os.path.normpath(path)
        if any(real == r or real.startswith(r + os.sep) for r in real_roots):
            return real
        return None
    return resolve


def host_allowlist(hosts: Iterable[str]) -> Callable[[str], Optional[str]]:
    """The network half of Layer 2. Returns the hostname, or None if the URL
    points anywhere you did not name.

    Matches the host exactly or as a subdomain, and compares the parsed host
    rather than the string, because `https://evil.com/?x=api.openai.com` and
    `https://api.openai.com.evil.com` both pass a naive substring check.
    """
    from urllib.parse import urlparse
    allowed = [h.lower().lstrip(".") for h in hosts]

    def check(url: str) -> Optional[str]:
        host = (urlparse(url).hostname or "").lower()
        if any(host == a or host.endswith("." + a) for a in allowed):
            return host
        return None
    return check


# ---------------------------------------------------------------- layer 3
class Store:
    """Three destinations, and you cannot write without naming one.

        s = Store()
        s.put("chat", None, "user said hi")          # dies with the session
        s.put("disk", "decisions/db.md", "postgres") # survives a reset
        s.put("config", "always_migrate_in_tx", True)# shapes every session
        s.reset()                                    # only chat is cleared
    """
    KINDS = ("chat", "disk", "config")

    def __init__(self) -> None:
        self.chat: List[Any] = []
        self.disk: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}

    def put(self, kind: str, key: Optional[str], value: Any) -> None:
        if kind not in self.KINDS:
            raise ValueError(f"kind must be one of {self.KINDS}, got {kind!r}")
        if kind == "chat":
            self.chat.append(value)
        else:
            getattr(self, kind)[key] = value

    def reset(self) -> None:
        """What a context reset actually does. Everything else is untouched."""
        self.chat.clear()


# ---------------------------------------------------------------- layer 4
def read_only(view):
    """Hand a reviewer a copy so its verdict stays a verdict.

    A reviewer that can write turns a failing review and a passing one into the
    same transcript, which is the signal you were trying to buy.
    """
    return dict(view) if isinstance(view, dict) else list(view)


def dry_run(fn: Callable) -> Callable:
    """Make the safe path the default for anything irreversible.

        @dry_run
        def apply_fix(path, new): ...
        apply_fix("total.py", "...")                  # describes
        apply_fix("total.py", "...", dry_run=False)   # acts
    """
    @functools.wraps(fn)
    def guarded(*args: Any, **kwargs: Any) -> Any:
        if kwargs.pop("dry_run", True):
            return f"DRY RUN: would call {fn.__name__}{args}, nothing written"
        return fn(*args, **kwargs)
    return guarded


# ---------------------------------------------------------------- layer 5
class Distiller:
    """Delegate the reading, return the answer, and count both.

        d = Distiller()
        answer = d.run(lambda: search_everything(q), lambda r: r[:400])
        d.main_tokens, d.subagent_tokens
    """
    def __init__(self) -> None:
        self.main_tokens = 0
        self.subagent_tokens = 0

    def run(self, explore: Callable[[], Any], distill: Callable[[Any], Any]) -> Any:
        """Counts WORDS, not tokens. It is a ratio you can trust and an absolute
        you cannot: swap in your provider's tokenizer before you quote a bill."""
        raw = explore()
        self.subagent_tokens += len(str(raw).split())
        out = distill(raw)
        self.main_tokens += len(str(out).split())
        return out
