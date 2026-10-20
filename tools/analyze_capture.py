#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""List the control requests sent to the Elgato Facecam in a USBPcap capture (.pcapng).

No dependencies (no tshark): it parses pcapng and the USBPcap header (linktype 249) directly,
so it runs the same on Windows and Linux.

Usage:
  python3 analyze_capture.py <capture.pcapng> [--addr N] [--set-only] [--no-hid] [--summary]

  --addr N     USB address of the camera (default: from the 0fd9:0078 device descriptor if the
               capture contains it, otherwise the only address with control traffic)
  --set-only   writes only (SET_CUR and SET_REPORT)
  --no-hid     hide HID traffic (Camera Hub polls the HID interface periodically)
  --summary    at the end, the distinct values written to each control

USBPcap layout: control OUT transfers carry setup + data in the setup record (stage 0); IN
transfers carry their data in the completion record (stage 3, info=1), matched by irpId.
Rejected requests show STATUS=0xc0000004 (STALL).
"""
import collections, struct, sys

UVC_REQ = {0x01: "SET_CUR", 0x81: "GET_CUR", 0x82: "GET_MIN", 0x83: "GET_MAX", 0x84: "GET_RES",
           0x85: "GET_LEN", 0x86: "GET_INFO", 0x87: "GET_DEF"}
UNITS = {1: "CT", 2: "PU", 3: "XU"}
NAMES = {(1, 2): "AE Mode", (1, 4): "Exposure Time Abs", (1, 11): "Zoom Abs",
         (2, 2): "Brightness", (2, 3): "Contrast", (2, 5): "Power Line Freq", (2, 7): "Saturation",
         (2, 8): "Sharpness", (2, 10): "WB Temperature", (2, 11): "WB Temperature Auto"}
USBPCAP_HDR = struct.Struct("<HQIHBHHBBI")


def packets(path):
    """(t_seconds, info, dev, ep, transfer, stage, irp, status, payload) for each USBPcap packet."""
    d = open(path, "rb").read()
    off, linktypes, tsres = 0, [], []
    while off + 12 <= len(d):
        btype, blen = struct.unpack_from("<II", d, off)
        body = d[off + 8:off + blen - 4]
        if btype == 1:
            linktypes.append(struct.unpack_from("<H", body)[0])
            tsres.append(1e-6)
        elif btype == 6:
            iid, th, tl, caplen, _ = struct.unpack_from("<IIIII", body)
            if linktypes[iid] == 249:
                p = body[20:20 + caplen]
                hl, irp, status, _fn, info, _bus, dev, ep, tr, _dl = USBPCAP_HDR.unpack_from(p)
                stage = p[27] if tr == 2 else None
                yield (((th << 32) | tl) * tsres[iid], info, dev, ep, tr, stage, irp, status, p[hl:])
        off += blen


def le(b):
    return int.from_bytes(b, "little") if 0 < len(b) <= 4 else None


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("--"):
        print(__doc__)
        return 1
    pkts = list(packets(args[0]))
    addr = int(args[args.index("--addr") + 1]) if "--addr" in args else None
    if addr is None:
        for _t, info, dev, _ep, tr, stage, *_r, data in pkts:
            if tr == 2 and stage == 3 and data[:2] == b"\x12\x01" and data[8:12] == bytes.fromhex("d90f7800"):
                addr = dev
                break
    if addr is None:
        devs = {p[2] for p in pkts if p[4] == 2}
        if len(devs) != 1:
            sys.exit(f"cannot guess the camera address (found {sorted(devs)}); pass --addr N")
        addr = devs.pop()
    print(f"# Facecam at USB address {addr}; {len(pkts)} packets")
    t0 = pkts[0][0] if pkts else 0

    pending, written = {}, collections.defaultdict(list)
    for t, info, dev, ep, tr, stage, irp, status, data in pkts:
        if dev != addr or tr != 2:
            continue
        if stage == 0 and info == 0 and len(data) >= 8:
            brt, breq, wval, widx, wlen = struct.unpack_from("<BBHHH", data)
            pending[irp] = (t, brt, breq, wval, widx, wlen, data[8:8 + wlen])
            continue
        if stage != 3 or info != 1 or irp not in pending:
            continue
        ts, brt, breq, wval, widx, wlen, out = pending.pop(irp)
        payload = out if not brt & 0x80 else data
        iface, ent, sel = widx & 0xFF, widx >> 8, wval >> 8
        if iface == 0 and brt in (0x21, 0xA1) and breq in UVC_REQ:
            name = NAMES.get((ent, sel), "")
            desc = f"UVC {UVC_REQ[breq]:8} {UNITS.get(ent, f'ent{ent}')} sel={sel:<2} {name}"
            is_set = breq == 0x01
            if is_set and status == 0:
                written[(ent, sel, name)].append(le(payload))
        elif iface == 2 and brt == 0x21 and breq == 0x09:
            if "--no-hid" in args:
                continue
            desc, is_set = "HID SET_REPORT", True
            payload = payload.rstrip(b"\0")
        elif iface == 2 and brt == 0xA1 and breq == 0x01:
            if "--no-hid" in args or "--set-only" in args:
                continue
            desc, is_set = "HID GET_REPORT", False
            payload = payload.rstrip(b"\0")
        else:
            continue
        if "--set-only" in args and not is_set:
            continue
        val = le(payload) if desc.startswith("UVC") else None
        st = "" if status == 0 else f"  STATUS=0x{status:08x}"
        print(f"{ts - t0:9.3f}  {desc:44} {payload.hex()}" + (f"  (={val})" if val is not None else "") + st)

    if "--summary" in args:
        print("\n# UVC writes per control (in order, consecutive repeats collapsed)")
        for (ent, sel, name), vals in sorted(written.items()):
            seq = [v for i, v in enumerate(vals) if i == 0 or v != vals[i - 1]]
            print(f"{UNITS.get(ent, ent)} sel={sel:<2} {name:20} {seq}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
