#!/usr/bin/env python3
# Capture the 8052 internal ROM dump printed by the AVR host, and save it as a
# binary file.
#
# Usage (PlatformIO's Python has pyserial):
#   ~/.platformio/penv/bin/python scripts/capture_romdump.py [port] [output.bin]
#
# The port defaults to the first /dev/cu.usb* device. The output defaults to
# romdump.bin. The script resets the AVR (via DTR) after opening the port, so
# the whole startup sequence - RAM test, load, dump - runs again.

import glob
import re
import sys
import time

import serial

BAUD = 38400
ROM_SIZE = 0x4000
TIMEOUT_SECONDS = 120

LINE_RE = re.compile(r"^([0-9A-F]{4}):((?: [0-9A-F]{2}){16})$")


def main():
    args = sys.argv[1:]
    port = args[0] if len(args) > 0 else None
    output = args[1] if len(args) > 1 else "romdump.bin"
    if port is None:
        candidates = sorted(glob.glob("/dev/cu.usb*"))
        if not candidates:
            sys.exit("No /dev/cu.usb* serial port found. Specify one.")
        port = candidates[0]

    # Open with DTR/RTS deasserted, then pulse DTR to reset the AVR. Opening
    # with DTR asserted would reset it before the port is ready to receive.
    s = serial.Serial()
    s.port = port
    s.baudrate = BAUD
    s.timeout = 0.5
    s.dtr = False
    s.rts = False
    s.open()
    time.sleep(0.2)
    s.reset_input_buffer()
    s.dtr = True
    s.rts = True
    time.sleep(0.05)
    s.dtr = False
    s.rts = False
    print(f"Reset AVR on {port}. Waiting for dump...", file=sys.stderr)

    data = bytearray(ROM_SIZE)
    seen = set()
    in_dump = False
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        line = s.readline().decode("ascii", errors="replace").rstrip("\r\n")
        if not line:
            continue
        if not in_dump:
            print(line, file=sys.stderr)
        if line == "ROMDUMP BEGIN":
            in_dump = True
            continue
        if line == "ROMDUMP END":
            break
        if in_dump:
            m = LINE_RE.match(line)
            if not m:
                print(f"Unparseable dump line: {line!r}", file=sys.stderr)
                continue
            address = int(m.group(1), 16)
            data[address:address + 16] = bytes.fromhex(m.group(2))
            seen.add(address)
    else:
        sys.exit("Timed out waiting for the dump to finish.")

    missing = [a for a in range(0, ROM_SIZE, 16) if a not in seen]
    if missing:
        print(f"Warning: {len(missing)} lines missing, "
              f"first at 0x{missing[0]:04X}. Filled with 00.", file=sys.stderr)

    with open(output, "wb") as f:
        f.write(data)
    print(f"Wrote {len(data)} bytes to {output}.", file=sys.stderr)

    distinct = len(set(data))
    print(f"First bytes: {data[:16].hex(' ')}", file=sys.stderr)
    print(f"Distinct byte values: {distinct}", file=sys.stderr)
    if data[:3] == bytes([0x02, 0x40, 0x00]):
        print("Starts with the reset stub (02 40 00): EA was probably latched "
              "at reset, or the ROM is protected. This is likely NOT the "
              "internal ROM.", file=sys.stderr)
    elif distinct <= 2:
        print("Very few distinct values: probably not a real ROM dump.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
