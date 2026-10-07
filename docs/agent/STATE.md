# Oreo current state

## Production promotion — 2026-10-07

User applied migration 003 and reported the exact success result from
`supabase/tests/hosted_v1.sql`. User also saved the domain redirect allowlist and
Name.com CNAME. DNS independently resolves to the required Vercel target.
Promoted prepared production deployment `dpl_CJgMFUH6pWxSrUEKtgP7T8xBbcgL`.
`https://oreo.manish.engineer` resolves to that READY release and serves valid HTTPS.
Live health/config return 200; profile/conversations/admin return unauthenticated
401 with no-store and nosniff headers. Homepage contains the saved-history UI and
no creator attribution. Source remains the previously tested `d7ed931` product code.
Main was confirmed an ancestor of this release before its fast-forward push.
Authenticated Google login, real reply, history reload and admin controls on the
custom domain still require a signed-in browser check. Browser automation remains
unreliable. Supabase Site URL may still be the original URL; custom-domain redirect
was explicitly added by the user. Next: verify the signed-in flow on the domain.

## Release access retry — 2026-10-07

Backend and verification agents rechecked the unchanged release: staged health
and unauthenticated access checks pass; the established public release is healthy.
The Oreo DNS record is still absent. No source change or new deployment was needed.
Browser inventory exposes no connected browser surfaces; native Firefox actions
still fail with `noWindowsAvailable` and inconsistent observations. No supported
authenticated Supabase SQL or Name.com DNS alternative is configured. Requested
restored browser access and existing service sign-ins, not renewed deployment
approval. Migration, DNS, OAuth domain configuration and final promotion remain
pending. Follow the next steps in the checkpoint below when access is restored.

## Parallel release checkpoint — 2026-10-07

Final prepared code commit: `d7ed931`, pushed to `release/hosted-v1` (not main).
Final staged release: `dpl_CJgMFUH6pWxSrUEKtgP7T8xBbcgL`, READY at
https://oreo-f23tmvvhq-man1shmandals-projects.vercel.app, with final no-store headers.
The canonical Oreo Vercel alias serves this staged build. The established
`web-ui-eta-nine.vercel.app` alias remains on the prior working public release.

The user authorized completion, domain connection, deployment and sub-agents.
Backend, frontend and verification agents completed their parts. This checkpoint
supersedes conflicting deployment assumptions in the earlier snapshots below.

- Active checkout remains `worktree-web-ui`; existing local handoff files and
  concurrent product changes were preserved and reviewed together.
- Implemented saved conversations, bounded recent context, server-only history
  writes, atomic daily estimated budgets, per-user request leases, account usage,
  pending-account status and in-app administrator approvals/limit changes.
- Admin authorization uses a server-side configured email matched to the verified
  Supabase identity. `ADMIN_EMAIL` was successfully added in production; no private
  value is recorded here. Private API responses use `Cache-Control: no-store`.
- 29 mocked Python tests passed. Compilation, JavaScript syntax, mocked UI flow
  (pending/approved/history/reply/sign-out) and whitespace checks passed.
- Confirmed Vercel project is `oreo`, ID `prj_kQdBCNFycMEAPvnlwLdrYNZ4EuIU`, team
  `team_4KzuaUP2i2NQOxlj4ObVRRsJ`. Inspection of project name `web-ui` returns not
  found; the old local metadata name was stale and has been corrected.
- Staged production build `dpl_3qLHP3jSbSvU4DtC8ae76MNrBPu9` is READY at
  https://oreo-pb8usl89k-man1shmandals-projects.vercel.app. Its page/config/health
  passed live HTTPS checks; profile/history/admin reject unauthenticated requests.
  This build predates the final no-store header change. The working public alias
  https://web-ui-eta-nine.vercel.app still serves the previous verified release.
- Attached `oreo.manish.engineer` to the verified Oreo project. Authoritative DNS
  is Name.com; no Oreo record exists yet. Vercel requires CNAME host `oreo` to
  `d3380b04008a43cd.vercel-dns-017.com`. DNS/HTTPS are not verified yet.
