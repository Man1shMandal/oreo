# Oreo

My personal AI in the terminal, running on the ABB AI API (Claude, GPT and Gemini).

## Run

    ~/oreo/bin/oreo

To get an `oreo` command everywhere:

    ln -s ~/oreo/bin/oreo /opt/homebrew/bin/oreo

Or in the browser:

    oreo web              # http://localhost here, http://oreo.local for the rest of the network
    oreo web --local      # this Mac only
    oreo web 8080         # another port; --no-open skips opening the browser

It uses port 80 so the link has no port number, and falls back to 4747 if 80 is taken. The name `oreo.local` is announced with Bonjour while the server runs. Macs, iPhones and recent Windows and Android devices pick it up; on anything else, use the IP address it prints.

Use the + button to attach PDFs, Word files, text and code files, or images. You can also drag them in or paste them. Documents are turned into text. Images and scanned PDFs are sent as PDF pages, the only way the ABB gateway takes pictures. Only Claude can see them, so a message with a picture always goes to Sonnet.

The Web button (on by default) lets Oreo research. Haiku first decides whether the question needs the web. If it does, Oreo searches DuckDuckGo (no key needed), reads the top 5 pages, keeps the relevant paragraphs and answers with numbered sources. A searched answer costs about 3k tokens; anything else costs one tiny Haiku call. Paste a link and Oreo reads that page directly.

Anyone on the same Wi-Fi can open the network link. Oreo asks each person their name and keeps their chats separate, in `~/.oreo/people/<name>`. Everyone uses your API key and monthly tokens.

Some things only work from a browser on this Mac (http://127.0.0.1:4747): settings, the API key, usage, `@file` attachments, your standing instructions, and the chats you share with the terminal. Names aren't passwords, so anyone on the network can type someone else's name and see that person's chats. Only use it on networks you trust.

On first run Oreo asks for your API key and saves it to the macOS Keychain (the same entry `Check Usage.command` uses). `ABBY_API_KEY` overrides it if set.

Type `/settings` to change the key, default model, temperature, reply length and standing instructions, or to test the connection. Settings are saved in `~/.oreo/settings.json`.

## Use

- Type to chat. Ctrl-C stops a reply, Ctrl-D quits.
- `@path/to/file` attaches a file.
- `/help` lists commands: `/settings`, `/model`, `/new`, `/resume`, `/usage`, `/system`, `/temp`, `/check`.

Chats are saved as JSON in `~/.oreo/chats`. Web visitors' chats go in `~/.oreo/people/<name>`. Uploaded images go in an `uploads` folder next to the chats.

## Saving tokens

Oreo is set up to spend as little of the 20M monthly tokens as it can:

- The system prompt is short (about 80 tokens) and asks for brief answers.
- Only about 1500 tokens of recent history go with each message. Older turns are folded into an 80-word summary by Haiku. Change this under Settings > Memory.
- Attached files are sent once. Later messages carry a one-line note instead, so `@` the file again if Oreo needs to see it.
- Replies are capped at 1024 tokens (Settings > Reply length).
- Asking the exact same thing in the same context again is answered from `~/.oreo/cache` for free.
- Each reply shows a rough token count, e.g. `≈94 in · 2 out`.

The cheapest models per request are the Claude ones. In a quick test the same one-line question cost 25 tokens on Haiku or Sonnet, 36 on GPT and 82 on Gemini, which spends extra on hidden reasoning.

## Code

- `oreo/config.py`: models, defaults, Oreo's personality
- `oreo/provider.py`: API calls (swap this to use another provider)
- `oreo/commands.py`: slash commands (add one with `@command`)
- `oreo/cli.py`: chat loop
- `oreo/files.py`: `@file` attachments
- `oreo/store.py`: saved chats
- `oreo/lean.py`: token saving (history window, summaries, cache)
- `oreo/attach.py`: uploaded files (PDF, Word, text, images)
- `oreo/research.py`: web search and reading for answers
- `oreo/web.py` + `oreo/web.html`: the browser UI (local only, no extra installs)
- `oreo/settings.py`: saved settings and the Keychain key
