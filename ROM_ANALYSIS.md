# MSM83C154 Mask ROM Analysis

Analysis of the 16 KB internal mask ROM dumped from an OKI MSM83C154
(8051-family) microcontroller. The dump is `romdump.bin` (16384 bytes, internal
checksum verified).

## The chip

Markings:

```
79X1396
M83C154-42
©OKI '80/85
JAPAN 94000
```

| Line | Reading | Confidence |
|---|---|---|
| `79X1396` | The equipment maker's own part number. Mask-ROM chips are often marked with the customer's number. The `79X` prefix doesn't match any scheme found online. | Medium |
| `M83C154-42` | OKI MSM83C154 with ROM code 42: the number OKI gave this customer program. Based on OKI's suffix pattern; nothing confirms "-42" itself. | Medium |
| `©OKI '80/85` | Standard OKI copyright line, not a date code. '80 likely refers to the MCS-51 architecture, '85 to OKI's CMOS version. | Medium |
| `JAPAN 94000` | Probably date and lot. OKI's format isn't documented online. Most plausible: 1994, or 1989/1999 with a month and lot number. | Low |

Neither `79X1396` nor `M83C154-42` appears anywhere online (searched
2026-11-23). The markings show the chip was made for one company's product
under its own part number. If 94 is the year, it is late for a mask-ROM 8051,
which would suggest a mature, long-running product.

