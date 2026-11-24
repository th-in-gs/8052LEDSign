# MSM83C154 Mask ROM Analysis

Analysis of the 16 KB internal mask ROM dumped from an OKI MSM83C154
(8051-family) microcontroller. The dump is `romdump.bin` (16384 bytes, internal
checksum verified).

Every register role in this document is inferred from how the code uses it.

**Notation.** Channels are numbered n = 1..8, matching register R7 in the
code. Addresses are written the way the code computes them, so channel n's
command register is EFh+n (F0h–F7h for channels 1–8).

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
| `79X1396` | Either the equipment maker's own part number (mask-ROM chips are often marked with the customer's number) or an OKI customer/lot code. The `79X` prefix doesn't match any scheme found online. | Low |
| `M83C154-42` | OKI MSM83C154, mask code 42. Consistent with OKI's `MSM83C154-xxx` ordering code, where xxx is the mask code. The package suffix is not marked. | Medium |
| `©OKI '80/85` | Copyright line, not a date code. The years may refer to the MCS-51 architecture and OKI's CMOS version, or may simply be copyright years. | Low |
| `JAPAN 94000` | Probably date and lot. OKI's format isn't documented online. 1994 is plausible, but the fifth digit makes "date + lot" safer than a specific month. | Low |

No datasheet or independent part listing mentions `79X1396` or
`M83C154-42` (searched 2026-11-23). The markings suggest the chip was made
for one company's product. If 94 is the year, it is late for a mask-ROM 8051,
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

OKI's user manual describes EA as sampled at reset. In practice, on this chip,
raising EA after reset made MOVC read the internal ROM: the dump succeeded and
its internal checksum matches. Treat this as observed behaviour of this part,
not a datasheet guarantee.

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
| ROM checksum | 16-bit sum of 0x0000–0x3FFC = 0x45B9, stored at 0x3FFE–0x3FFF as `B9 45` |
| Config byte | 0x3FFD (00h in this dump) |
| ASCII strings | None |
| Code reached by recursive disassembly | 12,685 of 16,384 bytes |
| Unused | 0x36CA–0x3FFC (zero-filled) |

The 8052's hardware UART is not used: there are no SBUF or SCON accesses.
P3.0 and P3.1 are used as general-purpose outputs.

## The hardware the firmware talks to

The 8052 is an I/O controller sitting under a larger host computer. Almost
everything it does goes through **other chips on its external bus**, which
were on the original board but are not part of this dump.

### Memory-mapped peripherals

On an 8051, `MOVX` instructions read and write *external data memory*: the
CPU puts an address on P0/P2, pulses RD or WR, and moves a byte over P0. The
CPU cannot tell RAM from anything else at those addresses. Address-decoding
logic on the board decides which chip answers, so peripheral chips can be
placed in this space, each register at its own address.

This firmware runs from internal ROM and uses no external RAM. Every `MOVX`
in it is a peripheral access. There are two regions:

| Region | Accessed with | What is there (inferred) |
|---|---|---|
| FFD9h–FFFFh | `MOVX @R0/@R1`, with P2 at its reset value FFh (normal code never changes P2) | **Channel/host interface.** Status registers (D9h, DAh, DEh, DFh), the per-channel data window (E0h–EFh), channel command bytes (F0h–F7h), the host mailbox (F8h–FFh), and write-only controls such as the watchdog (E3h). Possibly several chips separated by address decoding. |
| 0000h–000Ah | `MOVX @DPTR`, with DPH = 00h | **Link controller.** Status, command, indirect index and data, message FIFO, destination. |

The same hardware interrupts the CPU on INT0. IRQ_STATUS (D9h) and
HOST_STATUS (DFh) say which part needs attention.

```
 Original board (inferred)

         ┌─────────────────────────────┐
         │ OKI MSM83C154               │
         │ (code in internal ROM)      │
         └──────────────┬──────────────┘
                        │ P0/P2 bus, RD/WR
         ┌──────────────┴──────────────┐
         │ address decode              │
         └────┬───────────────────┬────┘
        FFxxh │                   │ 0000h
 ┌────────────▼─────────┐ ┌───────▼─────────────┐
 │ channel/host         │ │ link controller     │
 │ interface            │ │ 0000h–000Ah         │
 │ FFD9h–FFFFh          │ │                     │
 │ (drives INT0)        │ │                     │
 └──┬────────────┬──────┘ └──────────┬──────────┘
    │            │                   │
 host        8 channels          network / link
 computer    (sensor heads)
```

