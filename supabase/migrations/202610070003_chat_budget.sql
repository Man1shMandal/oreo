-- Browser clients can read their history; only the server writes model turns.
begin;
drop policy if exists "users manage their conversations" on public.conversations;
drop policy if exists "users manage messages in their conversations" on public.messages;
drop policy if exists "users read their conversations" on public.conversations;
create policy "users read their conversations" on public.conversations
  for select using (auth.uid() = user_id);
drop policy if exists "users read their messages" on public.messages;
create policy "users read their messages" on public.messages
  for select using (exists (
    select 1 from public.conversations c
    where c.id = conversation_id and c.user_id = auth.uid()
  ));
revoke insert, update, delete on public.conversations, public.messages, public.daily_usage
  from anon, authenticated;
create index if not exists messages_conversation_time
  on public.messages (conversation_id, created_at desc, id desc);
create index if not exists conversations_user_time
  on public.conversations (user_id, updated_at desc);

-- Row locking makes simultaneous requests share one estimated application budget.
-- The server reserves estimated prompt tokens plus the full output cap; this is
-- not an exact provider-token count because the gateway omits actual usage.
create or replace function public.reserve_chat(
  p_user uuid, p_conversation uuid, p_title text, p_input integer, p_output integer
) returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
  v_limit integer;
  v_usage public.daily_usage;
  v_chat uuid := p_conversation;
  v_date date := (now() at time zone 'UTC')::date;
begin
  if p_input < 1 or p_output < 1 then
    raise exception 'Invalid budget';
  end if;
  select daily_token_limit into v_limit from public.profiles
    where id = p_user and approved;
  if not found then
    return jsonb_build_object('error', 'approval');
  end if;
  if v_chat is not null and not exists (
    select 1 from public.conversations where id = v_chat and user_id = p_user
  ) then
    return jsonb_build_object('error', 'conversation');
  end if;
  insert into public.daily_usage (user_id, usage_date) values (p_user, v_date)
    on conflict do nothing;
  select * into v_usage from public.daily_usage
    where user_id = p_user and usage_date = v_date for update;
  if v_usage.input_tokens + v_usage.output_tokens + p_input + p_output > v_limit then
    return jsonb_build_object('error', 'limit');
  end if;
  update public.daily_usage set input_tokens = input_tokens + p_input,
    output_tokens = output_tokens + p_output
    where user_id = p_user and usage_date = v_date;
  if v_chat is null then
    insert into public.conversations (user_id, title) values (p_user, left(p_title, 80))
      returning id into v_chat;
  end if;
  return jsonb_build_object('conversation_id', v_chat,
    'remaining', v_limit - v_usage.input_tokens - v_usage.output_tokens - p_input - p_output);
end;
$$;

-- Store the pair atomically, with deterministic order even at equal timestamps.
create or replace function public.save_chat_turn(
  p_user uuid, p_conversation uuid, p_message text, p_reply text
) returns jsonb language plpgsql security invoker set search_path = '' as $$
begin
  perform id from public.conversations
    where id = p_conversation and user_id = p_user for update;
  if not found then raise exception 'Conversation not found'; end if;
  insert into public.messages (conversation_id, role, content, created_at) values
    (p_conversation, 'user', p_message, clock_timestamp()),
    (p_conversation, 'assistant', p_reply, clock_timestamp() + interval '1 microsecond');
  update public.conversations set updated_at = clock_timestamp() where id = p_conversation;
  return jsonb_build_object('saved', true);
end;
$$;
revoke all on function public.reserve_chat(uuid, uuid, text, integer, integer) from public, anon, authenticated;
revoke all on function public.save_chat_turn(uuid, uuid, text, text) from public, anon, authenticated;
grant execute on function public.reserve_chat(uuid, uuid, text, integer, integer) to service_role;
grant execute on function public.save_chat_turn(uuid, uuid, text, text) to service_role;

-- A short server-only lease serializes each user's requests before history reads.
create table if not exists public.chat_requests (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  lease uuid not null,
  expires_at timestamptz not null
);
alter table public.chat_requests enable row level security;
revoke all on public.chat_requests from public, anon, authenticated;
grant select, insert, update, delete on public.chat_requests to service_role;
create or replace function public.acquire_chat(p_user uuid)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_lease uuid := gen_random_uuid();
begin
  perform id from public.profiles where id = p_user and approved for update;
  if not found then return jsonb_build_object('error', 'approval'); end if;
  insert into public.chat_requests (user_id, lease, expires_at)
    values (p_user, v_lease, clock_timestamp() + interval '5 minutes')
    on conflict (user_id) do update set lease = excluded.lease,
      expires_at = excluded.expires_at
    where public.chat_requests.expires_at < clock_timestamp();
  if not found then return jsonb_build_object('error', 'busy'); end if;
  return jsonb_build_object('lease', v_lease);
end;
$$;
create or replace function public.release_chat(p_user uuid, p_lease uuid)
returns jsonb language plpgsql security invoker set search_path = '' as $$
begin
  delete from public.chat_requests where user_id = p_user and lease = p_lease;
  return jsonb_build_object('released', true);
end;
$$;
revoke all on function public.acquire_chat(uuid) from public, anon, authenticated;
revoke all on function public.release_chat(uuid, uuid) from public, anon, authenticated;
grant execute on function public.acquire_chat(uuid) to service_role;
grant execute on function public.release_chat(uuid, uuid) to service_role;
commit;
