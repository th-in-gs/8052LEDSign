# MSM83C154 Mask ROM Analysis

Analysis of the 16 KB internal mask ROM dumped from an OKI MSM83C154
(8051-family) microcontroller. The dump is `romdump.bin` (16384 bytes, internal
checksum verified).

Everything this document says about what an address or variable is for is
inferred from how the code uses it.

## Background: the 8051 for modern programmers

The 8051 is Intel's 1980 8-bit microcontroller design, still made in many
variants. A few of its features differ from what most programmers today
expect.

### Notation in this document

- **Hex** is written `0xFF`. 8051 assemblers and the generated listings use
  the older `FFh` form for the same thing.
- **Byte sequences** (message contents, table entries) are written as
  space-separated hex in code font, without prefixes: `30 11 2B`.
- **Bit numbers** count from 0, the least significant bit. `0x21.3` means bit
  3 of internal RAM byte 0x21.
- **Code addresses** in parentheses, such as (0x05A4), point to the routine
  that does what is being described. They are locations in the ROM and can
  be looked up in `romdump_annotated.lst`.
- **Channels** are numbered n = 1..8, matching the loop counter R7 in the
  code. Per-channel addresses are written the way the code computes them, so
  channel n's command byte is at 0xFFEF+n (0xFFF0–0xFFF7 for channels 1–8).

### Separate memory spaces

An 8051 has several address spaces, and the same number can mean different
things depending on which instruction uses it:

| Space         | Size          | Accessed with                         | Here                                                                                                                                        |
| ------------- | ------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Code          | 64 KB         | Instruction fetch, `MOVC` (read-only) | The 16 KB ROM inside the chip, 0x0000–0x3FFF.                                                                                               |
| Internal RAM  | 256 bytes     | Most instructions                     | The program's variables, flags and stack. Written as two hex digits: 0x20, 0x77.                                                            |
| SFRs          | 128 addresses | Most instructions                     | Special function registers: the CPU's own control and I/O registers, such as the ports, timers and interrupt controls. Named, not numbered. |
| External data | 64 KB         | `MOVX` only                           | Whatever chips the circuit board connects to the bus. Written as four hex digits: 0xFFF8, 0x0001.                                           |

Internal RAM 0x00–0x1F also holds the CPU's working registers R0–R7, in four
banks of eight. Part of internal RAM is bit-addressable: individual bits can
be set, cleared and tested directly, which the program uses for flags.

"Register" in this document means storage inside the CPU: the accumulator
A, R0–R7, the 16-bit pointer DPTR, and the SFRs. Locations on other chips
are called by their address.

### Ports

The 8051 has four 8-bit I/O ports, P0, P1, P2 and P3. Each is 8 pins of
general-purpose I/O, read and written as one byte through an SFR, like a
GPIO register on a modern microcontroller. `P1.4` means bit 4 of port 1, a
single pin.

Some pins have second jobs:

- **P0 and P2** form the external bus when the program uses external memory:
  P0 carries the low address byte and the data, and P2 the high address byte.
  This firmware uses the bus, so those two ports are not free for other I/O.
- **P3**'s pins double as the serial port (P3.0 RXD, P3.1 TXD), the external
  interrupt inputs (P3.2 INT0, P3.3 INT1), the timer inputs (P3.4 T0,
  P3.5 T1) and the bus read and write strobes (P3.6 WR, P3.7 RD). A program
  can use any of these as plain I/O when it doesn't need the special
  function.
- **P1** has no second job on the original 8051. On the 8052 and this OKI
  part, P1.0 and P1.1 can serve Timer 2, which this firmware doesn't use.

### Memory-mapped I/O

`MOVX` reads and writes external data memory: the CPU puts an address on
P0/P2, pulses its RD or WR pin, and moves a byte over P0. The CPU cannot
tell RAM from anything else at those addresses. Address-decoding logic on
the board decides which chip answers. So a peripheral chip can be placed in
this space, and reading or writing an address talks to that chip. This is
how the OKI firmware reaches most of its hardware.

A read and a write at the same address need not reach the same storage. A
peripheral chip can return status when read and accept a command when
written.

## The chip

Markings:

```
79X1396
M83C154-42
©OKI '80/85
JAPAN 94000
```