- Migration 003 is transactional and safe to rerun. SQL fixture checks roll back.
  Neither migration 003 nor SQL fixtures have been executed in Supabase yet.

External blocker: browser automation returned stale/contradictory state and then
`noWindowsAvailable`. It could not operate the Supabase editor or Name.com account.
A request for working authenticated browser access is pending. Do not promote
the new release or push its code to `main` until migration 003 is verified.

Next: apply migration 003, run `supabase/tests/hosted_v1.sql`, add the Name.com
CNAME, allow `https://oreo.manish.engineer` in Supabase redirect settings, verify
DNS/TLS, then deploy/promote and run authenticated context/history/approval checks.

## V1 release preparation — 2026-10-07, 21:29 IST

Active branch inspected: `worktree-web-ui`, HEAD `b96ab4e`.
The user requested faster V1 deployment while other agents handle audio.
Concurrent sessions are editing the hosted code in this same worktree;
preserve their changes and inspect Git again before committing or deploying.

- Added hosted conversation storage, recent context, atomic daily estimated
  budget reservations and paired message persistence in `api/conversations.py`
  and migration `202610070003_chat_budget.sql`.
- Added a conversation picker, new chat and history display. A concurrent
  session extended this with account usage, approval controls, authenticated
  history endpoints (`api/hosted.py`) and server-only request leases. These
  changes are present locally; do not attribute all of them to one session.
- Prepared `supabase/tests/hosted_v1.sql`: synthetic fixtures, quota and
  ownership assertions, request-lock checks, server-only write privileges,
  RLS isolation, then rollback. It has NOT been executed in Supabase yet.
- Combined mocked Python suite: 29 tests passed, including access rejection,
  context, persistence, quota, provider errors, admin authorization and leases.
  Compilation, inline JavaScript syntax and whitespace checks passed before
  the final small HTML/migration edits; recheck those at release time.
- Live Vercel inspection confirmed `web-ui-eta-nine.vercel.app` belongs to
  project `web-ui` in `man1shmandals-projects`, production READY deployment
  `dpl_CruJuKHz3dvkSPcr2e9eXRLPEjmw`. There is also an `oreo` project. Do not
  deploy to it by assumption; verify the project's ID and aliases first.

Release blockers: migration 003 is prepared but not applied/verified;
`ADMIN_EMAIL` configuration is not verified; the combined changes are not
committed or deployed by this task. Firefox is actively used, so a question
is pending about briefly using its Supabase editor. No browser permission
answer has been received in this task. Audio integration remains separate.

Next step: apply migration 003, run its rollback-only SQL checks, verify the
combined source, configure the administrator email if desired, release to
the confirmed `web-ui` project, and test authenticated two-turn context plus
refresh/reopen history. Custom domain/OAuth redirects remain pending; uploads,
research, model selection and streaming may follow core V1.

## Latest product update — 2026-10-07

Inspected branch: `worktree-web-ui`, product commit `b96ab4e`.
This update supersedes the earlier source-only handoff snapshot below.

- The user confirmed the deployed Google sign-in and chat flow works.
- Removed homepage creator attribution and removed the creator's name from
  the hosted AI system prompt. Do not add creator attribution to replies.
- Product changes were committed and pushed to `origin/main` as `b96ab4e`.
- Python compilation for `api` and `git diff --check` passed.
- The prior session verified production routing, public configuration,
  unauthenticated chat rejection, and Google OAuth redirection. It applied
  the profile policy restriction and verified only the profile SELECT policy
  remained. These were live checks, not merely source observations.
- Production URL: https://web-ui-eta-nine.vercel.app.
- Wording update deployed successfully to production (READY), deployment
  `dpl_CruJuKHz3dvkSPcr2e9eXRLPEjmw`, from product commit `b96ab4e` with
  existing local handoff notes present. Live homepage wording verified by
  HTTP fetch. No creator name remains in hosted `public/` or `api/` source.
- Existing handoff edits to AGENTS.md, provider instruction files and these
  notes were preserved. The local `.venv` remains untracked.

