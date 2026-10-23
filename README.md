# Obtura

Camera Hub-style controls for the **Elgato Facecam (1st generation)** on Linux: manual shutter speed, ISO, AE metering, noise reduction and anti-flicker, plus a fix for the camera losing its controls when it is plugged in.

Elgato only supports these settings through Camera Hub on Windows and macOS. They were reverse-engineered from USB captures of Camera Hub; see [docs/protocol.md](docs/protocol.md).

> Formerly *facecam-linux*: `sudo ./install.sh` removes the old `facecam` files. Re-check the OBS source properties afterwards (the control names did not change).
>
> Unofficial project, not affiliated with or endorsed by Elgato or Corsair. "Elgato" and "Facecam" are trademarks of Corsair Memory, Inc.

## Supported hardware

| Camera | USB ID | Firmware (`bcdDevice`) | Status |
|---|---|---|---|
| Elgato Facecam (1st gen) | `0fd9:0078` | 4.09 | tested |

Facecam MK.2, Facecam Pro and Facecam Neo have different USB IDs and are **not** supported. Captures from their owners are welcome (see [Contributing](#contributing)).

## What you get

- **`obtura-gui`**, a Camera Hub-style window (*Obtura* in the application menu): live preview, exposure (auto/manual, metering, shutter speed, ISO), zoom, contrast, saturation, sharpness, white balance, noise reduction and anti-flicker. Settings are read back from the camera every couple of seconds, so changes made from OBS or `obtura` show up too.
- **`obtura` command**, with the same names and values as Camera Hub:
  ```
  obtura                          # show current settings
  obtura exposure manual          # like switching "Auto" off in Camera Hub (starts at ISO 100, 1/33 s)
  obtura shutter 1/50             # 1/30 1/33 1/50 1/60 1/90 1/100 1/120 1/200 1/250
  obtura iso 800                  # 100 400 800 3200 6400
  obtura exposure auto
  obtura metering average         # center | average (auto exposure only)
  obtura noise-reduction off
  obtura anti-flicker 50          # off | 50 | 60
  ```
  It works whether or not another application (OBS…) is using the camera.
- **New V4L2 controls**: *Shutter Speed* (a menu with the Camera Hub speeds), *AE Metering* and *Noise Reduction*. They appear in OBS (V4L2 source properties) and in any V4L2 control app.
- **Boot fix**: when it is plugged in, the camera rejects part of the requests uvcvideo uses to register its controls, and uvcvideo drops them silently (anywhere from 5 of 10 to all of them). A udev rule re-initialises the driver when that happens and then registers the new controls.
- **Settings that stick**: the camera resets its settings whenever Linux puts it to sleep (USB autosuspend, 2 s after the last application closes it), while V4L2 and OBS keep showing the old values. The udev rule and `obtura-init` disable autosuspend for this camera (`obtura-init` has to do it again because uvcvideo turns it back on whenever it binds).

## Install

Requirements: Python 3, `v4l-utils` (`v4l2-ctl`), systemd and udev. No compiled code. The GUI also needs **PySide6** with QtMultimedia (`pyside6` and `qt6-multimedia` on Arch, `python3-pyside6` on Fedora, `python3-pyside6.qtmultimedia` and `python3-pyside6.qtmultimediawidgets` on Debian/Ubuntu); the command line tool needs no extra Python packages.

```sh
git clone https://github.com/CarlosArraiza/obtura.git
cd obtura
sudo ./install.sh
```

Then re-plug the camera (or reboot) and check the log: `journalctl -t obtura`. The new controls (*Shutter Speed*, *AE Metering*, *Noise Reduction*) should be listed by `v4l2-ctl -d /dev/videoN --list-ctrls`, where `/dev/videoN` is the Facecam (`v4l2-ctl --list-devices`). To uninstall: `sudo ./uninstall.sh`.

Files installed: `/usr/local/bin/obtura`, `/usr/local/bin/obtura-gui`, `/usr/local/share/applications/obtura-gui.desktop`, `/usr/local/libexec/obtura-init`, `/etc/udev/rules.d/99-obtura.rules`.

### Arch Linux and derivatives

Build and install the package with pacman instead (it will also be on the AUR as `obtura`):

```sh
git clone https://github.com/CarlosArraiza/obtura.git
cd obtura/packaging/arch
makepkg -si
```

For the GUI: `sudo pacman -S --asdeps pyside6 qt6-multimedia`. Remove it with `sudo pacman -R obtura`. If you installed with `install.sh` before, run `sudo ./uninstall.sh` first: its udev rule in `/etc` would take precedence over the package's.

## Using the GUI

Run `obtura-gui` or open *Obtura* from the application menu.

- If the camera is free, the window opens a preview (UYVY 960×540).
- If another application (OBS…) is using the camera, there is no preview, but the settings still work.
- **Stop preview** frees the camera for other applications; the settings keep working.

Exposure offers only Camera Hub's values. Zoom, contrast, saturation, sharpness and white balance are standard UVC controls and use the ranges the camera reports. On an untested firmware version the window is read-only unless started with `obtura-gui --force`.

## Using it with OBS

In the properties of the *Video Capture Device (V4L2)* source:

| Camera Hub | OBS control | Values |
|---|---|---|
| Exposure: Auto on | Auto Exposure | Auto Mode |
| Exposure: Auto off | Auto Exposure | Shutter Priority Mode |
| Shutter speed | Shutter Speed | 1/30 s … 1/250 s |
| ISO (manual) | Brightness | ISO 100 = 0, 400 = 86, 800 = 128, 3200 = 214, 6400 = 255 |
| Exposure compensation (auto) | Brightness | 128 = neutral |
| Metering | AE Metering | Center-weighted / Average |
| Noise reduction | Noise Reduction | on / off |
| Anti-flicker | Power Line Frequency | Disabled / 50 Hz / 60 Hz |

ISO and auto exposure are standard UVC controls and uvcvideo does not allow renaming them, which is why ISO shows up as "Brightness". Use `obtura iso 800` if you prefer Camera Hub's units.

Things to know:

- **OBS keeps its own copy of the control values in the scene.** It did not re-apply them when starting (OBS 32.2, tested), but it can write them back to the camera when you open the source properties, which undoes changes made with `obtura`. Keep the values in the OBS source properties in line with what you want.
- Camera Hub captures **UYVY 1920×1080 at 60 fps**. Choose the same in OBS for the same image quality.
- Under 50 Hz lighting (Europe and most of the world) use 1/50 s or 1/100 s in manual mode; other speeds can flicker. With 60 Hz mains use 1/60 or 1/120 s.
- **Stutter at 60 fps in low light**: in auto exposure the camera lengthens the exposure past one frame (e.g. 1/50 s = 20 ms against 16.7 ms per frame at 60 fps) and frames arrive irregularly; OBS logs `select timed out`. Capture at 30 fps (plenty if your OBS output is 30 fps), or use manual exposure at 1/60 s or shorter (1/100 s under 50 Hz lighting) and raise the ISO. The same applies to manual 1/30 s and 1/33 s at 60 fps.

## Safety

The camera also has a vendor HID interface. On other Elgato devices that channel can rewrite or erase the firmware. This project **never** uses it, and only sends values seen in Camera Hub captures. `obtura` refuses to write on firmware versions other than the tested one unless you pass `--force`.

## Contributing

Missing pieces: contrast, saturation, sharpness and white balance captures (probably standard UVC), Camera Hub's **SAVE** button, other firmware versions, and the other Facecam models. [docs/reverse-engineering.md](docs/reverse-engineering.md) explains how to capture Camera Hub on Windows safely and how to analyse the result with `tools/analyze_capture.py`. Raw data from the tested unit is in [`captures/`](captures/) and [`data/`](data/).

Planned: a uvcvideo quirk upstream so the boot fix is no longer needed.

## License

[GPL-3.0-or-later](LICENSE).