| Line          | Reading                                                                                                                                                                                        | Confidence |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `79X1396`     | Either the equipment maker's own part number (mask-ROM chips are often marked with the customer's number) or an OKI customer/lot code. The `79X` prefix doesn't match any scheme found online. | Low        |
| `M83C154-42`  | OKI MSM83C154, mask code 42. Consistent with OKI's `MSM83C154-xxx` ordering code, where xxx is the mask code. The package suffix is not marked.                                                | Medium     |
| `©OKI '80/85` | Copyright line, not a date code. The years may refer to the MCS-51 architecture and OKI's CMOS version, or may simply be copyright years.                                                      | Low        |
| `JAPAN 94000` | Probably date and lot. OKI's format isn't documented online. 1994 is plausible, but the fifth digit makes "date + lot" safer than a specific month.                                            | Low        |

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

The EA (External Access) pin selects where code comes from: low means
external memory, high means the internal ROM. OKI's user manual describes EA
as sampled at reset. In practice, on this chip, raising EA after reset made
`MOVC` read the internal ROM: the dump succeeded and its internal checksum
matches. Treat this as observed behaviour of this part, not a datasheet
guarantee.

1. The AVR host loads a small dumper program (`mcs51/src/romdump.c`) at
   code address 0x4000, plus a stub `LJMP 0x4000` at 0x0000.
2. The AVR holds EA low and releases reset. The 8052 fetches everything
   externally, runs the stub and jumps to the dumper.
3. About 10 ms later the AVR raises EA. Code addresses 0x0000–0x3FFF now read
   the internal ROM. Code at 0x4000 and above is still fetched externally.
4. The dumper copies code 0x0000–0x3FFF (`MOVC`) to external data
   0x0000–0x3FFF (`MOVX`).
5. The AVR resets the 8052, reads the SRAM back and prints it over serial.
   `scripts/capture_romdump.py` captures the output and writes `romdump.bin`.

Build: `pio run -e mcs51 -t upload` (see `platformio.ini` and `README.md`).

## Overview

| Item                                  | Value                                                                    |
| ------------------------------------- | ------------------------------------------------------------------------ |
| Reset vector                          | 0x0000 → 0x10E8                                                          |
| INT0 vector                           | 0x0003 → 0x0030                                                          |
| Timer 1 / Timer 2 vectors             | 0x001B / 0x002B → 0x0637                                                 |
| ROM checksum                          | 16-bit sum of 0x0000–0x3FFC = 0x45B9, stored at 0x3FFE–0x3FFF as `B9 45` |
| Config byte                           | 0x3FFD (0x00 in this dump)                                               |
| ASCII strings                         | None                                                                     |
| Code reached by recursive disassembly | 12,685 of 16,384 bytes                                                   |
| Unused                                | 0x36CA–0x3FFC (zero-filled)                                              |

The 8052's built-in serial port is not used: the code never touches its
SFRs (SBUF, SCON). P3.0 and P3.1, normally the serial pins, are used as
general-purpose outputs.

## The hardware the firmware talks to

The 8052 is an I/O controller sitting under a larger host computer. Almost
everything it does goes through **other chips on its external bus**, which
were on the original board but are not part of this dump.

### Memory-mapped peripherals

This firmware runs from internal ROM and uses no external RAM. Every `MOVX`
in it is a peripheral access (see "Memory-mapped I/O" above). There are two
regions:

| Region        | Accessed with                                                                       | What is there (inferred)                                                                                                                                                                                                                                                                                |
| ------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0xFFD9–0xFFFF | `MOVX @R0/@R1`, with P2 left at its reset value 0xFF (normal code never changes P2) | **Channel/host interface.** Status (0xFFD9, 0xFFDA, 0xFFDE, 0xFFDF), the per-channel data window (0xFFE0–0xFFEF), channel command bytes (0xFFF0–0xFFF7), the host mailbox (0xFFF8–0xFFFF), and write-only controls such as the watchdog (0xFFE3). Possibly several chips separated by address decoding. |
| 0x0000–0x000A | `MOVX @DPTR`, with the high byte 0x00                                               | **Link controller.** Status, command, indirect index and data, message FIFO, destination.                                                                                                                                                                                                               |

