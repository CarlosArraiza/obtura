#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo ./uninstall.sh" >&2; exit 1; }
rm -f /usr/local/bin/obtura /usr/local/bin/obtura-gui /usr/local/share/applications/obtura-gui.desktop /usr/local/libexec/obtura-init /etc/udev/rules.d/99-obtura.rules
udevadm control --reload-rules
echo "Uninstalled. Mapped controls disappear the next time the camera is re-plugged."
