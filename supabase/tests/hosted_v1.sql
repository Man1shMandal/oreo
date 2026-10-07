-- Run after migration 003. All synthetic fixtures are rolled back.
begin;
insert into auth.users (id, email) values
  ('00000000-0000-0000-0000-00000000a001', 'oreo-release-a@example.invalid'),
  ('00000000-0000-0000-0000-00000000a002', 'oreo-release-b@example.invalid');
update public.profiles set approved = true, daily_token_limit = 1000
  where id in ('00000000-0000-0000-0000-00000000a001', '00000000-0000-0000-0000-00000000a002');

do $$
declare
  result jsonb;
  chat uuid;
  lease uuid;
begin
  result := public.acquire_chat('00000000-0000-0000-0000-00000000a001');
  lease := (result->>'lease')::uuid;
  if lease is null then raise exception 'Request lock missing'; end if;
  result := public.acquire_chat('00000000-0000-0000-0000-00000000a001');
  if result->>'error' is distinct from 'busy' then raise exception 'Concurrent request bypass'; end if;
  perform public.release_chat('00000000-0000-0000-0000-00000000a001', lease);
  result := public.reserve_chat('00000000-0000-0000-0000-00000000a001', null, 'Release test', 100, 700);
  chat := (result->>'conversation_id')::uuid;
  if chat is null or (result->>'remaining')::integer <> 200 then
    raise exception 'Reservation failed: %', result;
  end if;
  result := public.reserve_chat('00000000-0000-0000-0000-00000000a001', chat, 'Release test', 100, 700);
  if result->>'error' is distinct from 'limit' then raise exception 'Quota bypass'; end if;
  result := public.reserve_chat('00000000-0000-0000-0000-00000000a002', chat, 'Release test', 100, 700);
  if result->>'error' is distinct from 'conversation' then raise exception 'Ownership bypass'; end if;
  perform public.save_chat_turn('00000000-0000-0000-0000-00000000a001', chat, 'hello', 'hello back');
  if (select count(*) from public.messages where conversation_id = chat) <> 2 then
    raise exception 'Turn persistence failed';
  end if;
  if has_function_privilege('authenticated', 'public.reserve_chat(uuid,uuid,text,integer,integer)', 'execute')
    or has_function_privilege('authenticated', 'public.acquire_chat(uuid)', 'execute')
    or has_table_privilege('authenticated', 'public.messages', 'insert')
    or has_function_privilege('authenticated', 'public.save_chat_turn(uuid,uuid,text,text)', 'execute')
    or has_function_privilege('authenticated', 'public.release_chat(uuid,uuid)', 'execute')
    or has_function_privilege('anon', 'public.reserve_chat(uuid,uuid,text,integer,integer)', 'execute')
    or has_function_privilege('anon', 'public.acquire_chat(uuid)', 'execute')
    or has_table_privilege('authenticated', 'public.conversations', 'update')
    or has_table_privilege('authenticated', 'public.daily_usage', 'update')
    or has_table_privilege('authenticated', 'public.chat_requests', 'select') then
    raise exception 'Client write privileges remain';
  end if;
end;
$$;

select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-00000000a002', true);
set local role authenticated;
do $$
begin
  if exists (select 1 from public.conversations where user_id = '00000000-0000-0000-0000-00000000a001')
    or exists (select 1 from public.messages) then
    raise exception 'Cross-user read isolation failed';
  end if;
end;
$$;
reset role;
rollback;
select 'Hosted V1 quota, persistence, permissions and isolation checks passed' as result;