`MOVX @R0` and `@R1` supply only the low address byte; the high byte comes
from whatever P2 holds. P2 is never changed, so these accesses all land in
0xFF00–0xFFFF. The listing shows only the low byte, for example
`MOV R1,#F8h`.

The same hardware interrupts the CPU through the INT0 pin. IRQ_STATUS
(0xFFD9) and HOST_STATUS (0xFFDF) say which part needs attention.

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
       0xFFxx │                   │ 0x00xx
 ┌────────────▼─────────┐ ┌───────▼─────────────┐
 │ channel/host         │ │ link controller     │
 │ interface            │ │ 0x0000–0x000A       │
 │ 0xFFD9–0xFFFF        │ │                     │
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
- **Reads and writes at the same address often reach different storage.**
  For example, reading 0xFFFB gets the host's debug command, but writing it
  sets the channel toggle bits. Typical of peripheral chips and latches.
- **The host mailbox** may be a dual-port RAM or mailbox chip shared with the
  host CPU, fitting an I/O card in a larger machine.
- **The link controller** has a message FIFO at one address, a second set
  of settings reached indirectly, and command codes: a dedicated network or
  serial-link chip. Its layout is the strongest fingerprint for identifying
  the equipment.

### What this means on the dumping breadboard

On the LED-sign breadboard, all external data space is the SRAM, so these
"peripheral" accesses would simply land in RAM. That is why the dump works:
the dumper uses `MOVX` writes to copy the ROM into SRAM. It also means the
OKI firmware cannot do its real job on that board: the channel/host chips
and the link controller would have to be emulated. By contrast, the
Signetics SCN8031H program (`scn8031/`) uses no `MOVX` at all; everything it
controls is wired to its port pins.

The three interfaces in detail:

### 1. Host mailbox (0xFFF8–0xFFFF)

- **Status reads** (0x05A4). The host writes an internal RAM address to
  0xFFFA. The firmware puts the byte from that internal RAM address at 0xFFF8
  and echoes the address at 0xFFF9. Internal RAM bytes 0x20–0x25 and 0x2E
  are cleared when the host reads them (0x21 only partly, masked with 0xC1),
  so they act as host-visible error and status bytes.
- **Start command** (0x05F1). The host writes 0x01 to 0xFFFD. The firmware:
  - sets flags 0x20.0 and 0x21.3;
  - clears internal RAM 0x1E and 0x77, and writes 0x00 to 0xFFFB;
  - for each channel, sets its bit in CH_ACTIVE (internal 0x2D) if its status
    code at 0x3F+n is not 0x01, and in 0x1D if the code is 0x10;
  - writes status byte 0x21 to 0xFFFD, then recomputes the per-channel status.
- **Debug monitor** (0x35A7–0x36C1):
  - Entry: the host writes 0xFC to 0xFFFB. The firmware answers 0xFC at
    0xFFFA and sets flag 0x2A.1.
  - Exit: the host writes 0xFA to 0xFFFB.
  - Command 0x8_ writes and 0xA_ reads. Bits 0–3 pick the target:

    | Bit | Target                                                |
    | --- | ----------------------------------------------------- |
    | 0   | Internal RAM, through `@R0` (0x00–0xFF; not the SFRs) |
    | 1   | External data (`MOVX @R0`, high byte set by P2)       |
    | 2   | Link controller (`MOVX @DPTR`, 0x0000–0x00FF)         |
    | 3   | Port: P1, P2 or P3 (target address < 2, = 2, > 2)     |

    SFRs other than the ports, and program memory, are not reachable.
  - The target address comes from 0xFFFF and the data from 0xFFFE. Read
    results go to 0xFFFA. The address and data are echoed to 0xFFE4/0xFFE5.
  - In debug mode the main poll keeps polling channels and kicking the
    watchdog but never returns to the background loop, so the self-test is
    suspended. Status reporting and the P3.5 health output also stop.
- **Health output (P3.5):** outside debug mode, every 100 passes of the main
  poll (0x1751), status byte 0x21 is written to 0xFFFD and pin P3.5 is
  updated: low when internal 0x26, 0x28 or 0x29 are non-zero, toggling while
  error flags 0x21.1 or 0x21.2 are set, otherwise high.