None of these chips has been identified. Clues about their nature:

- **Every read is done twice** (`MOVX A,@R1` twice in a row). That is
  typical of a slow peripheral, or one where the first read latches the
  value and the second returns it. It suggests a custom gate array or older
  NMOS peripherals rather than RAM.
- **Reads and writes at the same address often reach different
  registers.** For example, FBh reads the host's debug command but writes
  the channel toggle bits. Typical of peripheral chips and latches.
- **The host mailbox** may be a dual-port RAM or mailbox chip shared with the
  host CPU, fitting an I/O card in a larger machine.
- **The link controller** has a message FIFO behind one register, indirect
  registers and command codes: a dedicated network or serial-link chip. Its
  register map is the strongest fingerprint for identifying the equipment.

### What this means on the dumping breadboard

On the LED-sign breadboard, all external data space is the SRAM, so these
"peripheral" accesses would simply land in RAM. That is why the dump works:
the dumper uses `MOVX` writes to copy the ROM into SRAM. It also means the
OKI firmware cannot do its real job on that board: the channel/host chips
and the link controller would have to be emulated. By contrast, the
Signetics SCN8031H program (`scn8031/`) uses no `MOVX` at all; everything it
controls is wired to its port pins.

The three interfaces in detail:

### 1. Host mailbox (FFF8h–FFFFh)

- **Status reads.** The host writes an internal-RAM address to FAh. Firmware
  returns that byte at F8h and echoes the address at F9h. Flag bytes 20h–25h
  and 2Eh clear when read (21h is masked with C1h), so they are host-visible
  error and status registers. Handler: 0x05A4.
- **Start command** (0x05F1). The host writes 01h to FDh. Firmware:
  - sets flags 20h.0 and 21h.3;
  - clears 1Eh and 77h, and writes 00h to FBh;
  - for each channel, sets its bit in CH_ACTIVE (2Dh) if its status code at
    3Fh+n is not 01h, and in 1Dh if the code is 10h;
  - writes status byte 21h to FDh, then recomputes the per-channel status.
- **Debug monitor** (0x35A7–0x36C1):
  - Entry: host writes FCh to FBh. Firmware answers FCh at FAh and sets flag
    2Ah.1.
  - Exit: host writes FAh.
  - Command 8xh writes and Axh reads. Bits 0–3 pick the target:

    | Bit | Target |
    |---|---|
    | 0 | Internal RAM through `@R0` (00h–FFh; not the SFRs) |
    | 1 | External RAM (`MOVX @R0`, page set by P2) |
    | 2 | Link controller register (`MOVX @DPTR`, DPH = 00h) |
    | 3 | Port: P1, P2 or P3 (address < 2, = 2, > 2) |

    SFRs other than the ports, and program memory, are not reachable.
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

### 2. Eight channels (E0h–EFh, F0h–F7h)

- A command byte arrives for channel n at EFh+n (F0h–F7h): 7 bits plus odd
  parity, delivered via INT0. It is stored in internal RAM at 37h+n.
- Two readings per channel at E0h+2(n−1) and E1h+2(n−1): 7 bits plus odd
  parity. Both are read twice in a row (`MOVX A,@R1` twice).
- E0h–EFh is also read as a configuration block: a mode/type byte at E0h,
  data from E1h, and a checksum (see below). Normal code never changes P2,
  so how one window serves both uses is not explained by the ROM.
- Each accepted command flips that channel's bit in 77h, which is written to
  FBh. Commands 15h and 16h don't flip it. Function not proven: handshake
  line or indicator.
- Per-channel state for the main loop's state machine is at 2Fh+n (initial
  state 45h). A per-channel status code is at 3Fh+n: set to values 01h–13h
  and compared, never counted down. Further per-channel bytes are at 47h+n,
  4Fh+n, 57h+n, 5Fh+n and 67h+n.

#### Channel records

Upper internal RAM 80h–DFh holds a 12-byte record per channel, at
80h + 12(n−1). `check_window_block` (0x2E34–0x2E6D) fills it from the
configuration block, shifting bit fields down to the low bits:

