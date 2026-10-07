# Hosted Oreo

The development flow is:

1. Work on a branch and open a pull request.
2. GitHub Actions checks that Oreo installs and its Python files compile.
3. Merge to main.
4. Vercel deploys main to production; other branches receive preview deployments.

The first hosted endpoint is /api/health. It verifies that the GitHub to Vercel
release path works without exposing a model key or user data.

The hosted app must not use the macOS Keychain, local chat files, Bonjour, or terminal tools.
Use these services instead:

- Vercel environment variables for the ABBY_API_KEY secret
- Supabase Auth for sign-in
- Supabase Postgres for chats and user settings
- Supabase Storage for uploads

Before production, confirm that the ABB API accepts requests from Vercel and permits the key to be used from a public server.

## Current hosted v1

Production: https://web-ui-eta-nine.vercel.app

The Python preset uses `api.index:handler` as its single entrypoint. It serves
the page, `/api/config`, `/api/health`, and `/api/chat`. Pointing the entrypoint
at the health handler causes all API paths to return the health response.

Google sign-in uses Supabase. Its Google callback is
`https://ahgbdtbmmwisqhulutgy.supabase.co/auth/v1/callback`.
Allow the production URL in Supabase's redirect settings. The browser reads
only the Supabase URL and publishable key from `/api/config`.

Apply migrations in `supabase/migrations` through the Supabase SQL editor.
The approval-policy restriction was applied on 2026-10-07 and verified:
profiles have only the user SELECT policy. Approvals must be managed by the
project administrator; users cannot approve themselves.

The next release adds saved conversations, recent chat context and a daily
estimated token budget. Apply `202610070003_chat_budget.sql` before deploying
that code. Then run `supabase/tests/hosted_v1.sql` in the SQL Editor. Its
synthetic fixtures roll back; a passing result verifies persistence, quota,
server-only writes and cross-user read isolation.

The ABB gateway does not return actual token counts. Each request charges an
estimate of the full prompt (roughly four characters per token, plus message
overhead) and reserves the full 700-token answer cap. Failed requests also
consume that reservation. The daily budget resets at midnight UTC. This is
an application budget, not an exact model-token or billing meter.

The combined V1 code also includes an Accounts screen. Set `ADMIN_EMAIL` on
the intended Vercel project to enable it for that authenticated email only.
It can approve or revoke accounts and edit positive daily limits. Until it
is configured, use Supabase's Table Editor on `public.profiles` as the
administrator interface. Browser users cannot approve themselves, write
usage or inject model history. Never expose the server secret key to clients.

Release checks: run the Python tests and inline JavaScript syntax check,
apply and verify the migration, confirm the Vercel target, deploy, then test
Google sign-in, two-turn context, refresh/reopen history, new chat, sign-out,
pending-account rejection and daily-limit rejection. Do not release code
which calls the new database functions before the migration is applied.

Audio is being implemented separately. Uploads, research, model selection,
streaming and a custom domain are additional work. Configure the domain's
Supabase OAuth redirect allowlist when that domain is selected.

## Release setup checkpoint

The confirmed project is `oreo` (`prj_kQdBCNFycMEAPvnlwLdrYNZ4EuIU`). The local
metadata formerly called it `web-ui`; that name is stale. `ADMIN_EMAIL` is now
configured in production. The new code is built and staged; migration 003 still
requires execution and the rollback-only SQL checks before promotion.

`oreo.manish.engineer` is attached to this project. At Name.com, add a CNAME with
host `oreo` and value `d3380b04008a43cd.vercel-dns-017.com`, as returned by Vercel
verification. Preserve all other DNS records. Add `https://oreo.manish.engineer`
to Supabase's redirect allowlist and use it as the Site URL when going live.
Google's callback stays the Supabase callback URL above.