The INT0 handler (0x0030) reads IRQ_STATUS at 0xFFD9. Bit 0 → channel
receive. Bit 1 → host mailbox dispatch at 0x00B2, which branches on
HOST_STATUS at 0xFFDF: bit 4 → channel command (read from 0xFFFC, 0x00DA),
bit 2 → status read, bit 3 → debug monitor, bit 5 → start command, bits 6
and 7 → writes to 0xFFE4/0xFFE5.

### 2. Eight channels (0xFFE0–0xFFEF, 0xFFF0–0xFFF7)

- A command byte arrives for channel n at 0xFFEF+n (0xFFF0–0xFFF7): 7 bits
  plus odd parity, signalled by INT0. It is stored in internal RAM at
  0x37+n.
- Two readings per channel at 0xFFE0+2(n−1) and 0xFFE1+2(n−1): 7 bits plus
  odd parity. Each is read twice in a row (`MOVX A,@R1` twice).
- 0xFFE0–0xFFEF is also read as a configuration block: a mode/type byte at
  0xFFE0, data from 0xFFE1, and a checksum (see below). Normal code never
  changes P2, so how one window serves both uses is not explained by the ROM.
- Each accepted command flips that channel's bit in internal 0x77, which is
  written to 0xFFFB. Commands 0x15 and 0x16 don't flip it. Function not
  proven: handshake line or indicator.
- Per-channel state for the main loop's state machine is at internal
  0x2F+n (initial state 0x45). A per-channel status code is at 0x3F+n: set to
  values 0x01–0x13 and compared, never counted down. Further per-channel
  bytes are at 0x47+n, 0x4F+n, 0x57+n, 0x5F+n and 0x67+n.

#### Channel records

Internal RAM 0x80–0xDF holds a 12-byte record per channel, at
0x80 + 12(n−1). `check_window_block` (0x2E34–0x2E6D) fills it from the
configuration block, shifting bit fields down to the low bits. WIN_E0 etc.
are the listing's names for the bytes at 0xFFE0 onwards.

| Offset | Contents                    |
| ------ | --------------------------- |
| +0     | WIN_E0 bits 6–4 (type, 0–7) |
| +1     | WIN_E0 bits 3–0             |
| +2..+7 | WIN_E1..WIN_E6              |
| +8     | WIN_E7 bits 5–4             |
| +9     | WIN_E8 bits 7–6             |
| +0xA   | WIN_E8 bits 5–4             |
| +0xB   | WIN_E9                      |

WIN_E0 bit 7 is not stored; MSG_FLAGS (internal 0x74) bit 7 is set to its
inverse instead (0x021D). WIN_E0 bit 6 selects MSG_PARAM (internal 0x19):
0x06 if set, 0x04 if clear. The state 0x45 handler tests record byte 0 bit 2
(WIN_E0 bit 6) and record byte 0xA == 2.

#### Checksum conventions

- `send_window_block` (0x04DA) sends the bytes at 0xFFE1..0xFFE8.
  `check_window_checksum` (0x0504) then requires
  sum(0xFFE1..0xFFE8) + byte at 0xFFE9 + 1 = 0, that is, 0xFFE9 holds the
  one's complement of the sum. The type 3 path (0x0342) does the same with
  0xFFE1..0xFFE4 and the checksum at 0xFFE5.
- `check_window_block` (0x2DFA) sums 0xFFE0..0xFFE8 (types 1 and 2) or
  0xFFE0..0xFFEA (other types) and expects 0xFF.
- `receive_and_checksum` (0x052F) reads the message type byte, then R6 data
  bytes, adds them to R2, then adds the local checksum byte and 1 and expects
  zero. The starting values come from the caller.

### 3. Link controller chip (0x0000–0x000A)

Part number unknown.

- Its reset input is driven from pin P3.3.
- It has two kinds of storage: a set of addresses the CPU reaches directly,
  and a second set inside the chip that the CPU reaches indirectly, by
  writing an index and then reading or writing a data address.