| Offset | Contents |
|---|---|
| +0 | WIN_E0 bits 6–4 (type, 0–7) |
| +1 | WIN_E0 bits 3–0 |
| +2..+7 | WIN_E1..E6 |
| +8 | WIN_E7 bits 5–4 |
| +9 | WIN_E8 bits 7–6 |
| +A | WIN_E8 bits 5–4 |
| +B | WIN_E9 |

WIN_E0 bit 7 is not stored; MSG_FLAGS (74h) bit 7 is set to its inverse
instead (0x021D). WIN_E0 bit 6 selects MSG_PARAM (19h): 06h if set, 04h if
clear. The state
45h handler tests record byte 0 bit 2 (WIN_E0 bit 6) and record byte A == 2.

#### Checksum conventions

- `send_window_block` (0x04DA) sends E1h..E8h; `check_window_checksum`
  (0x0504) then requires sum(E1h..E8h) + E9h + 1 = 0, i.e. E9h is the one's
  complement of the sum. The type 3 path (0x0342) does the same with E1h..E4h
  and the checksum at E5h.
- `check_window_block` (0x2DFA) sums E0h..E8h (types 1 and 2) or E0h..EAh
  (other types) and expects FFh.
- `receive_and_checksum` (0x052F) reads the message type byte, then R6 data
  bytes, adds them to R2, then adds the local checksum byte and 1 and expects
  zero. The starting values come from the caller.

### 3. Link controller chip (0000h–000Ah)

Part number unknown.

- Reset pulse comes from P3.3.
- Two ways in: direct registers, plus an indirect register file.

| Register | Use |
|---|---|
| 1 | Status. Bit 4 = ready for a new message (polled up to 100 times after command 04h, 0x0584). Bit 6 = message received (polled in 0x052F). |
| 2 | Write: indirect register number; bit 3 set = select for reading. Read: bit 7 = ready for an indirect access (polled up to 200 times, 0x2F41). |
| 3 | Command. 04h = prepare to send, 01h = send, 08h = release receive buffer. |
| 7 | Indirect data port. |
| 8 | Message FIFO (data in and out). |
| 0Ah | Destination: 2Fh+n (30h–37h) or FFh+n (= n−1, 00h–07h). |

- **Indirect write:** data to reg 7, then the register number to reg 2.
  Register numbers used: 10h–17h (per channel, 0x2F41), 30h–37h (warm
  init, 0x06DF), 80h–87h, A0h–A7h, C2h–C4h.
- **Indirect read:** the register number with bit 3 set to reg 2, then read
  reg 7.
- **Setup (0x08BC):**
  - Config C2h←28h, C4h←37h.
  - Table 80h–87h ← 81h–88h.
  - Table A0h–A7h ← 97h, 80h–86h.
  - C3h←01h.
  - C2h, C3h, 80h–87h and A0h–A7h are read back; C4h is not. Any mismatch
    goes to the 0x0CBE error path.
- **Sending:** command 04h and wait for ready, write bytes into the FIFO at
  reg 8, write the destination to reg 0Ah, then command 01h to reg 3.
- Link timeouts (no ready signal) set error flags 21h.2 and 24h.3.
- There is a loopback test that fills the FIFO with 55h/AAh and reads it back
  (0x0DA8–0x0DEF).

Writes to external register E3h appear 37 times (35 through `@R1`, 2 through
`@R0`), between steps of long operations. They are most likely watchdog
kicks.

## Message types

First byte of each message sent through the link controller:

| First byte | Data bytes | Notes |
|---|---|---|
| 03/43, 0B/4B, 13/53, 18/58, 23/63, 2B/6B | varies | Pairs differ only in bit 6. The first of each pair carries the configuration block: E1h..E8h, or E1h..E4h for 18h. |
| 06, 26, 66 | 2, 2, 0 | Variants differ in bits 5–6 |
| 27 | 1 | |
| 30 | 4 (6 in one error case) | Channel readings (see below) |

Startup handshake (0x0BC2), per channel:
1. Indirect write C0h to register 10h+(n−1).
2. Send `26 04 88` to 2Fh+n.
3. Send `66` to FFh+n (= n−1), and expect `66 04 88` back. The value written
   in step 2 is read back.
