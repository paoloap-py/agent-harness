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

    ("example         all five wrapped round a real loop",
     "examples/real_loop.py",
     ["DENIED by reads-need-a-path-inside-work",
      "observations untouched by the reviewer: 2 entries",
      "after reset -> chat []"],
     ["sk-live-DO-NOT-LEAK"]),
]


def test_module():
    """harness.py is the liftable version. Same guarantees, asserted here so a
    change to the demos cannot quietly diverge from the code people import."""
    import harness

    class C:
        def __init__(self, n, **a): self.name, self.args = n, a

    ex = harness.boundary([("no-delete",
                            lambda c: c.name == "delete_file" and not c.args.get("approved_by_human"),
                            "needs approval")])(lambda c: f"ran {c.name}")
    checks = [
        ("boundary denies",        ex(C("delete_file", path="x")).startswith("DENIED")),
        ("boundary allows flag",   ex(C("delete_file", path="x", approved_by_human=True)) == "ran delete_file"),
        ("allowlist admits",       harness.allowlist(["work"])("work/a.md") == "work/a.md"),
        ("allowlist refuses",      harness.allowlist(["work"])("secrets/k") is None),
        ("allowlist refuses ..",   harness.allowlist(["work"])("work/../secrets/k") is None),
    ]
    st = harness.Store()
    st.put("chat", None, "hi"); st.put("disk", "d.md", "pg"); st.put("config", "tx", True); st.reset()
    checks += [("store reset keeps disk+config", st.chat == [] and st.disk and st.config)]
    try:
        st.put("nope", "k", "v"); checks.append(("store refuses bad kind", False))
    except ValueError:
        checks.append(("store refuses bad kind", True))

    snap = harness.read_only({"a": 1}); snap["a"] = 99
    checks.append(("read_only is a copy", snap["a"] == 99))

    @harness.dry_run
    def apply_fix(path, new): return f"wrote {path}"
    checks += [("dry_run is default",  apply_fix("t.py", "x").startswith("DRY RUN")),
               ("dry_run off acts",    apply_fix("t.py", "x", dry_run=False) == "wrote t.py")]

    d = harness.Distiller()
    d.run(lambda: "lorem " * 5000, lambda x: "ANSWER: 42")
    checks.append(("distiller bills the main thread only for the answer",
                   d.main_tokens == 2 and d.subagent_tokens == 5000))

    rep = harness.boundary([("no-delete", lambda c: c.name == "delete_file", "needs approval")],
                           max_repeats=3)(lambda c: "ran")
    first3 = [rep(C("delete_file", path="x")) for _ in range(3)]
    fourth = rep(C("delete_file", path="x"))
    checks += [
        ("deny-loop quiet for max_repeats", all("attempt" not in r for r in first3)),
        ("deny-loop escalates after",       "Stop retrying" in fourth),
        ("deny-loop resets on a new call",  rep(C("read", path="ok.md")) == "ran"
                                            and "attempt" not in rep(C("delete_file", path="x"))),
    ]

    bad = 0
    for label, ok_ in checks:
        print(f"  {'ok  ' if ok_ else 'FAIL'}  module: {label}")
        bad += 0 if ok_ else 1
    return bad


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
    failed += test_module()
    total = len(CASES) + 14
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