| Address | Use                                                                                                                                               |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0x0001  | Status. Bit 4 = ready for a new message (polled up to 100 times after command 0x04, 0x0584). Bit 6 = message received (polled in 0x052F).         |
| 0x0002  | Write: index of an indirect setting; bit 3 set = select for reading. Read: bit 7 = ready for an indirect access (polled up to 200 times, 0x2F41). |
| 0x0003  | Command. 0x04 = prepare to send, 0x01 = send, 0x08 = release receive buffer.                                                                      |
| 0x0007  | Indirect data.                                                                                                                                    |
| 0x0008  | Message FIFO (data in and out).                                                                                                                   |
| 0x000A  | Destination: 0x2F+n (0x30–0x37) or 0xFF+n (wraps to n−1, 0x00–0x07).                                                                              |

- **Indirect write:** data to 0x0007, then the index to 0x0002. Indexes
  used: 0x10–0x17 (per channel, 0x2F41), 0x30–0x37 (warm init, 0x06DF),
  0x80–0x87, 0xA0–0xA7, 0xC2–0xC4.
- **Indirect read:** the index with bit 3 set to 0x0002, then read 0x0007.
- **Setup (0x08BC):**
  - Config: index 0xC2 ← 0x28, 0xC4 ← 0x37.
  - Table at indexes 0x80–0x87 ← 0x81–0x88.
  - Table at indexes 0xA0–0xA7 ← 0x97, 0x80–0x86.
  - Index 0xC3 ← 0x01.
  - 0xC2, 0xC3, 0x80–0x87 and 0xA0–0xA7 are read back; 0xC4 is not. Any
    mismatch goes to the error path at 0x0CBE.
- **Sending:** command 0x04 and wait for ready, write bytes into the FIFO at
  0x0008, write the destination to 0x000A, then command 0x01 to 0x0003.
- Link timeouts (no ready signal) set error flags 0x21.2 and 0x24.3.
- A loopback test fills the FIFO with 0x55/0xAA and reads it back
  (0x0DA8–0x0DEF).

Writes to external address 0xFFE3 appear 37 times (35 through `@R1`, 2
through `@R0`), between steps of long operations. They are most likely
watchdog kicks: a watchdog resets the CPU if it isn't written to often
enough, recovering from a hang.

## Message types

First byte of each message sent through the link controller:

| First byte                               | Data bytes              | Notes                                                                                                                                        |
| ---------------------------------------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 03/43, 0B/4B, 13/53, 18/58, 23/63, 2B/6B | varies                  | Pairs differ only in bit 6. The first of each pair carries the configuration block: the bytes at 0xFFE1..0xFFE8, or 0xFFE1..0xFFE4 for 0x18. |
| 06, 26, 66                               | 2, 2, 0                 | Variants differ in bits 5–6                                                                                                                  |
| 27                                       | 1                       |                                                                                                                                              |
| 30                                       | 4 (6 in one error case) | Channel readings (see below)                                                                                                                 |

Startup handshake (0x0BC2), per channel:
1. Indirect write 0xC0 to index 0x10+(n−1).
2. Send `26 04 88` to destination 0x2F+n.
3. Send `66` to destination 0xFF+n (= n−1), and expect `66 04 88` back. The
   value written in step 2 is read back.
4. Send `30 11 2B 11 2B` (readings invalid) to destination 0x2F+n.

## Command 0x2_: read the channel

- Bits 4–6 = 010 means a data request (`(cmd & 0x70) == 0x20`).
- The reply is built at 0x0F7C:

  ```
  30 | value(0xFFE1+2(n−1)) hi lo | value(0xFFE0+2(n−1)) hi lo
  ```

  It goes to destination 0x2F+n.
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
  or +18 (0x34A7) for the first reading (0xFFE1+2(n−1)), bit 1 picks 0
  (0x31A7) or +128 (0x32A7) for the second (0xFFE0+2(n−1)). In effect each
  bit selects one of two ranges.
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

| N      | Exact matches |
| ------ | ------------- |
| 58     | 0             |
| 59     | 0             |
| **60** | **70**        |
| 61     | 3             |
| 62     | 0             |

- The low nibble takes only the values 0–4. It drops by 1 every 60 entries,
  at curve positions −96, −35, 25 and 85, and in 70 cases everything else
  stays the same: `24 05 → 23 05 → 22 05`, `14 AB → 13 AB`, `D3 03 → D2 03`.
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

