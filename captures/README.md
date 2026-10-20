# Captures

USBPcap captures of Elgato Camera Hub (Windows 11) talking to a Facecam with firmware 4.09. They contain only control and interrupt transfers; video was filtered out, so they contain no images. The camera's serial number has been replaced by `XXXXXXXXXXXX`.

Read them with `python3 ../tools/analyze_capture.py <file> --set-only --no-hid --summary`, or with Wireshark.

| File | What was done in Camera Hub | Result |
|---|---|---|
| `01_zoom_up_down` | Zoom slider up and down, several times. Also contains Camera Hub's start-up (HID `bb`, `cc`, `b2…`, `b7`) | CT Zoom Absolute 1–31 |
| `02_auto_exposure_off` | Auto exposure off (the other transitions fell outside the capture) | AE Mode 4, Exposure Time 312, XU sel 20 = 600, Brightness 0 |
| `02b_auto_exposure_off_on` | Auto exposure off, then on | Off as in 02; on: AE Mode 2, Brightness 128 |
| `03_shutter_1-33_1-60_1-120_1-250` | Manual mode, shutter 1/33 → 1/60 → 1/120 → 1/250, with intermediate slider steps | XU sel 20: 667, 600, 400, 333, 222, 200, 167, 100, 80 |
| `04_iso_100_400_800_3200_packet_loss` | ISO 100 → 400 → 800 → 3200. **Lost packets** (USBPcap buffer too small); kept for reference only | Brightness 86, 128 |
| `04b_iso_100_400_800_3200_6400` | Same with a 128 MB buffer, up to 6400 and back to 100 | Brightness 86, 128, 214, …, 255, …, 0 |
| `05_metering_center_to_average` | Auto mode, metering center-weighted → average | XU sel 8 = 2 |
| `06_ae_lock_unlock` | Auto mode, AE lock on (~4 s) and off (~11 s) | Emulated by Camera Hub with manual mode; the first XU sel 20 write in auto is rejected (STALL, "wrong state") |
| `07_noise_reduction_toggle` | Noise reduction on → off → on → off | XU sel 18: 1, 0, 1, 0 |
| `08_anti_flicker_off_50_60_50_off` | Anti-flicker Off → 50 → 60 → 50 → Off | Power Line Frequency 1, 2, 1, 0 |

`data/` has the USB descriptors (`lsusb -v`, serial removed), the HID report descriptor, the supported video formats and the V4L2 control list of the same unit.
