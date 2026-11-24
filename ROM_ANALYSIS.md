# MSM83C154 Mask ROM Analysis

Analysis of the 16 KB internal mask ROM dumped from an OKI MSM83C154
(8051-family) microcontroller. The dump is `romdump.bin` (16384 bytes, internal
checksum verified).

## How the dump was made

The MSM83C154 does not latch EA at reset, which allows the internal ROM to be
read:

1. The AVR host loads a small dumper program (`mcs51/src/romdump.c`) at
   code address 0x4000, plus a stub `LJMP 0x4000` at 0x0000.
2. The AVR holds EA low and releases reset. The 8052 fetches everything
   externally, runs the stub and jumps to the dumper.
3. About 10 ms later the AVR raises EA. Code addresses 0x0000–0x3FFF now read
   the internal ROM. Code at 0x4000 and above is still fetched externally.
4. The dumper copies code 0x0000–0x3FFF (MOVC) to data 0x0000–0x3FFF (MOVX).
5. The AVR resets the 8052, reads the SRAM back and prints it over serial.
   `scripts/capture_romdump.py` captures the output and writes `romdump.bin`.

Build: `pio run -e mcs51 -t upload` (see `platformio.ini` and `README.md`).

## Overview

| Item | Value |
|---|---|
| Reset vector | 0x0000 → 0x10E8 |
| INT0 vector | 0x0003 → 0x0030 |
| Timer 1 / Timer 2 vectors | 0x001B / 0x002B → 0x0637 |
| ROM checksum | 0x0000–0x3FFC, compared with 0x3FFE–0x3FFF (`B9 45`) |
| Config byte | 0x3FFD |
| ASCII strings | None |
| Code reached by recursive disassembly | 12,685 of 16,384 bytes |
| Unused | 0x36CA–0x3FFD (zero-filled) |

The 8052's hardware UART is not used.

## Revised picture

The 8052 is an I/O controller sitting under a larger host computer. It has
three interfaces.

### 1. Host mailbox (external registers F8h–FFh)

- **Status reads.** The host writes an internal-RAM address to FAh. Firmware
  returns that byte at F8h and echoes the address at F9h. Flag bytes 20h–25h
  and 2Eh clear when read (21h is masked with C1h), so they are host-visible
  error and status registers. Handler: 0x05A4.
- **Start command.** The host writes 01h to FDh. Firmware builds per-channel
  masks from each channel's state at 3Fh+n and returns status byte 21h at FDh.
  Handler: 0x05F1.
- **Debug monitor** (0x35A7–0x36C1):
  - Entry: host writes FCh to FBh. Firmware answers FCh at FAh and sets flag
    2Ah.1.
  - Exit: host writes FAh.
  - Command 8xh writes and Axh reads. Bits 0–3 pick the target:

    | Bit | Target |
    |---|---|
    | 0 | Internal RAM (`@R0`) |
    | 1 | External RAM (`MOVX @R0`) |
    | 2 | Link controller register (`MOVX @DPTR`, DPH = 00h) |
    | 3 | Port: P1, P2 or P3 (address < 2, = 2, > 2) |

  - Address comes from FFh and data from FEh. Read results go to FAh. The
    address and data are echoed to E4h/E5h.
  - In debug mode the main loop (0x1751) stops normal work. It kicks the
    watchdog and drives P3.5 as a health output: steady when OK, toggling
    when error flags 21h.1 or 21h.2 are set, and held low when 26h, 28h or
    29h are non-zero.

INT0 dispatch (0x0030) reads status register D9h. Bit 0 → channel receive.
Bit 1 → host mailbox dispatch at 0x00B3, which branches on status register
DFh: bit 4 → status read, bit 3 → debug monitor, bit 5 → start command,
bits 2 and 7 → writes to E4h/E5h.

### 2. Eight channels (external registers E0h–EFh, F0h–F7h)

- A command byte arrives per channel at F0h+n: 7 bits plus even parity,
  delivered via INT0. It is stored in internal RAM at 37h+n.
- Two readings per channel at E0h+2n and E1h+2n: 7 bits plus odd parity. Both
  are read twice in a row (`MOVX A,@R1` twice).
- Each accepted command flips that channel's bit in 77h, which is written to
  FBh. Commands 15h and 16h don't flip it. Function not proven: handshake
  line or indicator.
- Per-channel state for the main loop's state machine is at 2Fh+n (initial
  state 45h). Per-channel timeout counters are at 3Fh+n.

### 3. Link controller chip (DPTR 0000h–000Ah)

Part number unknown.

- Reset pulse comes from P3.3.
- Two ways in: direct registers, plus an indirect register file.

| Register | Use |
|---|---|
| 1 | Status. Bit 4 = ready for a new message. Polled up to 100 times after command 04h (0x0584). |
| 2 | Write: indirect index and command. Read: bit 7 = data available (polled up to 200 times, 0x2F41). |
| 3 | Command. 04h = prepare to send, 01h = send, 08h = other. |
| 7 | Indirect data port. |
| 8 | Message FIFO (data in and out). |
| 0Ah | Destination: 30h+n, or n. |

- **Indirect write:** data to reg 7, then the index to reg 2 with bit 7 set.
- **Indirect read:** the index with bit 3 set to reg 2, then read reg 7.
- **Setup (0x08BC):**
  - Config C2h←28h, C3h←01h, C4h←37h.
  - Table 80h–87h ← 81h–88h.
  - Table A0h–A7h ← 97h, 80h–86h.
  - Every value is read back. Any mismatch goes to the 0x0CBE error path.
