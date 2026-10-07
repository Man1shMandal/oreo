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
