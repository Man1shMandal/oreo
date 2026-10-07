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
