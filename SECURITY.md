# Security

## What this is not

`harness.py` is workflow control, not a security boundary. Everything in it runs
inside your own process, which means it only sees the calls that pass through
the `execute` you wrapped.

An agent that reaches the same file through a shell tool, a subprocess, a second
client, or a library that opens files directly never touches these guards. That
is not a bug in this code, it is the reason Layer 2 exists: if prompt injection
is in your threat model, the limit that holds is the one the operating system
puts on the process. Start it with access to nothing and add back what the job
needs.

Use `allowlist()` and `host_allowlist()` to catch your own mistakes. Use a
container, a restricted user, or a seccomp profile to catch everything else.

## Reporting

Open an issue. This is example code with no network access, no credentials, and
no dependencies, so the realistic surface is a guard that fails to refuse
something it should. Include the call that got through and the rules you had.
