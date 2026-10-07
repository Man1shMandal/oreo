# Oreo handoff state

Updated 2026-10-07. Active checkout: `/Users/manishmandal/oreo/.claude/worktrees/web-ui`,
branch `worktree-web-ui`, synced to `origin/main` at `d74a368`.

## Live release

- Production site: https://oreo.manish.engineer
- Current Vercel deployment: `dpl_ApcSU59guKKtdCy222SL7uT2R9iL`, READY and aliased to the custom domain.
- Supabase project: `ahgbdtbmmwisqhulutgy`; Google sign-in and the redirect allowlist for the custom domain are configured.
- Domain CNAME resolves to `d3380b04008a43cd.vercel-dns-017.com`.
- Supabase migration `202610070003_chat_budget.sql` was applied by the user. User ran `supabase/tests/hosted_v1.sql`; it returned “Hosted V1 quota, persistence, permissions and isolation checks passed.”
- Live `/api/health` returns 200. `/api/admin` returns 404. Unauthenticated account endpoints reject requests with 401/no-store.

## Current product behavior

Google sign-in gives any account immediate chat access. Manual approval, admin account management, and pending-account UI/API routes were removed in `d32d405`. Saved conversations, account history isolation, estimated daily usage limits, request leases, and server-only writes remain. The old database `profiles.approved` field and SQL checks remain for compatibility; the server automatically sets that legacy flag for an authenticated account before using the existing quota/lease RPCs. It no longer controls access. No new migration is required.

Verification for `d32d405`: 27 mocked Python tests passed, including a formerly pending user completing chat and removed admin routes returning 404. Python compilation, UI syntax/mock flow, and `git diff --check` passed. Production smoke checks confirmed health, the updated homepage, and `/api/admin` 404. Authenticated Google sign-in and a real provider reply were not exercised in the browser.

## Next step

User should refresh https://oreo.manish.engineer, sign in with Google, and send a chat. If a defect is reported, reproduce against this release and fix from this worktree. No deployment or database work is currently pending.

## Workspace notes

Preserve existing unrelated local work: modified `AGENTS.md`; untracked `.github/copilot-instructions.md`, `GEMINI.md`, and `.venv` symlink. Do not stage these as part of an Oreo product change. The portfolio repo `/Users/manishmandal/Manish.engineer` was separately updated and deployed: its “Try Oreo” link targets this hosted site.

## 2026-10-07 — Workspace review

Inspected HEAD `072a8e6` on `worktree-web-ui`; local tracking ref matches HEAD.
The release details above are prior recorded checks, not reverified live in this review.
Preserved all existing changes. There is also uncommitted product work in
`api/chat.py`, `api/config.py`, `api/conversations.py`, and `public/index.html`:
sidebar chat UI, model selection, uploads, and optional web research. Its deployment
status is unverified. Thus the earlier no-pending-work statement applies to the
recorded release, not these local changes.

Checks: all 27 mocked Python tests passed; extracted UI module passed
`node --check`; `git diff --check` passed. Existing tests do not establish
correctness of the new upload/research/browser flows. Review found research
reads conversation messages with the service credential before prepare checks
ownership, and calls its planner before reserving quota. Model default is a
short alias while select option values are model IDs. Conversation switching
no longer sets the loading guard, and pending attachments are not cleared on
account changes. These need review and correction before releasing this work.
Next step: address those gaps and test the new feature flows; authenticated
live chat remains unverified by this review. No product files edited or deployed.

## 2026-10-07 — Hosted experience rebuilt

Rebuilt the hosted UI around the local app's capabilities: responsive sidebar and
mobile drawer, anchored composer, streamed replies, safe formatted markdown,
code copying, model selection, attachments/paste/drop, and web citations.
Added `api/messages.py` for backward-compatible versioned saved turns retaining
document text, image PDF parts, small previews, original names, and citations.
File follow-ups survive reopening a conversation. No SQL migration is required.
Browser photos resize automatically; five files / 2.2 MB combined and 48,000
extracted document characters are the current limits. Answer cap is 2,048 tokens.

Fixed ownership-before-research, quota-before-planner, model default ID, loading
and sending guards, account-change draft clearing, and attachment recovery on
failed requests. Public research URLs are checked on redirects. SDK automatic
retries are disabled so calls cannot repeat outside the reserved budget.

Checks so far: 41 mocked Python tests passed; Python compilation, both JS syntax
checks, and diff whitespace checks passed. Firefox fake-auth/model preview
verified desktop streaming, code/list/table formatting, citations, new chat,
reopened saved citations, and mobile layout at 375 x 667. The preview is isolated
from real accounts, conversations and model credentials. Production provider and
Google sign-in checks are still pending. Existing unrelated agent instructions
and symlink remain unstaged. Vercel project identity has been verified as `oreo`.
Next step: publish and verify the rebuilt app on the existing domain.
