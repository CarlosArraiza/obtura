# How the protocol was found (and how to contribute captures)

The method is simple: record the USB traffic between Elgato Camera Hub and the camera on Windows while changing **one setting at a time**, then find the requests that only appear in that capture. Use the same method to add settings that are still missing (contrast, saturation, sharpness, white balance, the SAVE button), other firmware versions or other Facecam models.

## Safety rules (read first)

- **Only ever send what Camera Hub itself sends.** Never send requests that are made up, fuzzed or "similar" to a captured one, over HID or over the extension unit. On other Elgato devices the vendor HID channel can erase the firmware flash; a wrong request can brick the camera.
- Never capture or replay a **firmware update**.
- On Windows, do not install drivers that replace the camera's driver (Zadig, WinUSB, libusbK): Camera Hub would stop working. USBPcap is a capture filter and is fine.
- Note down the firmware version Camera Hub shows, and do not update the firmware in the middle of a capture session.

## Windows: capturing

1. Install **Wireshark** with the **USBPcap** option ticked, and reboot (USBPcap is a filter driver).
2. Find the root hub the camera is on: run `C:\Program Files\USBPcap\USBPcapCMD.exe` as administrator, or capture on each `USBPcapN` while re-plugging the camera.
3. In the USBPcap options (gear icon next to `USBPcapN`):
   - Tick **the checkbox** of the camera's device. Selecting the row is not enough (and hard to see in the dark theme); without the tick the capture comes out empty. Untick "capture from all devices".
   - **Snapshot length 2048**: control requests fit, video packets are truncated.
   - **Capture buffer length 134217728** (128 MB). With the default 1 MB, the video stream from the Camera Hub preview overflows the buffer and control packets are lost.
4. Do **one capture per setting**, under one minute long: start the capture, wait about 10 s without touching anything, change a single setting with ~5 s between changes (switch: off → on → off → on; slider: a few known values), wait 5 s, stop. Write down what you did and roughly when.
5. With the preview open the raw capture is huge (gigabytes of video). Keep only control and interrupt transfers:
   ```
   tshark -r raw.pcapng -Y "usb.transfer_type == 0x02 || usb.transfer_type == 0x01" -w 05_metering.pcapng
   ```
6. Known USBPcap glitch: an elevated `USBPcapCMD.exe` can hang when a capture stops and block the next one. Kill it with `taskkill /PID <pid> /F` as administrator.

## Analysing

```
python3 tools/analyze_capture.py captures/05_metering_center_to_average.pcapng --set-only --no-hid --summary
```

It needs no Wireshark or tshark and works on Windows and Linux. Things to know:

- Camera Hub re-reads every control about every 3 s (`GET_CUR`). These reads tell you the camera's exact state at any point of a capture.
- HID traffic is periodic polling (see [protocol.md](protocol.md#hid-interface)); `--no-hid` hides it.
- A rejected request shows `STATUS=0xc0000004` (STALL). Camera Hub then usually reads `ent0 sel=2` (`VC_REQUEST_ERROR_CODE_CONTROL`), which gives the reason (2 = wrong state).
- In a UVC request the selector is the high byte of `wValue` and the unit is the high byte of `wIndex` (1 = CT, 2 = PU, 3 = the Elgato XU).

Useful Wireshark display filters (`N` = USB address of the camera):

| What | Filter |
|---|---|
| SET_CUR to the Elgato XU | `usb.device_address == N && usb.setup.bRequest == 0x01 && usb.setup.wIndex == 0x0300` |
| SET_CUR to the PU / CT | same with `wIndex == 0x0200` / `0x0100` |
| HID SET_REPORT | `usb.device_address == N && usb.setup.bRequest == 0x09 && usb.setup.wIndex == 2` |

## Linux: reproducing

1. With the camera streaming, compare before and after: `facecam xu-dump`.
2. Reproduce **only captured values**, one change at a time, and check the effect on the picture. For exposure-related settings, measuring the mean luma of captured frames gives an objective check. The tables in `facecam/facecam` only contain values verified this way.
3. Open an issue or pull request with the capture (`.pcapng`, control traffic only), what you did during it, your firmware version (`cat /sys/bus/usb/devices/*/bcdDevice` for the camera, or `lsusb -v`) and the `analyze_capture.py` output.

Before sharing a capture, remove your camera's serial number: it is sent as a UTF-16 string in the device descriptors at the start of a capture that includes plugging the camera in.
