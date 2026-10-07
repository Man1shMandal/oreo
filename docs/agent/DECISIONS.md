# Decisions

## 2026-10-07 — Reserve a daily estimated chat budget on the server
The ABB gateway omits actual usage. Hosted requests charge an estimate for
the complete prompt and reserve the full 700-token response cap before a
provider call. Failed calls keep their reservation. This bounds the app's
estimated daily budget under concurrent requests, but does not claim exact
model usage or billing. Reset at midnight UTC and describe it as estimated.
Only the server writes hosted messages and usage; browsers read their own
data. Migration 003 must precede deployment of code calling its functions.

## 2026-10-07 — Keep creator attribution out of the app
The user requested no "by Manish" copy. The creator's name may appear only
on the homepage, if needed, and must not appear as branding in other screens
or assistant instructions. The hosted homepage now uses "A small personal AI."

## 2026-10-07 — Store agent context in the repository
Use AGENTS.md for shared working instructions, STATE.md for current work and
DECISIONS.md for enduring reasons. Provider-specific instruction files point here.
This makes context readable by any AI and portable with a clone. Agents must keep
it current; files do not automatically capture conversations or private AI memory.

## 2026-10-07 — Register the active worktree
The local `oreo` project entry points to `.claude/worktrees/web-ui`, since that is
where the hosted and local browser code currently lives. Treat this as a local path,
not a requirement to reproduce Claude's directory layout on another machine.

## Existing design constraints
Keep the app lean and modular, keep UI controls minimal, and preserve token-saving
behavior. Local terminal/web data and secrets stay local; hosted authentication and
data use Supabase and server-side environment variables. These constraints were
already documented in AGENTS.md; inspect implementation before assuming completion.
