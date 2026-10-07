# Oreo

My personal AI in the terminal, running on the ABB AI API (Claude, GPT and Gemini).

## Run

    ~/oreo/bin/oreo

To get an `oreo` command everywhere:

    ln -s ~/oreo/bin/oreo /opt/homebrew/bin/oreo

On first run Oreo asks for your API key and saves it to the macOS Keychain (the same entry `Check Usage.command` uses). `ABBY_API_KEY` overrides it if set.

Type `/settings` to change the key, default model, temperature, reply length and standing instructions, or to test the connection. Settings are saved in `~/.oreo/settings.json`.

## Use

- Type to chat. Ctrl-C stops a reply, Ctrl-D quits.
- `@path/to/file` attaches a file.
- `/help` lists commands: `/settings`, `/model`, `/new`, `/resume`, `/usage`, `/system`, `/temp`, `/check`.

Chats are saved in `~/.oreo/chats`.

## Code

- `oreo/config.py`: models, defaults, Oreo's personality
- `oreo/provider.py`: API calls (swap this to use another provider)
- `oreo/commands.py`: slash commands (add one with `@command`)
- `oreo/cli.py`: chat loop
- `oreo/files.py`: `@file` attachments
- `oreo/store.py`: saved chats
- `oreo/web.py` + `oreo/web.html`: the browser UI (local only, no extra installs)
- `oreo/settings.py`: saved settings and the Keychain key