4. Send `30 11 2B 11 2B` (readings invalid) to 2Fh+n.

## Command 2xh: read the channel

- Bits 4–6 = 010 means a data request (`(cmd & 70h) == 20h`).
- The reply is built at 0x0F7C:

  ```
  30 | value(E1h+2(n−1)) hi lo | value(E0h+2(n−1)) hi lo
  ```

  It goes to destination 2Fh+n.
- A parity failure depends on which reading fails:
  - **First reading** (0x0F91): only `30` has been written, so the message is
    `30 11 2B 11 2B`, 5 bytes. Both values are invalidated.
  - **Second reading** (0x1002): the first value's two bytes are already in
    the FIFO. 0x1005 jumps to the same handler, which appends four bytes:
    `30 hh ll 11 2B 11 2B`, 7 bytes. See "Suspected firmware bugs".
- Each 7-bit reading goes through a lookup table: 128 entries of 2 bytes,
  held in 4 tables at 0x31A7, 0x32A7, 0x33A7 and 0x34A7.
- The tables join into one monotonic curve of about 360 entries. 0x31A7 and
  0x32A7 are contiguous. 0x33A7 starts 110 entries before 0x31A7's first
  entry, and 0x34A7 starts 18 entries after it.
- Command bits 0 and 1 choose the starting offset: bit 0 picks −110 (0x33A7)
  or +18 (0x34A7) for the first reading (E1h+2(n−1)), bit 1 picks 0 (0x31A7)
  or +128 (0x32A7) for the second (E0h+2(n−1)). In effect each bit selects
  one of two ranges.
- Entries 251–255 hold a sentinel value, `17 0B` (out of range).
- So the controller converts raw 7-bit samples into a calibrated quantity
  before forwarding them. That points to sensor or control values, not text.

## Encoding of the table values

Summary: a 4-bit decimal exponent plus a 12-bit mantissa. The mantissa
encoding is unresolved.

### Byte 0's low nibble: a decimal exponent, 60 entries per decade

Comparing each entry with the one N entries further along, and counting exact
matches where only byte 0's low nibble differs (by 1), out of about 300
positions:

| N | Exact matches |
|---|---|
| 58 | 0 |
| 59 | 0 |
| **60** | **70** |
| 61 | 3 |
| 62 | 0 |

- The low nibble takes only the values 0–4. It drops by 1 every 60 entries,
  at curve positions −96, −35, 25 and 85, and in 70 cases everything else
  stays the same: `2405 → 2305 → 2205`, `14AB → 13AB`, `D303 → D203`.
- The exact matches are mostly in the upper part of the curve. Many
  mismatches are large: position 10 is `22 05` but position 70 is `21 A4`.
  So the mantissa does not simply repeat each decade. It may be a
  calibration curve, an inexact log table, or a binary fraction with a
  nonstandard bit order.
- Once the exponent reaches 0 it can't drop further, so the values decay to
  small integers and then to `00 00`. That explains the plateaus at the end
  of the curve.
- The curve spans about 360 entries, so about 6 decades. One 7-bit reading
  covers about 2.1 decades. The two command bits move that window within the
  6 decades.

So each raw reading appears to be on a log scale, and the firmware turns it
into a value with a decimal exponent. In audio or RF terms, 60 counts per
decade is ⅓ dB per count for amplitude, or ⅙ dB per count for power.

### A second landmark: the A–F → 7 wrap

The high nibble of byte 0 runs through the codes A–F, then 7 down to 1. The
wrap from A–F to the 0–7 codes also recurs every 60 entries, at positions
−70, −10, 50 and 110, 25–26 entries after each exponent change. So each
60-entry cycle has two fixed landmarks. The split between codes A–F and
0–7 is part of the number's structure.

### Two anomalies

- Position −70 (0x33A7 entry 40): `14 01`, exponent 4 between neighbours
  with exponent 3 (`E30A → 1401 → 7301`).
- Position 110 (0x31A7 entry 110, also 0x34A7 entry 92): `11 01`, exponent 1
  between neighbours with exponent 0 (`E00B → 1101 → 600B`).

