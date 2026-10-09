# Hosted Oreo

Production is https://oreo.manish.engineer. The existing Vercel project is
`oreo`. Its Python entrypoint is `api.index:handler`; it serves the page,
JavaScript modules, and authenticated API routes. Google sign-in and owned
conversation data use Supabase. Every signed-in account can chat immediately.

The hosted interface supports streaming, saved conversations, model selection,
PDF/Word/text attachments, images, scanned PDFs, and optional web research.
Images are resized in the browser and wrapped as PDF files for ABB's gateway.
Requests containing images use Claude when a non-Claude model was selected.
Web results have citations; unavailable search results produce an explicit notice.

Voice chat uses the browser's own speech recognition and speech output, so it
needs no key and adds no server calls. The mic types what you say and keeps
listening through pauses. While voice is on, a bar above the box offers Pause/
Resume (stop, check or edit the text, then carry on) and Send. Nothing is sent
until Send, Enter or the send arrow. Answers are never read aloud on their
own: each finished answer has Listen (read it aloud, tap again to stop) and Copy
(copy the answer text). After about three silent
recognition sessions the mic pauses itself. Sending "new chat", "turn web
on/off", "open settings", "read that again" or "stop" by voice runs that action
instead (`public/voice.js`). Firefox has no recognition, so the button is
disabled there.

Oreo installs as an app on phones, tablets and computers. Chrome, Edge and
Android show an Install button in the sidebar. iPhone and iPad never offer that
prompt, so there the same button shows how to use Share, then Add to Home Screen.
`public/manifest.webmanifest` and the icons describe the app.
`public/sw.js` caches only the signed-out shell (page, scripts, icons and the
Supabase module) so the app opens on a weak connection. It never caches `/api/`
or non-GET requests, so chats and tokens stay out of the cache. Raise `CACHE` in
`sw.js` if the list of shell files changes.

The browser sends up to five files with a combined size of 2.2 MB after photo
resizing. The server limits JSON bodies to 3.2 MB to fit serverless requests.
Document extraction retains up to 200,000 characters per file. These are upload
and processing bounds, not daily token quotas.

Versioned content in the existing messages table retains extracted document
text, model-readable PDF image parts, small image previews, original file names,
and assistant citations. Old plain-text messages remain readable. Attachments
follow the conversation's ownership and row-level policies. No new database
migration is needed. This is bounded inline storage for small uploads; separate
private object storage is appropriate if larger files are added later.

Server-side secrets are Vercel environment variables. `/api/config` exposes only
Supabase's public connection settings and model choices. The browser cannot write
messages or usage. Apply the existing three migrations for a fresh installation,
then run `supabase/tests/hosted_v1.sql`. The legacy approved flag is automatically
enabled by the server; it does not require manual user approval.

All authenticated accounts have no application daily token quota. Chat no longer
calls reserve_chat or writes daily_usage, and answer calls have no application
max_tokens cap. Provider context, output, and account limits still apply. Legacy
quota tables/functions remain for schema compatibility; no migration is needed.
A server-only lease serializes requests per account and saves remain owned.

Settings is visible in the chat header. It offers custom standing instructions,
default model, reply style, creativity, recent history depth, attachment reuse,
web defaults, and Enter behavior. Preferences are stored per account in this
browser, not synced between devices. Efficient history uses up to roughly 3,000
tokens of text; balanced roughly 6,000; extended roughly 16,000. Selection scans
the latest 100 messages, keeps the last three turns even after long answers,
and includes bounded earlier excerpts ranked against the current question.
Long messages are shortened with an explicit marker; this is bounded context,
not permanent memory of every message. No extra model call is needed.
Attachment excerpts have a separate small budget. Follow-ups select relevant excerpts from the latest document instead of sending
all previous files. Brief replies and optional web research save more tokens.
No extra summarization model call is needed. New uploads are still sent in full.
The original circular Oreo mark is shared across hosted and local surfaces.

Run `.venv/bin/python -m unittest discover -s tests -v`, Python compilation,
`node --check public/chat.js`, `node --check public/markdown.js`, `node --check public/preferences.js`, and
`git diff --check` before release. Use an isolated fake-auth/model server for
browser checks. For production verify Google sign-in, streaming, file follow-ups,
reopened history and citations, model selection, new chat, and sign-out.

Deploy to the existing Oreo project. Preserve its custom-domain aliases and
Supabase redirect allowlist. The local terminal and Mac web interfaces continue
using their existing local settings, Keychain, and chat files.

Hosted auth and database calls reuse HTTPS connections in warm functions. The
browser loads the account through one authenticated history request and updates
the sidebar from saved replies without two additional account/history requests.
Streamed markdown paints at most every 40 ms and flushes the final answer
immediately. Provider generation and optional web search still affect latency.

CI caches Python dependencies, cancels superseded runs on the same ref, and runs
Python regressions plus JavaScript behavior and syntax checks. Mock HTTP servers
use a short shutdown poll instead of waiting half a second after every test.
