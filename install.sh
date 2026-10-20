#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Installs obtura, obtura-gui, the udev rule and its helper. Run as root: sudo ./install.sh
set -euo pipefail
cd "$(dirname "$0")"
[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo ./install.sh" >&2; exit 1; }
for dep in python3 v4l2-ctl systemd-run; do
    command -v "$dep" >/dev/null || { echo "Missing dependency: $dep (v4l2-ctl is in v4l-utils)" >&2; exit 1; }
done
# Remove the files of v0.1-v0.2, when the project was called facecam-linux
rm -f /usr/local/bin/facecam /usr/local/bin/facecam-gui /usr/local/share/applications/facecam-gui.desktop \
      /usr/local/libexec/facecam-init /etc/udev/rules.d/99-elgato-facecam.rules
install -Dm755 obtura/obtura /usr/local/bin/obtura
install -Dm755 obtura/obtura-gui /usr/local/bin/obtura-gui
install -Dm644 obtura/obtura-gui.desktop /usr/local/share/applications/obtura-gui.desktop
install -Dm755 udev/obtura-init /usr/local/libexec/obtura-init
install -Dm644 udev/99-obtura.rules /etc/udev/rules.d/99-obtura.rules
udevadm control --reload-rules
python3 -c "import PySide6.QtMultimediaWidgets" 2>/dev/null ||
    echo "Note: obtura-gui needs PySide6 (Qt 6 with QtMultimedia): pyside6 / python3-pyside6 / python3-pyside6.qtmultimedia"
echo "Installed. Re-plug the camera (or reboot), then check: journalctl -t obtura"
echo "To apply it now without re-plugging: sudo udevadm trigger --action=add --attr-match=idVendor=0fd9 --attr-match=idProduct=0078"