Both sit exactly on the A–F → 7 wrap, 180 entries (3 × 60) apart, with the
same shape. The other two wraps (−10, 50) have no such entry. They look like
a renormalisation carry or a deliberate special code, not table defects. A
test: decode the values either side. If `1x01` is 1.0 × 10^(e+1) and its
neighbours are about 9.99 × 10^e, it is a carry.

### Mantissa: unresolved

- The high nibble of byte 0 counts cleanly if each nibble is decoded as
  `x ≥ 8 ? x − 8 : 15 − x`. That gives the order 8, 9, A–F, 7, 6 … 0. Only 13
  small glitches remain, at boundaries.
- Byte 1 reverses direction depending on its own low nibble, which looks like
  a reflected code.
- None of these produced a monotonic 12-bit value (also checked
  independently by a reviewer):
  - plain binary under all 8-bit permutations;
  - Gray code under all bit orders and XOR masks;
  - signed-digit forms;
  - reflected mixed-radix forms;
  - the transform above applied to all three nibbles.

  The best still had 46 out-of-order steps.
- Next idea: decode the mantissa as a binary or log fraction rather than
  decimal digits.

## Other tables

| Address | Contents |
|---|---|
| 0x318E | Channel bit masks: `FF 01 02 04 08 10 20 40 80` (indexed 0–8) |
| 0x3196 | Inverted channel masks: `80 FE FD FB F7 EF DF BF 7F` (shares its first byte with 0x318E) |
| 0x1791 | Jump table of 35 `LJMP`s: per-channel state machine (dispatcher at 0x178D, `JMP @A+DPTR` at 0x1790). The state value is the byte offset into the table, so state = 3 × entry. States 4Eh–5Dh all go to 0x2CEC. |

Unreferenced: nothing in the code points at these (no DPTR setup, no
`MOVC A,@A+PC`). They may be leftovers, or data for something not in this ROM.

| Address | Contents |
|---|---|
| 0x308F | 256-byte bit-reverse table |
| 0x319F | `03 03 0C 0C 30 30 C0 C0` |
| 0x36C2 | Inverted bit masks: `FE FD FB F7 EF DF BF 7F` |

## Other routines

- **Startup (0x10E8):** clears external registers FCh and FBh, sets SP = DFh.
  Init at 0x0654 reads the reset cause and records it in status byte 20h for
  the host: IRQ_STATUS (D9h) bit 2 → 08h, bit 3 → 04h, HOST_STATUS (DFh)
  bit 1 → 02h. IRQ_STATUS bit 4 reinitialises only the link and channels.
  Then it clears internal RAM, checksums the whole ROM (0x07E1), tests
  internal RAM, configures the link controller and starts Timer 2 and INT0.
- **Background self-test (0x1117):** between runs of the main poll, a
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
- **Timer ISR (0x0637):** Timer 2 with RCAP2 = FE80h (384 machine cycles per
  tick). Drives decimal counters at 10h–13h: every tick, 10, 100 and 1000
  ticks.
- **Per-channel input lines:** P1 is read while P3.1 (0x2DD2) or P3.0+P3.1
  (0x2DE4) is pulsed, then masked with the channel's bit. Two banks of 8
  per-channel inputs: switches or presence lines.

## Suspected firmware bugs

1. **Write to a bank 0 register (0x2C5C).** In the state 45h handler, the
   code computes `FFh + R7` (= n−1) and writes 10h through it. That lands in
   internal RAM 00h–07h, the bank 0 registers, instead of the per-channel
   status code at 3Fh+n that the equivalent code at 0x0788–0x07A6 uses. For
   channel 8 it overwrites R7, the channel loop counter. It only runs on one
   path (command 07h received while the channel is not faulty), which may be
   why it went unnoticed.
2. **7-byte readings message (0x1005).** When the second reading fails its
   parity check, the first value has already been written, and the error
   handler appends four more bytes (see "Command 2xh"). 0x1005 should
   probably go to a path that writes only `11 2B`. Whether this breaks the
   receiver depends on whether it treats `30` as a fixed 5-byte message,
   which can't be told without the link controller's datasheet. Probable,
   not certain.

## Corrections to earlier claims

- The message first bytes are types that come in variants (see table above).
  Calling this "3-bit type + 4-bit code" was wrong.
- Commands 15h and 16h are not discarded. They are processed but don't flip
  the channel bit.
