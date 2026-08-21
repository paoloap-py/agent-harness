#!/usr/bin/env python3
"""Every claim this repo makes, asserted against what the scripts actually print.

Both directions per layer. The failure script must still demonstrate the failure,
and the layer script must still prevent it. A test that only checked the fix would
pass forever after the demo quietly stopped demonstrating anything.

Run:  python3 test_harness.py
"""
import subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).parent


def run(script):
    r = subprocess.run([sys.executable, str(ROOT / script)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"{script} exited {r.returncode}\n{r.stderr}"
    return r.stdout


# (label, script, substrings that MUST appear, substrings that MUST NOT)
CASES = [
    ("1 no boundary   deletes the client file",
     "failures/01_no_execution_boundary.py",
     ["deleted client-deliverable.md"], ["DENIED"]),
    ("1 boundary      refuses the delete",
     "layers/01_execution_boundary.py",
     ["DENIED by delete-needs-approval", "'client-deliverable.md'"], ["deleted client-deliverable.md"]),

    ("2 no sandbox    leaks the key through ../",
     "failures/02_no_sandbox.py",
     ["sk-live-DO-NOT-LEAK"], ["OUTSIDE SANDBOX"]),
    ("2 sandbox       refuses the traversal",
     "layers/02_sandboxing.py",
     ["OUTSIDE SANDBOX"], ["sk-live-DO-NOT-LEAK"]),

    ("3 no persistence  loses the decision",
     "failures/03_no_persistence.py",
     ["after reset:  []", "sqlite"], []),
    ("3 persistence     keeps disk and config",
     "layers/03_memory_persistence.py",
     ["conversation: []", "decisions/db.md", "always_run_migrations_in_a_transaction"], []),

    ("4 reviewer writes  silently patches the bug",
     "failures/04_reviewer_can_write.py",
     ["reviewer silently rewrote", "return sum(xs)"], []),
    ("4 read-only        reports and cannot touch",
     "layers/04_verification_loops.py",
     ["VERDICT: off-by-one", "DRY RUN", "return sum(xs) + 1"], ["wrote total.py"]),

    ("5 no pipeline    main thread reads the corpus",
     "failures/05_no_context_pipeline.py",
     ["9,602 tokens"], []),
    ("5 pipeline       main thread reads 2",
     "layers/05_context_pipelines.py",
     ["main thread context: ~2 tokens", "9,602 tokens"], []),
]


def main():
    failed = 0
    for label, script, must, must_not in CASES:
        out = run(script)
        problems = [f"missing {s!r}" for s in must if s not in out]
        problems += [f"unexpectedly present {s!r}" for s in must_not if s in out]
        if problems:
            failed += 1
            print(f"  FAIL  {label}")
            for p in problems:
                print(f"          {p}")
        else:
            print(f"  ok    {label}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
