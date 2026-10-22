# Elgato Facecam (1st gen) — control protocol

Everything here was obtained by capturing USB traffic from Elgato Camera Hub on Windows (USBPcap + Wireshark) while changing one setting at a time, and then reproducing it on Linux with the image brightness measured. Each fact is marked **confirmed** (seen in captures *and* reproduced on Linux) or **hypothesis**.

Tested unit: USB `0fd9:0078`, `bcdDevice` 4.09, USB 3.0 SuperSpeed, Linux 7.2 (`uvcvideo`), Camera Hub on Windows 11.

## Device layout

- Interfaces: **0** VideoControl (UVC 1.10), **1** VideoStreaming, **2** vendor HID.
- UVC topology: `CT (unit 1, sensor) → PU (unit 2) → XU (unit 3) → OT (unit 4, USB streaming)`.
- Extension unit (XU): unit 3, GUID `{a8e5782b-36e6-4fa1-87f8-83e32b323124}`, 9 controls (selectors 8, 18, 19, 20, 21, 25, 26, 27, 28).
- HID (interface 2): usage page `0xFF00`, no report IDs, 1024-byte input and output reports. Interrupt IN endpoint `0x89`; output reports go through `SET_REPORT` control transfers. Descriptor in [`data/hid_report_descriptor.hex`](../data/hid_report_descriptor.hex).
- Video formats: UYVY and MJPEG at 1920×1080, 1280×720 and 960×540, at 30 or 60 fps. Camera Hub uses **UYVY 1920×1080 at 60 fps** (format 1, frame 9).

## Behaviour that matters on Linux

1. **USB autosuspend resets the camera** (confirmed). The kernel runtime-suspends the camera 2 s after its last user (`power/control` = `auto`, `autosuspend_delay_ms` = 2000). On resume the camera restarts: it stalls every control request (`-EPIPE`, "Broken pipe") for about 0.5 s, and then reports its stored settings, losing whatever was changed since (seen: noise reduction 0 → 1, metering → center-weighted; shutter speed 600 kept). uvcvideo does not notice: V4L2, and therefore OBS, keep showing the old values. Opening a stream sometimes restores them (uvcvideo writing its cached values, apparently), but not reliably. With autosuspend disabled (`power/control` = `on`) the camera answers reads and writes without any stream and keeps its settings; the udev rule sets it when the camera is added, and obtura-init sets it again at the end, because uvcvideo re-enables autosuspend every time it binds (confirmed: `on` before a re-bind, `auto` after it; this is why the camera was back to `auto` after every boot). This is what earlier looked like "the camera only answers while it is streaming": a stream keeps it from suspending.
2. **uvcvideo loses controls at enumeration** (confirmed). The camera stalls part of the `GET_DEF`/`GET_CUR` requests uvcvideo sends while registering controls, and uvcvideo silently drops those controls: 5 of 10 or 0 of 10 controls have been observed. Re-binding uvcvideo (unbind/bind, which resets the device) recovers all 10. Look for `Failed to query (GET_DEF) ... -32` in the kernel log. `udev/obtura-init` automates the fix.
3. **XU selector 20 rejects writes in auto exposure** (confirmed). `SET_CUR` is stalled, and `VC_REQUEST_ERROR_CODE_CONTROL` then reads 2 ("Wrong state"). uvcvideo reports `EACCES` (Permission denied). Its `GET_INFO` changes with the mode: `0x0f` (disabled-by-auto, autoupdate) in auto, `0x03` in manual.
4. **`exposure_time_absolute` cannot be written through V4L2** (confirmed), even in shutter-priority mode while streaming, although the camera accepts the request from Camera Hub on Windows. Hypothesis: uvcvideo only marks that control active when `auto_exposure` is "Manual", a mode this camera does not offer. It is not needed: XU selector 20 controls the shutter speed.
5. **Settings persist across a reboot** (confirmed for XU sel 8 and PU Brightness). Whether they survive a real power loss is not known. After several uvcvideo re-binds, Power Line Frequency was back at its default (60 Hz) and metering read 0 while in auto, a value Camera Hub never sets.

## Camera Hub settings → USB requests

All writes are `SET_CUR` on interface 0, little-endian.