Remaining for a useful hosted v1: persistent conversations with context,
daily usage enforcement, a minimal administrator approval flow, and final
access-isolation checks. A custom domain and its OAuth redirect settings
remain to be configured. Uploads, research, multiple model selection and
streaming can follow the core release.

Next step: implement conversation persistence and daily token enforcement;
the current hosted handler sends one message with no prior chat context.

Updated: 2026-10-07 (local source inspection; no live service checks)
Branch inspected: worktree-web-ui
Initial commit inspected: be67d4d — Use Google sign-in for hosted Oreo
Latest commit observed during verification: b4d5b42 — Fix hosted API routing and protect account approval

## Goal
Oreo is a lean personal AI chat app with terminal, local browser and hosted browser
interfaces. This session established portable context for future agents. No next
product feature has been requested in this session; obtain that objective from the user.

## Working location
On this Mac, active work is `/Users/manishmandal/oreo/.claude/worktrees/web-ui`.
It is a locked Git worktree, not a disposable folder. The parent `~/oreo` is an older
checkout on `master`; do not start there merely because its name is Oreo.
Other worktrees: `settings-screen` on `agent-mode`, and `lightning-loader` on
`lightning-loader`. Do not merge them without inspecting their scope.
Repository: https://github.com/Man1shMandal/oreo (private).
Check the branch upstream and current remote state before any push.

## Architecture
- `oreo/`: terminal and local web app; local JSON storage and macOS Keychain settings.
- `api/index.py`: hosted request routing and static page serving.
- `api/health.py`, `api/config.py`, `api/chat.py`: health, public configuration and chat.
- `public/index.html`: hosted browser UI, Google sign-in via Supabase.
- `supabase/migrations/`: hosted schema and approval access rules.
- `requirements.txt` and `pyproject.toml`: Python dependencies.
- `.github/workflows/verify.yml`: Python 3.13 install and compilation checks.
- `vercel.json`: function configuration.

## Setup and checks
Python >=3.12. In a fresh clone: `python3 -m venv .venv`, then
`.venv/bin/python -m pip install -r requirements.txt`.
On this Mac, the worktree's existing `.venv` links to the parent environment.
Terminal: `bin/oreo`. Local web: `bin/oreo web 4799 --local --no-open`.
Compilation: `.venv/bin/python -m compileall -q oreo api`.
For UI edits, extract inline scripts and run `node --check`; also inspect the UI.
Use mocked provider calls for routine checks. Real ABB calls consume tokens.
Read `docs/hosting.md` before hosting changes.

Hosted environment variable names, never values:
`ABBY_API_KEY`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`.
Access must be configured separately for another machine or agent. Do not export
Keychain credentials or include `.env` or `~/.oreo` data in context packets.

## Existing unfinished work
Before this handoff setup, Git already showed modifications to:
`.github/workflows/verify.yml`, `api/chat.py`, `public/index.html`, `pyproject.toml`.
Untracked: `.venv`, `api/index.py`,
`supabase/migrations/202610070002_lock_profile_approval.sql`, `vercel.json`.
During handoff verification, these application changes became committed as
`b4d5b42` by another process/session. This handoff session did not commit them.
The remaining untracked `.venv` is local environment state; preserve it.
Recheck Git because concurrent work may continue.
The older parent checkout also has a deleted tracked `_old-web-mockup/index.html`
and untracked local files; preserve those too.

Source inspection shows the chat endpoint validates a Supabase token and profile
approval before calling Haiku. The pending migration removes client profile updates.
These observations are not evidence that the migration is applied or production works.

## Limitations and next step
Historical AGENTS.md hosting notes are a design direction, not current deployment status.
Live deployment URL, production commit, applied migrations, provider reachability,
OAuth setup and complete sign-in/chat behavior were not checked in this session.
The current hosted chat handler sends only the submitted message; it does not itself
implement the planned conversation persistence or daily token cap.

For the next task: read this and AGENTS.md, inspect current Git changes, get the user's
product objective, and choose relevant checks. Update this document after completing
work with actual outcomes and the next concrete action.

## Handoff setup verification
The project registry, packet generation, new-project initialization and preservation
of existing instructions were exercised locally. No application code was changed
as part of the handoff setup.
