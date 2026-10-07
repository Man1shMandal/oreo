# Oreo handoff state

Updated 2026-10-07. Active checkout:
`/Users/manishmandal/oreo/.claude/worktrees/web-ui`, branch `worktree-web-ui`.
Base inspected: `39e7fbf`. Current task: remove hosted token quotas, restore the
original circular logo, and expose personal settings. Release verification pending.

## Changes

All authenticated users bypass the old reserve_chat/daily_usage quota path.
New conversations use a server-owned insert, existing conversation ownership is
checked before history/research, and atomic owned saves and leases remain.
No application max_tokens answer cap or 6,000-character message limit remains.
Provider limits and physical upload constraints still apply. No SQL migration.

Visible header Settings includes standing instructions, default model, brief/
balanced/thorough replies, creativity, efficient/balanced/extended recent context,
latest attachment reuse, web defaults and Enter behavior. Stored per account in
this browser, not across devices. Efficient context and ranked earlier-document
excerpts reduce repeated input without deleting saved history. A fewer-tokens
preset selects brief replies, efficient context and web off. New uploads are sent
in full. The shared SVG restores the original simple circular mark everywhere.

## Checks

44 Python mocked tests pass, covering quota-free new chats, ownership, settings
validation, custom instructions, provider creativity with no output cap, long
messages, attachments, research citations and streamed save failures. JavaScript
settings harness passes open/save/reset, efficient preset and account isolation.
Three JS syntax checks, Python compilation and git diff --check pass.

Earlier production verification covered real Haiku streaming, saved history and
web sources. Production file submission remains untested (mock upload tests pass).
Native Firefox preview was interrupted by concurrent user browser activity;
visual verification of the new settings dialog remains pending.

## Workspace

Preserve unrelated modified AGENTS.md and untracked GEMINI.md,
.github/copilot-instructions.md and .venv symlink. No secrets or private chat data
are recorded. Next: push and deploy, smoke-check public assets and update this
state with the verified release.