| Camera Hub setting | Request | Encoding | Status |
|---|---|---|---|
| Zoom / FOV | CT Zoom Absolute (standard) | 2 B, 1–31 | confirmed (= V4L2 `zoom_absolute`) |
| Auto exposure → off | CT AE Mode = `0x04` (shutter priority), CT Exposure Time Absolute = 312, XU sel 20 = 600, PU Brightness = 0 | AE 1 B; exposure 4 B (100 µs units); sel 20 4 B | confirmed (Exposure Time not needed on Linux) |
| Auto exposure → on | CT AE Mode = `0x02`, PU Brightness = 128 | — | confirmed |
| Shutter speed (manual) | **XU sel 20** | 4 B, **units of 50 µs** (value = 20000 / denominator): 1/30 = 667, 1/33 = 600, 1/50 = 400, 1/60 = 333, 1/90 = 222, 1/100 = 200, 1/120 = 167, 1/200 = 100, 1/250 = 80. Range 1–5000 | confirmed |
| ISO (manual) | **PU Brightness** (standard) | 2 B: ISO 100 = 0, 400 = 86, 800 = 128, 3200 = 214, 6400 = 255 (roughly logarithmic, not exactly) | confirmed |
| Metering (auto) | **XU sel 8** | 1 B: center-weighted = 1, average = 2. Reads 0 by itself in manual mode; Camera Hub never writes 0 | confirmed |
| Noise reduction | **XU sel 18** | 1 B: on = 1, off = 0 | confirmed |
| Anti-flicker | PU Power Line Frequency (standard) | 1 B: off = 0, 50 Hz = 1, 60 Hz = 2 | confirmed (= V4L2 `power_line_frequency`) |
| AE lock | Not a camera control: Camera Hub switches to manual using the current auto values, and back to auto on unlock | — | confirmed |
| Contrast, saturation, sharpness, white balance | Not captured | — | hypothesis: standard PU controls, already in V4L2 |
| SAVE button | Not captured | — | hypothesis: stores settings in the camera |

In auto exposure, PU Brightness works as **exposure compensation** (128 = neutral). Measured mean luma: 48 / 95 / 130 for 0 / 128 / 255.

## Extension unit selectors

Values read on the tested unit.

| Sel | Len | Min–max / default | GET_INFO | Meaning |
|---|---|---|---|---|
| 8 | 1 | 0–2 / 1 | GET, SET | **Metering** (confirmed) |
| 18 | 1 | 0–1 / 0 | GET, SET | **Noise reduction** (confirmed) |
| 19 | 1 | 0–1 / 0 | GET, SET | unknown switch; never written by Camera Hub |
| 20 | 4 | 1–5000 / 312 | GET, SET (+ disabled-by-auto, autoupdate in auto) | **Shutter speed**, 50 µs units (confirmed). Writing CT Exposure Time Absolute = N sets it to 2N |
| 21 | 2 | 0–100 / 60 | GET, SET | unknown percentage; never written by Camera Hub (it is **not** ISO) |
| 25 | 1 | 0–1 / 0 | GET, SET | unknown switch; never written |
| 26 | 4 | 0–0 / 0 | GET, SET | live statistic that follows image brightness (hypothesis); treat as read-only |
| 27 | 4 | 0–0 / 0 | GET, SET | constant 11796 (hypothesis: calibration or AE target); treat as read-only |
| 28 | 2 | 0–1 / 0 | GET, SET | unknown switch; never written |

## HID interface

Camera Hub sends **no setting over HID** (confirmed across all captures). It only polls the camera:

- Every ~1.6 s: `SET_REPORT` with payloads starting with `00 c4`, `00 dd 06 06` and `00 dd 06 07`, plus `GET_REPORT` reads.
- Only while exposure is in auto: `00 dd 03 0e` … `00 dd 03 11`. Hypothesis: these read the current auto-exposure gain and shutter, which Camera Hub needs for "AE lock".
- Once when Camera Hub starts: `00 bb`, `00 cc`, `00 b2 a1/02/05/06`, `00 b7 02`. They are not needed to change settings from Linux.

**Do not send anything to the HID interface.** On other Elgato devices (e.g. Cam Link 4K) the vendor HID channel can read, write and **erase the firmware flash**.

## Not working / not investigated

- No HDR on this model, not even in Camera Hub.
- XU selectors 19, 21, 25 and 28: Camera Hub never writes them. Do not write them.
- Firmware update: never captured, never to be reproduced.
