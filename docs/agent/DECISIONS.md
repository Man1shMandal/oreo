# Decisions

## 2026-10-07 — Sign-in grants hosted chat access
The user removed the manual approval model. Every verified signed-in account can
chat immediately, subject to the existing daily budget. There is no admin account
listing or approval endpoint/UI. The server automatically enables the legacy
database flag because deployed quota/lease functions still reference it; it no
longer controls eligibility. This keeps the existing database compatible without
requiring another manual migration. Ownership and server-only writes remain.

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

## 2026-10-07 — Restore local chat capabilities in the hosted app
Use the local UI's safe markdown renderer and shared attachment/research modules.
The hosted UI stays buildless, with separate JavaScript modules for chat state
and markdown. Stream answers, keep the composer anchored, and use a mobile chat
drawer. Preserve Google sign-in and server-owned budgets and history.

## 2026-10-07 — Persist bounded attachments in versioned message content
The existing owned message rows hold a versioned envelope for document text,
gateway-compatible image PDF parts, small previews, file names, and citations.
Plain-text rows remain compatible. This avoids requiring a manual migration for
this release and enables reopened file follow-ups. Combined uploads are limited
to 2.2 MB, extracted text to 48,000 characters, and recent context remains bounded.
This is appropriate for the current small-file interface; move larger files to
private object storage if the limits expand.

## 2026-10-07 — Reserve research costs before using any model
Prepare checks conversation ownership and reserves quota before research sees
history or calls the planner. Reserve 4,000 extra estimated tokens for bounded
research and a 2,048-token answer cap. Disable automatic SDK retries to avoid
unreserved repeated provider requests. Search failures must be visible to users.
Validate public URLs again on redirects as well as on the first fetch.

## 2026-10-07 — Keep usage quiet and branding consistent
Show the account allowance as a small ring, with exact numbers and reset time in
its tooltip and accessible label. Use one canonical `oreo/logo.svg` asset across
the hosted sign-in, sidebar, mobile header, browser favicon, and local browser UI.

## 2026-10-07 — Unlimited hosted access and visible personal settings
Supersedes earlier quota/ring and answer-cap decisions. The user requested no
application token limits for any account. Create owned conversations directly,
retain owned save/lease functions, and bypass reserve_chat and daily_usage.
Remove the answer max_tokens field; provider limits remain outside Oreo's control.
Keep legacy SQL for compatibility rather than requiring a destructive migration.

Settings are per-account browser preferences: standing instructions, model,
style, creativity, context depth, file reuse, web defaults, and Enter behavior.
Use compact recent history and ranked document excerpts to reduce input tokens;
do not enforce a quota or truncate answers to make usage small. Preferences do
not sync across devices. Restore the original simple circular Oreo mark in the
shared SVG; avoid a new cookie illustration.

## 2026-10-08 — Preserve turns without an extra model call
Context selection must never discard the entire conversation because the latest
answer exceeds the text budget. Keep recent question/answer pairs, explicitly
shorten oversized messages, and reserve space for older relevant excerpts from
a bounded retrieval window. Keep their original roles; do not promote user text
to system instructions. Locate reusable attachments independently. This improves
continuity without adding a summarization call to response latency. Ownership
checks, per-account leases and atomic saves remain required.

## 2026-10-08 — Fast default for hosted chat
New hosted browser sessions default to Haiku for lower response latency. Keep
Sonnet and the other models in the picker so users can choose more capability
for harder requests. Reuse the provider client across warm function calls to
reuse its outbound connection pool; cache by API key so credential rotation does
not keep using a stale client.
