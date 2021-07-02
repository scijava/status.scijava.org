#!/bin/sh
mkdir -p "$HOME/.ssh"
echo "$SSH_PRIVATE_KEY" > "$HOME/.ssh/id_ed25519"
chmod -R -w,o-rwx,g-rwx "$HOME/.ssh"
