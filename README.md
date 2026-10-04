# clip-over-ssh

Paste screenshots from your Mac into an SSH session. Built for coding agents (Claude Code, Codex) running on a remote box.

You take a screenshot on your laptop, type `/clip` in the agent running over SSH, and it sees the image. No uploads, no shared folders, no third-party service: the clipboard travels through the SSH connection you already have.

```
 Mac (your laptop)                         Remote host (over SSH)
┌──────────────────────┐                 ┌──────────────────────────┐
│ clipd                │  RemoteForward  │ clip                     │
│ 127.0.0.1:47777  ◄───┼─────── ssh ─────┼─── 127.0.0.1:47777       │
│ reads/writes the     │                 │ → /tmp/clip/clip-….png   │
│ macOS pasteboard     │                 │ → agent opens the image  │
└──────────────────────┘                 └──────────────────────────┘
```

## Why

Agents in a remote terminal can read images from disk, but your screenshots live on your laptop. `scp`-ing every capture gets old fast. Terminal image paste doesn't survive SSH, and OSC 52 only handles text in one direction.

## Install

**On your Mac:**

```sh
git clone https://github.com/jmendozaf/clip-over-ssh && cd clip-over-ssh
./install.sh                    # installs clipd as a LaunchAgent and creates a token
./install.sh remote myserver    # installs `clip` + the token on the remote host
```

Then forward the port in `~/.ssh/config` on your Mac:

```
Host myserver
    RemoteForward 127.0.0.1:47777 127.0.0.1:47777
```

Reconnect and check it from the remote host:

```sh
clip status    # ok: clipd reachable on 127.0.0.1:47777
```

Requirements: macOS with the system `python3`, and `curl` plus a POSIX `sh` on the remote host. No other dependencies.

## Usage (on the remote host)

```sh
clip              # save the clipboard image, print /tmp/clip/clip-20261004-153012.png
clip text         # print the clipboard text
make 2>&1 | clip copy   # send text back to your Mac clipboard
clip status       # check the tunnel and the token
```

Exit codes: `0` ok, `2` the clipboard is empty, `1` anything else (no tunnel, bad token).

## With coding agents

Copy `skills/clip/` into your agent's skills folder on the remote host:

```sh
cp -r skills/clip ~/.claude/skills/   # Claude Code
cp -r skills/clip ~/.codex/skills/    # Codex
```

Now take a screenshot (Cmd+Ctrl+Shift+4), and in the agent type `/clip what's wrong with this layout?`

## Security

- `clipd` listens only on `127.0.0.1`, never on the network.
- Every request needs a random token (`~/.config/clip-over-ssh/token`, mode 600 on both ends). This matters on shared servers: anyone on the remote host can connect to a forwarded port, but only you have the token.
- The remote side writes captures to `/tmp/clip` with mode 700.
- Nothing leaves the SSH connection.

Rotate the token by deleting it on the Mac and running `./install.sh remote <host>` again.

## Uninstall

```sh
./install.sh uninstall              # on the Mac
rm ~/.local/bin/clip                # on the remote host
```

## Development

```sh
python3 -m unittest discover -s tests -v
shellcheck bin/clip install.sh
```

The tests run the real `clip` script against a real `clipd` server with a fake clipboard, so they also pass on Linux.

## License

MIT © Javier Mendoza
