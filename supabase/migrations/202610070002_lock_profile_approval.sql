-- Approval and limits are managed by the server or project administrator.
drop policy if exists "users update their profile" on public.profiles;
revoke update on public.profiles from anon, authenticated;