- **Sending:** command 04h and wait for ready, write bytes into the FIFO at
  reg 8, write the destination to reg 0Ah, then command 01h to reg 3.
- Timeouts set error flags 21h.2 and 24h.3.
- There is a loopback test that fills the FIFO with 55h/AAh and reads it back
  (0x0DA8–0x0DEF).

Writes to external register E3h appear 35 times, between steps of long
operations. They are most likely watchdog kicks.

## Message types

First byte of each message sent through the link controller:

| First byte | Data bytes | Notes |
|---|---|---|
| 03/43, 0B/4B, 13/53, 18/58, 23/63, 2B/6B | varies | Pairs differ only in bit 6 |
| 06, 26, 66 | 2, 2, 0 | Variants differ in bits 5–6 |
| 27 | 1 | |
| 30 | 4 | Channel readings (see below) |

At startup each channel gets `26 04 88` and `66`, and the firmware expects
`66 04` back.

## Command 2xh: read the channel

- Bits 4–6 = 010 means a data request (`(cmd & 70h) == 20h`).
- The reply has five bytes, built at 0x0F7C:

  ```
  30 | value(E1h+2n) hi lo | value(E0h+2n) hi lo
  ```

  It goes to destination 30h+n.
- A parity failure puts `11 2B` in place of that value.
- Each 7-bit reading goes through a lookup table: 128 entries of 2 bytes,
  held in 4 tables at 0x31A7, 0x32A7, 0x33A7 and 0x34A7.
- The tables join into one monotonic curve of about 360 entries. 0x31A7 and
  0x32A7 are contiguous. 0x33A7 starts 110 entries before 0x31A7's first
  entry, and 0x34A7 starts 18 entries after it.
- Command bits 0 and 1 choose the starting offset: 0 or +128 for the first
  reading, −110 or +18 for the second. In effect each bit selects one of two
  ranges.
- Entries 251–255 hold a sentinel value, `17 0B` (out of range).
- So the controller converts raw 7-bit samples into a calibrated quantity
  before forwarding them. That points to sensor or control values, not text.

## Encoding of the table values: unresolved

- The low nibble of byte 0 takes only the values 0–4 and steps down along the
  curve, like an exponent or range.
- The high nibble of byte 0 counts cleanly if each nibble is decoded as
  `x ≥ 8 ? x − 8 : 15 − x`. That gives the order 8, 9, A–F, 7, 6 … 0. Only 13
  small glitches remain, at boundaries.
- Byte 1 reverses direction depending on its own low nibble, which looks like
  a reflected code.
- 8 decodings tested, none monotonic:
  - plain binary under all 8-bit permutations;
  - Gray code under all bit orders and XOR masks;
  - signed-digit forms;
  - reflected mixed-radix forms.

  The best still had 46 out-of-order steps.
- Leading hypothesis: two fields, a coarse range/mantissa plus a signed fine
  correction. It could also be a native format of the receiving equipment.

## Other tables

| Address | Contents |
|---|---|
| 0x308F | 256-byte bit-reverse table |
| 0x318E | Channel bit masks: `FF 01 02 04 08 10 20 40 80` (indexed 0–8) |
| 0x3196 | Inverted channel masks: `80 FE FD FB F7 EF DF BF 7F` |
| 0x36C2 | Inverted bit masks: `FE FD FB F7 EF DF BF 7F` |
| 0x1791 | Jump table of 35 `LJMP`s: per-channel state machine (dispatcher at 0x178D, `JMP @A+DPTR` at 0x1790) |

## Other routines

- **Startup (0x10E8):** clears external registers FCh and FBh, sets SP = DFh.
  Init at 0x0654 reads reset-cause registers D9h and DFh and clears internal
  RAM. Verifies the ROM checksum. A periodic ROM recheck runs at 0x07EE.
- **Timer ISR (0x0637):** Timer 2 with RCAP2 = FE80h. Drives a chain of
  decimal counters.
- **DIP switches:** P1 is read while P3.0 and P3.1 are pulsed. Likely
  configuration switches.

## Corrections to earlier claims

- The message first bytes are types that come in variants (see table above).
  Calling this "3-bit type + 4-bit code" was wrong.
- Commands 15h and 16h are not discarded. They are processed but don't flip
  the channel bit.
- The constants 01h, 02h and 04h in comparisons are mostly compared against
  per-channel state variables, not received characters. They are not
  evidence of ASCII control characters (STX/EOT).

## Assessment

The firmware converts 8 channels of 7-bit readings into calibrated values and
sends them as addressed messages. It is set up by, and reports status to, a
host processor, which has full peek/poke debug access. It is a data-acquisition
or control front end. Text-serial is ruled out. Music/MIDI is unlikely: there
are no MIDI status bytes and the data has parity.

Every register role in this document is inferred from how the code uses it.
The chips on the original board would settle most open questions, the link
controller's part number above all.

## Tools

- `tools/dis51.py`: a minimal recursive-descent 8051 disassembler. Extra entry
  points (hex) follow the ROM path. To include the 0x1791 jump table and the
  0x00CB mailbox jump table:

  ```
  python3 tools/dis51.py romdump.bin 35A7 05A4 05E5 05F1 05EB 062E \
    $(python3 -c "print(' '.join(f'{0x1791+3*i:04X}' for i in range(35)))") \
    > rom.lst
  ```