The high nibble of byte 0 runs through the hex digits A–F, then 7 down to 1.
The wrap from A–F to 0–7 also recurs every 60 entries, at positions −70,
−10, 50 and 110, 25–26 entries after each exponent change. So each 60-entry
cycle has two fixed landmarks. The split between digits A–F and 0–7 is part
of the number's structure.

### Two anomalies

- Position −70 (0x33A7 entry 40): `14 01`, exponent 4 between neighbours
  with exponent 3 (`E3 0A → 14 01 → 73 01`).
- Position 110 (0x31A7 entry 110, also 0x34A7 entry 92): `11 01`, exponent 1
  between neighbours with exponent 0 (`E0 0B → 11 01 → 60 0B`).

Both sit exactly on the A–F → 7 wrap, 180 entries (3 × 60) apart, with the
same shape. The other two wraps (−10, 50) have no such entry. They look like
a renormalisation carry or a deliberate special code, not table defects. A
test: decode the values either side. If `1x 01` is 1.0 × 10^(e+1) and its
neighbours are about 9.99 × 10^e, it is a carry.

### Mantissa: unresolved

- The high nibble of byte 0 counts cleanly if each nibble value x is decoded
  as `x >= 8 ? x - 8 : 15 - x`. That gives the order 8, 9, A–F, 7, 6 … 0.
  Only 13 small glitches remain, at boundaries.
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

| Address | Contents                                                                                                                                                                                                         |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0x318E  | Channel bit masks: `FF 01 02 04 08 10 20 40 80` (indexed 0–8)                                                                                                                                                    |
| 0x3196  | Inverted channel masks: `80 FE FD FB F7 EF DF BF 7F` (shares its first byte with 0x318E)                                                                                                                         |
| 0x1791  | Jump table of 35 `LJMP`s: per-channel state machine (dispatcher at 0x178D, `JMP @A+DPTR` at 0x1790). The state value is the byte offset into the table, so state = 3 × entry. States 0x4E–0x5D all go to 0x2CEC. |

Unreferenced: nothing in the code points at these (no DPTR setup, no
`MOVC A,@A+PC`). They may be leftovers, or data for something not in this ROM.

| Address | Contents                                      |
| ------- | --------------------------------------------- |
| 0x308F  | 256-byte bit-reverse table                    |
| 0x319F  | `03 03 0C 0C 30 30 C0 C0`                     |
| 0x36C2  | Inverted bit masks: `FE FD FB F7 EF DF BF 7F` |

## Other routines

- **Startup (0x10E8):** clears external addresses 0xFFFC and 0xFFFB, and sets
  the stack pointer to internal 0xDF. Init at 0x0654 reads the reset cause
  and records it in status byte 0x20 for the host: IRQ_STATUS (0xFFD9) bit 2
  → 0x08, bit 3 → 0x04, HOST_STATUS (0xFFDF) bit 1 → 0x02. IRQ_STATUS bit 4
  reinitialises only the link and channels. Then it clears internal RAM,
  checksums the whole ROM (0x07E1), tests internal RAM, configures the link
  controller and starts Timer 2 and INT0.
- **Background self-test (0x1117):** between runs of the main poll, a
  rolling self-test runs:
  1. ROM checksum, 20 bytes per step.
  2. R0/R1 test.
  3. Internal RAM write/read test (0xFF, 0x00), 16 bytes per step.
  4. Internal RAM 0x80–0xDF checksum, compared with the first pass.
  5. Link controller config read-back.
  6. Link loopback test (0x13F3).
  7. Stack sentinel: internal RAM 0xFF must still be 0xFF.

  Failures set error bits in status bytes 0x21, 0x22 and 0x24 for the host.
  Config byte bit 2 (flag 0x2A.7) skips the self-test entirely.
- **Timer interrupt (0x0637):** Timer 2 with reload value RCAP2 = 0xFE80
  (384 machine cycles per tick). Drives decimal counters at internal
  0x10–0x13: every tick, 10, 100 and 1000 ticks.
- **Per-channel input lines:** port P1 is read while pin P3.1 (0x2DD2) or
  pins P3.0 and P3.1 (0x2DE4) are pulsed, then masked with the channel's
  bit. Two banks of 8 per-channel inputs: switches or presence lines.

## Suspected firmware bugs

