# Oreo: notes for agents

Oreo is Manish's personal AI chat app. It runs on the ABB "ABBY" AI API, which is OpenAI-compatible and serves Claude, GPT and Gemini. It has two thin front-ends, a terminal chat and a browser UI, over the same provider, storage and settings code. Read this before changing anything.

## How Manish wants it built

- Keep it lean and modular. Each concern lives in one small file and can be swapped out (for example a new provider or a new storage back end) without touching the rest.
- Keep the UI minimal: clean screens, few controls, extras later. No emoji in the UI or in replies.
- Write docs and copy in short, plain language that sounds like a person wrote it. Avoid AI-style filler and bullets that start with a bold label.
- Give plans as short bullets.
- Spend effort on capability, not decoration.
- Match the existing code: stdlib where possible, short docstrings, comments only where the reason isn't obvious.

## Layout

```
bin/oreo            launcher; runs `python -m oreo` with the repo's .venv
oreo/__main__.py    `oreo` → terminal chat, `oreo web` → browser server
oreo/config.py      models, defaults, persona prompt, VISION_MODEL, SUMMARY_MODEL
oreo/provider.py    API calls (streaming + retry on empty streams, usage endpoint)
oreo/lean.py        token saving: system prompt, history window, summaries, reply cache, image parts
oreo/store.py       chats as JSON files
oreo/settings.py    ~/.oreo/settings.json + API key in macOS Keychain
oreo/files.py       @path attachments (terminal, and the owner in web)
oreo/attach.py      browser uploads: PDF/Word/text → text, images/scanned PDFs → PDF pages
oreo/research.py    web research: plan queries (Haiku) → DuckDuckGo → read pages → cited extracts
oreo/web.py         stdlib HTTP server, JSON API, SSE streaming, owner/visitor rules, Bonjour
oreo/web.html       the whole browser UI (vanilla JS, no build step, small safe markdown renderer)
oreo/cli.py, commands.py   terminal chat loop and slash commands
```

## Running

- Terminal: `bin/oreo`. Web: `bin/oreo web`. It uses port 80 and falls back to 4747. Add `--local` to serve this Mac only and `--no-open` to skip opening the browser.
- Always run with the repo's `.venv`. In this worktree, `.venv` is a symlink to `~/oreo/.venv`. Homebrew's Python is missing pypdf, python-docx and Pillow, and uploads fail silently under it.
- The server reads `web.html` on every request but loads the Python only at startup. After changing a `.py` file, restart the server, or the page and the API won't match. (This already caused a "PDFs don't reach the model" bug once.)
- URLs: http://localhost on the Mac, http://oreo.local on the LAN (announced with `dns-sd -P`), or the Mac's LAN IP.

## Data (all under ~/.oreo)

- `chats/*.json` holds the owner's chats, shared by the terminal and web. `chats/uploads/` holds their images.
- `people/<name-slug>/` holds each web visitor's chats and uploads.
- `settings.json` holds model, temperature, max_tokens, context and instructions.
- `cache/` holds exact-repeat reply caching. Empty replies must never be cached.
- A message looks like `{"role", "content", "images"?: [file names], "sources"?: [{title, url}]}`. File attachments are inlined into `content` as `<file path="name">…</file>` blocks.

## Who can do what (web)

- **Owner**: a browser on this Mac, either from loopback or from the Mac's own LAN address (`client IP == socket's local IP`). The owner gets settings, the key, usage, `@path` and the terminal chats.
- **Visitors**: anyone else on the LAN. They give a name, which is stored in localStorage and sent as `X-Oreo-User`, and they get their own folder. Names aren't passwords.
- `trusted()` checks the Host and Origin headers, to block DNS rebinding and CSRF. Keep it when you add routes.
- `research.public()` blocks fetching private or LAN addresses, so visitors can't make Oreo read the router or the Mac.

## ABB gateway quirks (tested, important)

- Base URL: `https://api.abby.abb.com/api/v1/developers`. The key is in the Keychain under service `abby-ai-api`, account `usage`. `ABBY_API_KEY` overrides it. The limit is 20M tokens a month; `GET /usage` with header `X-ABBY-API-Key` reports use.
- The chat response's `usage` field is always empty, so token counts in the UI are estimates (about 4 characters per token).
- **Images**: standard `image_url` parts fail on every model. The only format that works is `{"type": "input_file", "file_data": <plain base64 PDF>, "filename": "x.pdf"}`, and only Claude models can read it. So images are wrapped in a one-page PDF, and when a GPT or Gemini model is selected, messages with pictures switch to `VISION_MODEL` (Sonnet).
- **Empty text parts are rejected**. A picture-only message needs placeholder text.
- **Flakiness**: at times a share of requests fail. Non-streaming calls show an upstream "403 Authentication failed". Streaming calls return 0 chunks with no error. `provider.stream` retries empty streams 3 times and then raises. Don't conclude that a model "can't do X" from one empty reply; retest several times.
- **Tool calling**: it works on GPT and Gemini but fails on Claude, because the gateway mishandles it. The agent-mode branch uses a text-based tool protocol instead.

## Token saving (lean.py)

Short persona prompt, about 1500 tokens of history per request, older turns folded into an 80-word Haiku summary, attachments sent once (later messages carry a one-line stub), a reply cap of 1024, and an exact-repeat cache. A web search adds about 3k tokens. Keep new features in that spirit.

## Testing

- Use a fake model for most tests. Monkeypatch `provider.Provider.stream`, run `web.main(["4799", "--local", "--no-open"])` in a thread with `HOME` set to a temp folder, and make HTTP calls to it.
- Real API tests cost tokens. Use `claude-4.5-haiku`, keep them small, and afterwards delete any test chats and uploads from `~/.oreo`.
- Check the page's JS by extracting the `<script>` block and running `node --check`.

## Git

- Repo: https://github.com/Man1shMandal/oreo (private). `main` is the current line of work.
- Local work happens in the worktree `~/oreo/.claude/worktrees/web-ui` (branch `worktree-web-ui`, which tracks `origin/main` with `push.default=upstream`). Manish sometimes edits on GitHub, so fetch and rebase if a push is rejected. Never force-push.
- Other local branches: `agent-mode` (tools: files, shell, web fetch, docs; text protocol for Claude) and `lightning-loader` (terminal loader). Neither has been pushed.
- End commit messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Planned next: hosted version on Vercel (not started)

The goal is to run Oreo independently at a subdomain of Manish's domain, at zero cost.

- **Hosting**: Vercel Hobby. The static page plus Python functions with streamed replies; 300 s max per request, about 4.5 MB request body.
- **Logins and data**: Supabase free tier, for Google and email sign-in, Postgres (chats, settings, token use per user, enforced by row-level rules) and file storage (images). Avoid Vercel Blob for chats, since its free tier allows only 2k writes a month.
- **Users**: multiple. New sign-ups wait for admin approval, there's a daily token cap per user, and admin is decided by email.
- **API key**: a server-side Vercel secret only. It never goes to the browser, the database or git, and the web Settings has no key field.
- **Storage**: `store.py` gets two interchangeable back ends, local files and Supabase. The terminal and Mac web keep working on files.
- **Step 0, before building**: confirm that the ABB API, and DuckDuckGo, are reachable from Vercel. The ABB API may only accept company addresses, and DuckDuckGo often blocks cloud servers; the fallback is a free search API (Tavily or Brave). Also confirm ABB allows using the key from a public server.
- **Waiting on Manish**: `npx vercel login`, the domain name, and later a Supabase account and a Google OAuth app.
