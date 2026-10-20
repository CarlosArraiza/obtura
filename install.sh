#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Installs facecam, the udev rule and its helper. Run as root: sudo ./install.sh
set -euo pipefail
cd "$(dirname "$0")"
[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo ./install.sh" >&2; exit 1; }
for dep in python3 v4l2-ctl systemd-run; do
    command -v "$dep" >/dev/null || { echo "Missing dependency: $dep (v4l2-ctl is in v4l-utils)" >&2; exit 1; }
done
install -Dm755 facecam/facecam /usr/local/bin/facecam
install -Dm755 udev/facecam-init /usr/local/libexec/facecam-init
install -Dm644 udev/99-elgato-facecam.rules /etc/udev/rules.d/99-elgato-facecam.rules
udevadm control --reload-rules
echo "Installed. Re-plug the camera (or reboot), then check: journalctl -t facecam"
echo "To apply it now without re-plugging: sudo udevadm trigger --action=add --attr-match=idVendor=0fd9 --attr-match=idProduct=0078"