1. **Write to a bank 0 register (0x2C5C).** In the state 0x45 handler, the
   code computes `0xFF + R7` (= n−1) and writes 0x10 to that internal RAM
   address. That lands in internal RAM 0x00–0x07, the bank 0 working
   registers R0–R7, instead of the per-channel status code at 0x3F+n that
   the equivalent code at 0x0788–0x07A6 uses. For channel 8 it overwrites
   R7, the channel loop counter. It only runs on one path (command 0x07
   received while the channel is not faulty), which may be why it went
   unnoticed.
2. **7-byte readings message (0x1005).** When the second reading fails its
   parity check, the first value has already been written, and the error
   handler appends four more bytes (see "Command 0x2_"). 0x1005 should
   probably go to a path that writes only `11 2B`. Whether this breaks the
   receiver depends on whether it treats `30` as a fixed 5-byte message,
   which can't be told without the link controller's datasheet. Probable,
   not certain.

## Corrections to earlier claims

- The message first bytes are types that come in variants (see table above).
  Calling this "3-bit type + 4-bit code" was wrong.
- Commands 0x15 and 0x16 are not discarded. They are processed but don't
  flip the channel bit.
- The 0xFFF0–0xFFF7 command bytes use odd parity, not even. The check is
  `JNB P`: an even number of 1 bits is an error.
- Link controller address 0x0002's bit 7 means "ready for an indirect
  access", not "data available". Bit 7 of a value written to 0x0002 is part
  of the index, not a write strobe. 0x2F41 waits for it, then writes R3 to
  indirect index 0x10+(n−1).
- Internal 0x3F+n holds a per-channel status code, not a timeout counter.
- Host mailbox dispatch bits were misassigned: HOST_STATUS bit 4 is the
  channel command, bit 2 the status read.
- The P3.5 health output is not driven in debug mode. It is driven in
  normal operation.
- The constants 0x01, 0x02 and 0x04 in comparisons are mostly compared
  against per-channel state variables, not received characters. They are not
  evidence of ASCII control characters (STX/EOT). The same applies to 0x15
  and 0x16: calling them NAK and SYN was unfounded.
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

| Feature                                                                                        | Implication                                                         |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Six-decade log scale, decimal exponent                                                         | A physical quantity measured across decades                         |
| Two readings per channel, on different parts of the curve                                      | Two related measurements, or two detectors/ranges per head          |
| Sentinel for out of range, `11 2B` for "invalid"                                               | The receiver displays or logs these values                          |
| Per channel: command byte, two readings, a configuration block with checksum, six device types | Smart remote sensor heads, not bare analog inputs                   |
| 7-bit data plus odd parity on all channel bytes                                                | Consistent with a serial-style link to each head                    |
| ROM checksum, RAM tests, watchdog, stack check, reset cause reported to the host               | Built for high reliability. Unusual for consumer equipment          |
| Host debug monitor                                                                             | Intelligent I/O card under a supervisory CPU, serviced in the field |
| Mask ROM, custom marking                                                                       | Made in volume for one company's product                            |

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
   address layout and command codes are the strongest fingerprint for the
   equipment family.
2. Other chips in the same batch with a different `79Xnnnn` or `-nn` marking,
   meaning other ROM programs from the same maker.
3. The makerspace donor, who might know the employer or equipment.
4. OKI's data books, for the marking and date-code layout.
5. Decoding the mantissa, and the two anomalies.

## Tools

- `romdump_annotated.lst`: annotated disassembly, generated by
  `python3 tools/annotate.py`. Names and comments come from
  `tools/romdump_annotations.py`. External accesses, per-channel array
  pointers, channel mask lookups and state assignments are annotated
  automatically. Each state handler gets a summary of the states it sets and
  the routines it calls. The listing uses assembler notation: `FFh` for hex,
  and only the low byte for `@R0`/`@R1` external addresses.
- `tools/dis51.py`: a minimal recursive-descent 8051 disassembler. Extra entry
  points (hex) follow the ROM path. To include the 0x1791 jump table and the
  0x00CB mailbox jump table:

  ```
  python3 tools/dis51.py romdump.bin 35A7 05A4 05E5 05F1 05EB 062E \
    $(python3 -c "print(' '.join(f'{0x1791+3*i:04X}' for i in range(35)))") \
    > rom.lst
  ```
