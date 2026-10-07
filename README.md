# Oreo

My personal AI in the terminal, running on the ABB AI API (Claude, GPT and Gemini).

## Run

    ~/oreo/bin/oreo

To get an `oreo` command everywhere:

    ln -s ~/oreo/bin/oreo /opt/homebrew/bin/oreo

Or in the browser, with the same chats and settings:

    oreo web              # opens http://127.0.0.1:4747; `oreo web 8080` for another port, --no-open to skip the browser

On first run Oreo asks for your API key and saves it to the macOS Keychain (the same entry `Check Usage.command` uses). `ABBY_API_KEY` overrides it if set.

Type `/settings` to change the key, default model, temperature, reply length and standing instructions, or to test the connection. Settings are saved in `~/.oreo/settings.json`.

## Use

- Type to chat. Ctrl-C stops a reply, Ctrl-D quits.
- `@path/to/file` attaches a file.
- `/help` lists commands: `/settings`, `/model`, `/new`, `/resume`, `/usage`, `/system`, `/temp`, `/check`.

Chats are saved in `~/.oreo/chats`.

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
- `oreo/web.py` + `oreo/web.html`: the browser UI (local only, no extra installs)
- `oreo/settings.py`: saved settings and the Keychain key
