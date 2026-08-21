"""harness.py - the five layers as things you can use, not just read.

Drop this one file into your project. No dependencies, no framework, no install.
Every function wraps or guards the `execute` your agent loop already calls.

    from harness import boundary, allowlist, Store, read_only, dry_run, Distiller

The demos under failures/ and layers/ show each layer failing and holding.
This is the same code with the teaching scaffolding removed.
"""
import os
import functools

__all__ = ["boundary", "allowlist", "Store", "read_only", "dry_run", "Distiller"]


# ---------------------------------------------------------------- layer 1
def boundary(rules, max_repeats=3):
    """Refuse calls before they execute. `rules` is a list of
    (name, predicate, reason). Deny LOUDLY: the agent is told why, so it can
    adapt instead of retrying blind, and you can see the refusal in the log.

        NEEDS_APPROVAL = [("delete-needs-approval",
                           lambda c: c.name == "delete_file"
                                     and not c.args.get("approved_by_human"),
                           "deletion requires an explicit human approval flag")]
        execute = boundary(NEEDS_APPROVAL)(execute)

    A denial the agent cannot act on becomes a retry loop, and a retry loop
    against a deterministic rule never terminates on its own: same call, same
    refusal, forever, at full token price. After `max_repeats` identical
    consecutive denials this stops explaining and says so, which gives the loop
    something new to react to and gives you a greppable marker.
    """
    def wrap(execute):
        state = {"last": None, "n": 0}

        @functools.wraps(execute)
        def guarded(call):
            for name, deny_if, reason in rules:
                if deny_if(call):
                    key = (name, getattr(call, "name", None), repr(getattr(call, "args", None)))
                    state["n"] = state["n"] + 1 if key == state["last"] else 1
                    state["last"] = key
                    if state["n"] > max_repeats:
                        return (f"DENIED by {name}, and this is attempt "
                                f"{state['n']}. The rule will not change. Stop "
                                f"retrying and do something else.")
                    return f"DENIED by {name}: {reason}"
            state["last"], state["n"] = None, 0
            return execute(call)
        return guarded
    return wrap


# ---------------------------------------------------------------- layer 2
def allowlist(roots):
    """Resolve a path to its real location, then check it. Returns the
    normalised path, or None if it lands outside `roots`.

    The order is the layer: normalising AFTER the check is how
    `work/../secrets/api_key` walks past a rule that names `secrets/`.

    This is a guard, not a sandbox. A sandbox is the process boundary. Use
    both: this catches your own bugs, the process boundary catches everything
    that never went through your code.
    """
    roots = [os.path.normpath(r) for r in roots]

    def resolve(path):
        real = os.path.normpath(path)
        if any(real == r or real.startswith(r + os.sep) for r in roots):
            return real
        return None
    return resolve


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

    def __init__(self):
        self.chat, self.disk, self.config = [], {}, {}

    def put(self, kind, key, value):
        if kind not in self.KINDS:
            raise ValueError(f"kind must be one of {self.KINDS}, got {kind!r}")
        if kind == "chat":
            self.chat.append(value)
        else:
            getattr(self, kind)[key] = value

    def reset(self):
        """What a context reset actually does. Everything else is untouched."""
        self.chat.clear()


# ---------------------------------------------------------------- layer 4
def read_only(view):
    """Hand a reviewer a copy so its verdict stays a verdict.

    A reviewer that can write turns a failing review and a passing one into the
    same transcript, which is the signal you were trying to buy.
    """
    return dict(view) if isinstance(view, dict) else list(view)


def dry_run(fn):
    """Make the safe path the default for anything irreversible.

    The wrapped call describes itself unless dry_run=False is passed on
    purpose, so forgetting the flag costs nothing.

        @dry_run
        def apply_fix(path, new): ...
        apply_fix("total.py", "...")                  # describes
        apply_fix("total.py", "...", dry_run=False)   # acts
    """
    @functools.wraps(fn)
    def guarded(*args, **kwargs):
        if kwargs.pop("dry_run", True):
            return f"DRY RUN: would call {fn.__name__}{args}, nothing written"
        return fn(*args, **kwargs)
    return guarded


# ---------------------------------------------------------------- layer 5
class Distiller:
    """Delegate the reading, return the answer, and count both.

    The subagent burns its own window. The main thread pays only for what
    comes back, on this turn and on every turn after it.

        d = Distiller()
        answer = d.run(lambda: search_everything(query), lambda r: r[:400])
        d.main_tokens, d.subagent_tokens
    """
    def __init__(self):
        self.main_tokens = 0
        self.subagent_tokens = 0

    def run(self, explore, distill):
        """Counts WORDS, not tokens. It is a ratio you can trust and an absolute
        you cannot: swap in your provider's tokenizer before you quote a bill."""
        raw = explore()
        self.subagent_tokens += len(str(raw).split())
        out = distill(raw)
        self.main_tokens += len(str(out).split())
        return out
