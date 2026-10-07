# Oreo

My personal AI in the terminal, running on the ABB AI API (Claude, GPT and Gemini).

## Run

    ~/oreo/bin/oreo

To get an `oreo` command everywhere:

    ln -s ~/oreo/bin/oreo /opt/homebrew/bin/oreo

The key comes from the macOS Keychain (the same entry `Check Usage.command` uses), or from `ABBY_API_KEY` if set.

## Use

- Type to chat. Ctrl-C stops a reply, Ctrl-D quits.
- `@path/to/file` attaches a file.
- `/help` lists commands: `/model`, `/new`, `/resume`, `/usage`, `/system`, `/temp`, `/check`.

Chats are saved in `~/.oreo/chats`.

## Code

- `oreo/config.py`: models, defaults, Oreo's personality
- `oreo/provider.py`: API calls (swap this to use another provider)
- `oreo/commands.py`: slash commands (add one with `@command`)
- `oreo/cli.py`: chat loop
- `oreo/files.py`: `@file` attachments
- `oreo/store.py`: saved chats