- The F0h–F7h command bytes use odd parity, not even. The check is
  `JNB P`: an even number of 1 bits is an error.
- Link register 2's bit 7 means "ready for an indirect access", not "data
  available". Bit 7 of a value written to reg 2 is part of the register
  number, not a write strobe. 0x2F41 waits for it, then writes R3 to indirect
  register 10h+(n−1).
- 3Fh+n holds a per-channel status code, not a timeout counter.
- Host mailbox dispatch bits were misassigned: DFh bit 4 is the channel
  command, bit 2 the status read.
- The P3.5 health output is not driven in debug mode. It is driven in
  normal operation.
- The constants 01h, 02h and 04h in comparisons are mostly compared against
  per-channel state variables, not received characters. They are not
  evidence of ASCII control characters (STX/EOT). The same applies to 15h and
  16h: calling them NAK and SYN was unfounded.
- Channel addresses were written inconsistently, sometimes as if n were
  0-based. They now use n = 1..8 throughout.
- A parity failure does not simply replace the failing value; the result
  depends on which reading fails.
- The "decimal floating point" claim was too strong. The exponent is solid;
  the mantissa encoding is not.

## Assessment

The firmware converts 8 channels of 7-bit readings, apparently on a log
scale, into values with a decimal exponent and sends them as addressed
messages. It is set up by, and reports status to, a host processor, which
has debug read/write access to RAM, the link controller and the ports. It is
a data-acquisition front end. Text-serial is ruled out. Music/MIDI is
unlikely: there are no MIDI status bytes and the data has parity.

### What the design implies

| Feature | Implication |
|---|---|
| Six-decade log scale, decimal exponent | A physical quantity measured across decades |
| Two readings per channel, on different parts of the curve | Two related measurements, or two detectors/ranges per head |
| Sentinel for out of range, `11 2B` for "invalid" | The receiver displays or logs these values |
| Per channel: command byte, two readings, a configuration block with checksum, six device types | Smart remote sensor heads, not bare analog inputs |
| 7-bit data plus odd parity on all channel bytes | Consistent with a serial-style link to each head |
| ROM checksum, RAM tests, watchdog, stack check, reset cause reported to the host | Built for high reliability. Unusual for consumer equipment |
| Host debug monitor | Intelligent I/O card under a supervisory CPU, serviced in the field |
| Mask ROM, custom marking | Made in volume for one company's product |

### Hypotheses, most likely first

1. **Multi-channel monitoring concentrator for log-range instruments.**
   Candidates: radiation monitoring (dose-rate and count-rate meters commonly
   span 6 decades on a log scale), vacuum gauges (ion and Pirani gauges have
   log outputs spanning decades), or gas detection. Fits the heavy
   self-testing, the reset-cause reporting and values for display. The two
   readings per channel would suit rate plus dose, ion plus Pirani, or
   measurement plus reference.
2. **Optical photometry or densitometry.** A 6-decade log response with
   sample/reference pairs fits the two readings sitting on different parts of
   the curve, plus per-head calibration and decimal output.
3. **RF or audio level monitoring.** 60 counts per decade suits dB-to-linear
   conversion. Two readings per channel fit forward/reflected power, peak/RMS,
   or two detector ranges, for example in a broadcast transmitter monitor.
   Against it: a decimal exponent is an odd choice for gain coefficients, and
   the self-test effort is less typical of audio.
4. **Telephone/PBX line monitoring.** 8 lines, two readings, per-line types.
   Weak: line voltage and current don't span six decades, which is the
   strongest single clue in the ROM.
5. **Building or process control** (temperatures, setpoints). Least likely:
   those quantities don't span decades.

Confidence is moderate on the overall architecture and low on the specific
application. The most distinctive clue after the log scale is the
configuration block with checksum and six device types: a smart sensor head
being configured and read back.

### What would narrow it down

1. Original tubes or reels, labels, other parts with a `79X` prefix, or boards
   these chips came from. On a board, identify the link controller first: its
   register map is the strongest fingerprint for the equipment family.
2. Other chips in the same batch with a different `79Xnnnn` or `-nn` marking,
   meaning other ROM programs from the same maker.
3. The makerspace donor, who might know the employer or equipment.
4. OKI's data books, for the marking and date-code layout.
5. Decoding the mantissa, and the two anomalies.

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
