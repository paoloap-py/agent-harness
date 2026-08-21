"""LAYER 3: memory persistence.

Decide, per artifact, which of three places it belongs in. Most teams never
make the call, which is why their agents feel amnesiac about the things that
mattered and stubborn about the things that did not.

Run:  python3 layers/03_memory_persistence.py
"""
CONVERSATION, DISK, HARNESS_CONFIG = [], {}, {}


def remember(kind, key, value):
    """kind: 'chat' dies with the session, 'disk' survives it,
    'config' shapes every session that follows."""
    {"chat": lambda: CONVERSATION.append(value),
     "disk": lambda: DISK.__setitem__(key, value),
     "config": lambda: HARNESS_CONFIG.__setitem__(key, value)}[kind]()


if __name__ == "__main__":
    remember("chat", None, "user said hi")
    remember("disk", "decisions/db.md", "postgres: we need concurrent writers")
    remember("config", "always_run_migrations_in_a_transaction", True)

    CONVERSATION.clear()          # same reset as the failure case

    print(f"conversation: {CONVERSATION}")
    print(f"disk:         {DISK}")
    print(f"config:       {HARNESS_CONFIG}")
    print("\nThe chatter is gone. The decision and the rule are not.")
    print("Restart conversations freely once this split is deliberate.")
