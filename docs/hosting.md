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

The current endpoint answers one message at a time. Saved conversation
history, uploads, an admin interface, and daily token enforcement are still
pending. A configured daily limit in the database does not yet enforce a cap.
