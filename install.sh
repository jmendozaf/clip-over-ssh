#!/bin/sh
# install.sh: set up clip-over-ssh.
#
#   ./install.sh                 on your Mac: install clipd + LaunchAgent, create the token
#   ./install.sh remote <host>   from your Mac: install `clip` and the token on <host>
#   ./install.sh uninstall       on your Mac: remove the LaunchAgent
set -eu

here=$(cd "$(dirname "$0")" && pwd)
bin_dir="$HOME/.local/bin"
label="dev.jmf.clipd"
plist="$HOME/Library/LaunchAgents/$label.plist"
port="${CLIP_OVER_SSH_PORT:-47777}"

install_mac() {
    [ "$(uname)" = Darwin ] || { echo "run this on your Mac (or use: ./install.sh remote <host>)" >&2; exit 1; }
    mkdir -p "$bin_dir" "$HOME/Library/LaunchAgents"
    install -m 755 "$here/bin/clipd" "$bin_dir/clipd"
    "$bin_dir/clipd" token >/dev/null
    sed "s#__CLIPD__#$bin_dir/clipd#" "$here/launchd/$label.plist" > "$plist"
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$plist"
    echo "clipd running on 127.0.0.1:$port (logs: /tmp/clipd.log)"
    echo
    echo "Next: ./install.sh remote <host>, then add to ~/.ssh/config:"
    echo "  Host <host>"
    echo "      RemoteForward 127.0.0.1:$port 127.0.0.1:$port"
}

install_remote() {
    host=$1
    token=$("$bin_dir/clipd" token)
    ssh "$host" 'mkdir -p ~/.local/bin ~/.config/clip-over-ssh && chmod 700 ~/.config/clip-over-ssh'
    scp -q "$here/bin/clip" "$host:.local/bin/clip"
    printf '%s\n' "$token" | ssh "$host" 'umask 077 && cat > ~/.config/clip-over-ssh/token && chmod +x ~/.local/bin/clip'
    echo "installed clip on $host. Reconnect with the RemoteForward and run: clip status"
}

case "${1:-mac}" in
    mac) install_mac ;;
    remote) [ $# -eq 2 ] || { echo "usage: ./install.sh remote <host>" >&2; exit 2; }; install_remote "$2" ;;
    uninstall)
        launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
        rm -f "$plist" "$bin_dir/clipd"
        echo "clipd removed (token kept in ~/.config/clip-over-ssh)"
        ;;
    *) sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