Custom OKI MSM83C154s did turn up in communications equipment: a Hayes modem
used one
([listing](https://www.electronicsurplus.com/oki-msm83c154-ic-hayes-copyright-p-n-04-00119-v2-5)).
This chip is marked differently, so that is not evidence of a Hayes
connection.

OKI's 1986 and 1988 microcontroller data books may explain the marking and
date-code layout:
[1986](https://bitsavers.trailing-edge.com/components/oki/_dataBooks/1986_OKI_Microcontroller.pdf),
[1988](https://bitsavers.trailing-edge.com/components/oki/_dataBooks/1988_OKI_Microcontroller_Data_Book.pdf).

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
  - In debug mode the main poll keeps polling channels and kicking the
    watchdog but never returns to the background loop, so the self-test is
    suspended. Status reporting and the P3.5 health output also stop.
- **Health output (P3.5):** outside debug mode, every 100 passes of the main
  poll (0x1751), status byte 21h is sent to FDh and P3.5 is updated: low when
  26h, 28h or 29h are non-zero, toggling while error flags 21h.1 or 21h.2 are
  set, otherwise high.

INT0 dispatch (0x0030) reads status register D9h. Bit 0 → channel receive.
Bit 1 → host mailbox dispatch at 0x00B2, which branches on status register
DFh: bit 4 → channel command (from FCh, 0x00DA), bit 2 → status read,
bit 3 → debug monitor, bit 5 → start command, bits 6 and 7 → writes to
E4h/E5h.

### 2. Eight channels (external registers E0h–EFh, F0h–F7h)

- A command byte arrives per channel at F0h+n: 7 bits plus odd parity,
  delivered via INT0. It is stored in internal RAM at 37h+n.
- Two readings per channel at E0h+2n and E1h+2n: 7 bits plus odd parity. Both
  are read twice in a row (`MOVX A,@R1` twice).
- Each accepted command flips that channel's bit in 77h, which is written to
  FBh. Commands 15h and 16h don't flip it. Function not proven: handshake
  line or indicator.
- Per-channel state for the main loop's state machine is at 2Fh+n (initial
  state 45h). A per-channel status code is at 3Fh+n: set to values 01h–13h
  and compared, never counted down. Further per-channel bytes are at 48h+,
  50h+, 58h+, 60h+ and 68h+ (n−1).

### 3. Link controller chip (DPTR 0000h–000Ah)

Part number unknown.

- Reset pulse comes from P3.3.
- Two ways in: direct registers, plus an indirect register file.

| Register | Use |
|---|---|
| 1 | Status. Bit 4 = ready for a new message. Polled up to 100 times after command 04h (0x0584). |
| 2 | Write: indirect register number; bit 3 set = select for reading. Read: bit 7 = ready for an indirect access (polled up to 200 times, 0x2F41). |
| 3 | Command. 04h = prepare to send, 01h = send, 08h = other. |
| 7 | Indirect data port. |
| 8 | Message FIFO (data in and out). |
| 0Ah | Destination: 30h+n, or n. |

- **Indirect write:** data to reg 7, then the register number to reg 2.
  Register numbers used: 10h–17h (per channel, 0x2F41), 80h–87h, A0h–A7h,
  C2h–C4h.
- **Indirect read:** the register number with bit 3 set to reg 2, then read
  reg 7.
- **Setup (0x08BC):**
  - Config C2h←28h, C3h←01h, C4h←37h.
  - Table 80h–87h ← 81h–88h.
  - Table A0h–A7h ← 97h, 80h–86h.
  - Every value is read back. Any mismatch goes to the 0x0CBE error path.
- **Sending:** command 04h and wait for ready, write bytes into the FIFO at
  reg 8, write the destination to reg 0Ah, then command 01h to reg 3.
- Link timeouts (no ready signal) set error flags 21h.2 and 24h.3.
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

Startup handshake (0x0BC2), per channel:
1. Indirect write C0h to register 10h+(n−1).
2. Send `26 04 88` to 30h+n−1.
3. Send `66` to n−1, and expect `66 04 88` back. The value written in step 2
   is read back.
4. Send `30 11 2B 11 2B` (readings invalid) to 30h+n−1.

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
- Command bits 0 and 1 choose the starting offset: bit 0 picks −110 (0x33A7)
  or +18 (0x34A7) for the first reading (E1h+2n), bit 1 picks 0 (0x31A7) or
  +128 (0x32A7) for the second (E0h+2n). In effect each bit selects one of two
  ranges.
- Entries 251–255 hold a sentinel value, `17 0B` (out of range).
- So the controller converts raw 7-bit samples into a calibrated quantity
  before forwarding them. That points to sensor or control values, not text.

## Encoding of the table values: logarithmic, decimal floating point

### The curve is logarithmic: 60 entries per decade

Comparing each entry with the one N entries further along, and counting exact
matches where only byte 0's low nibble differs (by 1):

| N | Exact matches |
|---|---|
| 58 | 0 |
| 59 | 0 |
| **60** | **70** |
| 61 | 3 |
| 62 | 0 |

- **Byte 0's low nibble is a decimal exponent.** It drops by 1 every 60
  entries while everything else stays the same: `2405 → 2305 → 2205`,
  `14AB → 13AB`, `D303 → D203`.
- **The mismatches are small and in the low digits.** That fits each decade
  being calculated separately and rounded.
- **Precision runs out at the bottom.** Once the exponent reaches 0 it can't
  drop further, so the values decay to small integers and then to `00 00`.
  That explains the plateaus at the end of the curve.
- **The values are decimal floating point:** a mantissa of about 3 digits, in
  an unusual nibble encoding, times 10 to the exponent. The value falls by a
  factor of 10 every 60 input counts.
- **Range:** the curve spans about 360 entries, so about 6 decades. One 7-bit
  reading covers about 2.1 decades. The two command bits move that window
  within the 6 decades.

So each raw reading is on a log scale, and the firmware turns it into an
engineering value of the form mantissa × 10ⁿ. In audio or RF terms, 60 counts
per decade is ⅓ dB per count for amplitude, or ⅙ dB per count for power.

### Mantissa digits: unresolved

- The low nibble of byte 0 takes only the values 0–4 and steps down along the
  curve: the exponent, above.
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
- With the exponent identified, only the 3 mantissa nibbles remain. If they
  decode to familiar values, the units may become obvious.

## Other tables

| Address | Contents |
|---|---|
| 0x308F | 256-byte bit-reverse table |
| 0x318E | Channel bit masks: `FF 01 02 04 08 10 20 40 80` (indexed 0–8) |
| 0x3196 | Inverted channel masks: `80 FE FD FB F7 EF DF BF 7F` |
| 0x36C2 | Inverted bit masks: `FE FD FB F7 EF DF BF 7F` |
| 0x1791 | Jump table of 35 `LJMP`s: per-channel state machine (dispatcher at 0x178D, `JMP @A+DPTR` at 0x1790). The state value is the byte offset into the table, so state = 3 × entry. States 4Eh–5Dh all go to 0x2CEC. |

## Other routines

- **Startup (0x10E8):** clears external registers FCh and FBh, sets SP = DFh.
  Init at 0x0654 reads the reset cause and records it in status byte 20h for
  the host: IRQ_STATUS (D9h) bit 2 → 08h, bit 3 → 04h, HOST_STATUS (DFh)
  bit 1 → 02h. IRQ_STATUS bit 4 reinitialises only the link and channels.
  Then it clears internal RAM, checksums the whole ROM (0x07E1), tests
  internal RAM, configures the link controller and starts Timer 2 and INT0.
- **Background self-test (0x1117):** between passes of the main poll, a
  rolling self-test runs:
  1. ROM checksum, 20 bytes per step.
  2. R0/R1 test.
  3. Internal RAM write/read test (FFh, 00h), 16 bytes per step.
  4. Internal RAM 80h–DFh checksum, compared with the first pass.
  5. Link controller config read-back.
  6. Link loopback test (0x13F3).
  7. Stack sentinel: internal RAM FFh must still be FFh.

  Failures set error bits in status bytes 21h, 22h and 24h for the host.
  Config byte bit 2 (flag 2Ah.7) skips the self-test entirely.
- **Per-channel records:** upper internal RAM 80h–DFh holds 8 records of 12
  bytes, one per channel (80h + 12(n−1)).
- **Timer ISR (0x0637):** Timer 2 with RCAP2 = FE80h (384 machine cycles per
  tick). Drives decimal counters at 10h–13h: every tick, 10, 100 and 1000
  ticks.
- **Per-channel input lines:** P1 is read while P3.1 (0x2DD2) or P3.0+P3.1
  (0x2DE4) is pulsed, then masked with the channel's bit. Two banks of 8
  per-channel inputs: switches or presence lines.

## Suspected firmware bug

In the state 45h handler, at 0x2C5C, the code computes `FFh + R7` (= n−1)
and writes 10h through it. That lands in internal RAM 00h–07h, the bank 0
registers, instead of the per-channel status code at 3Fh+n that the
equivalent code at 0x0788 uses. For channel 8 it overwrites R7, the channel
loop counter. It only runs on one path (command 07h received while the
channel is not faulty), which may be why it went unnoticed.

## Corrections to earlier claims

- The message first bytes are types that come in variants (see table above).
  Calling this "3-bit type + 4-bit code" was wrong.
- Commands 15h and 16h are not discarded. They are processed but don't flip
  the channel bit.
- The F0h–F7h command bytes use odd parity, not even. The check is
  `JNB P`: an even number of 1 bits is an error.
- Link register 2's bit 7 means "ready for an indirect access", not "data
  available". Bit 7 of a value written to reg 2 is part of the register
  number, not a write strobe.
- 3Fh+n holds a per-channel status code, not a timeout counter.
- Host mailbox dispatch bits were misassigned: DFh bit 4 is the channel
  command, bit 2 the status read.
- The P3.5 health output is not driven in debug mode. It is driven in
  normal operation. 0x2F41 waits for it, then writes R3 to indirect register
  10h+(n−1).
- The constants 01h, 02h and 04h in comparisons are mostly compared against
  per-channel state variables, not received characters. They are not
  evidence of ASCII control characters (STX/EOT).

## Assessment

The firmware converts 8 channels of 7-bit log-scale readings into decimal
floating-point values and sends them as addressed messages. It is set up by,
and reports status to, a host processor, which has full peek/poke debug
access. It is a data-acquisition front end. Text-serial is ruled out.
Music/MIDI is unlikely: there are no MIDI status bytes and the data has parity.

### What the design implies

| Feature | Implication |
|---|---|
| Six-decade log scale, decimal floating-point output | A physical quantity measured across decades |
| Two readings per channel, on different parts of the curve | Two related measurements, or two detectors/ranges per head |
| Sentinel for out of range, `11 2B` for "invalid" | The receiver displays or logs these values |
| Per channel: command byte, two readings, a configuration block with checksum, six device types | Smart remote sensor heads, not bare analog inputs |
| 7-bit odd parity everywhere, NAK (15h) and SYN (16h) handled specially | The heads talk to the board over ASCII-style asynchronous serial links |
| ROM checksum, RAM tests, watchdog, stack check, reset cause reported to the host | Built for high reliability. Unusual for consumer equipment |
| Host peek/poke debug monitor | Intelligent I/O card under a supervisory CPU, serviced in the field |
| Mask ROM, customer part number | Made in volume for one company's product |

### Hypotheses, most likely first

1. **Multi-channel monitoring concentrator for log-range instruments.**
   Candidates: radiation monitoring (dose-rate and count-rate meters commonly
   span 6 decades on a log scale), vacuum gauges (ion and Pirani gauges have
   log outputs spanning decades), or gas detection. Fits the heavy
   self-testing, the reset-cause reporting and decimal values for display.
   The two readings per channel would suit dose rate plus integrated dose, or
   two detector ranges.
2. **Audio or RF level system.** 60 counts per decade suits dB-to-linear
   conversion, and 8 channels is typical of a console or metering system.
   Against it: decimal floating point is an odd choice for gain coefficients,
   and the self-test effort seems more than a mixer would carry.
3. **Building or process control** (temperatures, setpoints). Least likely:
   those quantities don't span decades.

Confidence is moderate on the overall architecture and low on the specific
application.

### What would narrow it down

1. Original tubes or reels, labels, other parts with a `79X` prefix, or boards
   these chips came from.
2. Other chips in the same batch with a different `79Xnnnn` or `-nn` marking,
   meaning other ROM programs from the same maker.
3. The makerspace donor, who might know the employer or equipment.
4. OKI's data books, for the marking and date-code layout.
5. Decoding the mantissa nibbles.

Every register role in this document is inferred from how the code uses it.
The chips on the original board would settle most open questions, the link
controller's part number above all.

## Tools

- `romdump_annotated.lst`: annotated disassembly, generated by
  `python3 tools/annotate.py`. Names and comments come from
  `tools/romdump_annotations.py`. Register accesses, per-channel array
  pointers, channel mask lookups and state assignments are annotated
  automatically. Each state handler gets a summary of the states it sets and
  the routines it calls.
- `tools/dis51.py`: a minimal recursive-descent 8051 disassembler. Extra entry
  points (hex) follow the ROM path. To include the 0x1791 jump table and the
  0x00CB mailbox jump table:

  ```
  python3 tools/dis51.py romdump.bin 35A7 05A4 05E5 05F1 05EB 062E \
    $(python3 -c "print(' '.join(f'{0x1791+3*i:04X}' for i in range(35)))") \
    > rom.lst
  ```
