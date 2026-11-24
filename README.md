# MSM83C154 ROM Dump

A dump and analysis of the 16 KB internal mask ROM of an OKI MSM83C154
(8051-family) microcontroller, found among the pile of MCS-51 parts in my
[makerspace](https://ashevillemakers.org/)'s electronics supply drawers.

The chips turned out to be preprogrammed. This repository contains the tooling
used to read the ROM out, the dump itself, and an analysis of what the program
does.

A second set of chips from the same drawer, Signetics SCN8031Hs, is covered
in `scn8031/`. They are marked as the ROMless 8031, but their 4 KB internal
ROM holds a stepper motor controller program.

It is a branch of my 8052 LED sign project, which provided the hardware: an
8052 running from SRAM that an ATmega328 loads on its behalf. I'm documenting
that project on my blog,
https://www.blog.montgomerie.net/tags/makerspace-mcu-series/.


## Contents

| Path | What |
|---|---|
| `romdump.bin` | The 16,384-byte ROM dump. Its internal checksum verifies. |
| `ROM_ANALYSIS.md` | What the program does. |
| `romdump_annotated.lst` | Annotated disassembly. |
| `tools/dis51.py` | Minimal recursive-descent 8051 disassembler used for the analysis. |
| `tools/annotate.py` | Generator for the annotated disassemblies. `--annotations MODULE` picks the annotation data. |
| `tools/romdump_annotations.py` | Annotation data for the OKI dump (the default). |
| `scn8031/` | The SCN8031H dump, its analysis and annotated disassembly. |
| `tools/scn8031_annotations.py` | Annotation data for the SCN8031H dump. |
| `mcs51/src/romdump.c` | Dumper, run by the 8052. |
| `avr_host/src/` | AVR host: loads the dumper, runs it, prints the dump over serial. |
| `scripts/capture_romdump.py` | Captures the serial output into a `.bin` file (default `romdump.bin`). |
| `hardware/` | KiCad schematic and PCB of the circuit. |
| `docs/RAM:ROM Shadowing.txt` | Notes on the SRAM address decode the dumper relies on. |


## How the dump works

The MSM83C154 does not latch its EA (External Access) pin at reset, so the
internal ROM can be switched on after the chip has started running external
code:

1. The AVR writes the dumper to SRAM at code address 0x4000, and a stub
   `LJMP 0x4000` at 0x0000.
2. With EA held low, the AVR releases the 8052's reset. The 8052 runs the stub
   from external memory and jumps to the dumper.
3. The AVR raises EA. Code addresses 0x0000–0x3FFF now read the internal ROM.
   Code at 0x4000 and above is still fetched externally.
4. The dumper copies code 0x0000–0x3FFF (MOVC) to data 0x0000–0x3FFF (MOVX).
5. The AVR puts the 8052 back into reset, reads the SRAM, and prints it.

The 8052's EA pin must be wired to AVR pin PD2.


## Running it

This is built with [PlatformIO](https://platformio.org). On Apple Silicon Macs,
PlatformIO's MCS-51 and AVR toolchains need Rosetta.

```
pio run -e mcs51 -t upload
~/.platformio/penv/bin/python scripts/capture_romdump.py [port] [output.bin]
```

Uploading the `mcs51` environment builds the dumper, then builds and uploads
the AVR host with the dumper compiled into it. The capture script resets the
AVR, so the whole sequence (RAM test, load, dump) runs again while it listens.
The serial monitor runs at 38400 baud.


# Copyright

Copyright 2026 James Montgomerie.

See `LICENSE.txt` for license terms.
