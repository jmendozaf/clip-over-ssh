---
name: clip
description: Fetch the image (or text) on the user's Mac clipboard while working over SSH, and look at it. Use when the user types /clip, says "I copied a screenshot", "look at my clipboard", or refers to an image they copied on their local Mac.
---

# clip

The user is connected to this machine over SSH. Their clipboard lives on their Mac and is reachable through a tunnel via the `clip` command (clip-over-ssh).

1. Run `clip` (or `clip text` if they asked for text). It prints the path of a PNG under /tmp/clip/.
2. Open that path as an image (Read tool in Claude Code, view_image in Codex) and treat it as if the user had pasted it.
3. Continue with whatever the user asked alongside /clip, using the image as context. If they asked nothing, describe it briefly and ask what to do.

To send something back to the user's Mac clipboard: `echo "..." | clip copy`.

Errors:
- "no tunnel": the SSH session from the Mac lacks `RemoteForward 127.0.0.1:47777 127.0.0.1:47777`, or clipd is not running on the Mac. Ask the user to reconnect, or run on the Mac: `ssh -O forward -R 127.0.0.1:47777:127.0.0.1:47777 <host>`.
- "has no image": ask the user to copy the screenshot (Cmd+Ctrl+Shift+4) and try again.
- "token rejected": ask the user to run `./install.sh remote <host>` again on their Mac.
