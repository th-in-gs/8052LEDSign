# Annotations for the MSM83C154 ROM dump (romdump.bin), used by
# tools/annotate.py to produce romdump_annotated.lst.
#
# Everything here is inferred from how the code uses each address. Names are
# descriptive guesses, not names from any original source. See ROM_ANALYSIS.md.
#
# Conventions in the code:
#  - R7 is the channel number, 1-8, in almost all per-channel code.
#  - The table at 318Eh gives the bit mask for channel n (bit n-1), 3196h the
#    inverted mask.
#  - Per-channel arrays live at base+n: state at 2Fh+n, command at 37h+n,
#    status code at 3Fh+n.
#  - External registers are read twice in a row (MOVX A,@R1 twice).

# Extra trace entry points: the jump table at 1791h and the host mailbox
# dispatch at 00CBh.
ENTRIES = [0x35A7, 0x05A4, 0x05E5, 0x05F1, 0x05EB, 0x062E] + \
          [0x1791 + 3 * i for i in range(35)]

JUMP_TABLE = 0x1791
JUMP_TABLE_ENTRIES = 35

# Per-channel arrays: base address (as used in MOV A,#base / ADD A,R7) -> name.
CHANNEL_ARRAYS = {
    0x2F: 'state',
    0x37: 'cmd',
    0x3F: 'code',       # per-channel status code, 01h-13h
    0x47: 'ch48',
    0x4F: 'ch50',
    0x57: 'ch58',
    0x5F: 'ch60',
    0x67: 'ch68',
}

# ---------------------------------------------------------------------------
# External registers, accessed with MOVX @R0/@R1 (P2 is never changed, so
# probably FFxxh). Reads and writes at the same address are often different
# registers.

EXT_READ = {
    0xD9: 'IRQ_STATUS',     # b0 channel rx, b1 host; b2/b3/b4 reset cause
    0xDA: 'CH_STATUS',      # per-channel status bits (105Bh)
    0xDB: 'REG_DB',
    0xDE: 'CH_RX_READY',    # bit n-1 set: channel n has a command byte
    0xDF: 'HOST_STATUS',    # b1 reset cause; b2-b7 host request flags
    0xF8: 'HOST_F8',
    0xF9: 'HOST_F9',
    0xFA: 'HOST_ADDR',      # host: iRAM address to read / debug exit (FAh)
    0xFB: 'HOST_DBGCMD',    # host: debug command (FCh enter, 8xh/Axh)
    0xFC: 'HOST_CHCMD',     # host: channel command
    0xFD: 'HOST_START',     # host: 01h = start
    0xFE: 'HOST_DATA',      # host: debug data
    0xFF: 'HOST_DBGADDR',   # host: debug address
}
for _i in range(16):
    EXT_READ[0xE0 + _i] = f'WIN_{0xE0 + _i:02X}'   # channel data window
for _i in range(8):
    EXT_READ[0xF0 + _i] = f'CH{_i + 1}_CMD'        # 7 bits + odd parity

EXT_WRITE = {
    0xE2: 'CTRL_E2',        # written 10h, F8h, F9h
    0xE3: 'WATCHDOG',       # written (any value) between long steps
    0xE4: 'ACK_E4',
    0xE5: 'ACK_E5',
    0xE6: 'ACK_E6',
    0xE7: 'ACK_E7',
    0xF8: 'HOST_REPLY_DATA',
    0xF9: 'HOST_REPLY_ADDR',
    0xFA: 'HOST_REPLY',
    0xFB: 'CH_TOGGLE',      # per-channel bits, flipped per accepted command
    0xFC: 'REG_FC',
    0xFD: 'HOST_STATUS_OUT',
    0xFE: 'HOST_FE_OUT',
    0xFF: 'HOST_FF_OUT',
}
for _i in range(8):
    EXT_WRITE[0xE8 + _i] = f'CH{_i + 1}_CFG'

# ---------------------------------------------------------------------------
# Link controller, accessed with MOVX @DPTR, DPH = 00h.

LINK_REGS = {
    0x01: 'LINK_STATUS',    # b4 ready to send, b6 message received
    0x02: 'LINK_INDEX',     # w: indirect register (+08h = select for read); r: b7 ready
    0x03: 'LINK_CMD',
    0x07: 'LINK_IDATA',     # indirect data
    0x08: 'LINK_FIFO',      # message bytes in and out
    0x0A: 'LINK_DEST',      # destination
}
LINK_COMMANDS = {
    0x01: 'SEND',
    0x04: 'PREPARE (then wait for STATUS b4)',
    0x08: 'RELEASE RECEIVE BUFFER',
}

# ---------------------------------------------------------------------------
# Internal RAM and bit names.

IRAM = {
    0x10: 'TICK',           # Timer 2 tick count
    0x11: 'TICK_10',        # ...every 10 ticks
    0x12: 'TICK_100',
    0x13: 'TICK_1000',
    0x14: 'DIV_10',
    0x15: 'DIV_100',
    0x16: 'DIV_1000',
    0x19: 'MSG_PARAM',      # 04h or 06h, sent in 06/26 messages
    0x1B: 'RETRY',
    0x20: 'STAT20',         # host-readable status, read-to-clear (20h-25h, 2Eh)
    0x21: 'STAT21',         # summary flags, also sent to HOST_STATUS_OUT
    0x22: 'STAT22',         # error detail
    0x23: 'CH_PARITY_ERR',  # per-channel mask
    0x24: 'STAT24',         # error category
    0x25: 'CH_LINK_ERR',    # per-channel mask
    0x26: 'CH_FAULT',       # per-channel mask
    0x2D: 'CH_ACTIVE',      # per-channel mask
    0x2E: 'CH_CSUM_ERR',    # per-channel mask
    0x74: 'MSG_FLAGS',      # sent in 06/26/27 messages
    0x75: 'CH_DEFER_REQ',   # data request arrived while busy
    0x76: 'CH_PENDING',     # command arrived while slot full
    0x77: 'CH_TOGGLE_BITS',
    0x79: 'TMP79',
    0x7A: 'TMP7A',
    0x7B: 'CSUM_PTR_HI',
    0x7C: 'CSUM_PTR_LO',
    0x7D: 'IRAM_CSUM_REF',
    0x7E: 'BLINK_DIV',
}

BITS = {
    0x09: 'ERROR',          # 21h.1
    0x0A: 'FAULT',          # 21h.2: health output toggles while set
    0x10: 'ERR_CHECKSUM',   # 22h.0: iRAM 80h-DFh or channel block checksum
    0x11: 'ERR_RAM_TEST',   # 22h.1
    0x12: 'ERR_ROM_CSUM',   # 22h.2
    0x13: 'ERR_STACK',      # 22h.3: sentinel at iRAM FFh overwritten
    0x15: 'ERR_PARITY',     # 22h.5
    0x16: 'ERR_LINK',       # 22h.6
    0x17: 'ERR_PROTOCOL',   # 22h.7
    0x51: 'DEBUG_MODE',     # 2Ah.1
    0x53: 'FIRST_PASS',     # 2Ah.3
    0x55: 'DEFER_PENDING',  # 2Ah.5
    0x56: 'CFG_BIT1',       # 2Ah.6: from config byte 3FFDh bit 1
    0x57: 'CFG_BIT2',       # 2Ah.7: from config byte 3FFDh bit 2
    0xB5: 'HEALTH_OUT',     # P3.5
}

# ---------------------------------------------------------------------------
# Routine names.

LABELS = {
    0x0000: 'RESET',
    0x0003: 'VEC_INT0',
    0x000B: 'VEC_TIMER0',   # unused: NOPs fall through to the next vector
    0x0013: 'VEC_INT1',     # unused
    0x001B: 'VEC_TIMER1',
    0x0023: 'VEC_SERIAL',   # unused
    0x002B: 'VEC_TIMER2',
    0x0030: 'INT0_ISR',
    0x0049: 'int0_channel_rx',
    0x00A4: 'int0_parity_error',
    0x00B2: 'int0_host',
    0x00DA: 'host_channel_command',
    0x0177: 'channel_configure',
    0x04DA: 'send_window_block',
    0x0504: 'check_window_checksum',
    0x052F: 'receive_and_checksum',
    0x0584: 'link_prepare',
    0x05A4: 'host_status_read',
    0x05E5: 'host_ack_e4',
    0x05EB: 'host_ack_e5',
    0x05F1: 'host_start',
    0x062E: 'isr_exit',
    0x0637: 'TIMER_ISR',
    0x0654: 'init',
    0x07E1: 'rom_checksum_full',
    0x089B: 'init_recover',
    0x08BC: 'link_init',
    0x0BC2: 'channel_handshake',
    0x0CBE: 'link_error',
    0x0CDA: 'channel_link_test',
    0x0DA8: 'fifo_fill_55',
    0x0DB4: 'fifo_check_55',
    0x0DCD: 'fifo_fill_AA',
    0x0DD9: 'fifo_check_AA',
    0x0DF2: 'channel_echo_test',
    0x0F5F: 'delay_3C',
    0x0F63: 'delay_50',
    0x0F67: 'delay_82',
    0x0F7C: 'send_readings',
    0x105B: 'update_channel_status',
    0x10E8: 'start',
    0x1117: 'background_loop',
    0x13F3: 'link_loop_test',
    0x160C: 'send_26',
    0x163E: 'send_06_if_needed',
    0x1679: 'main_poll',
    0x1751: 'debug_mode_poll',
    0x178D: 'dispatch_state',
    0x1791: 'state_jump_table',
    0x2DD2: 'read_p1_bank_a',
    0x2DE4: 'read_p1_bank_b',
    0x2DFA: 'check_window_block',
    0x2E71: 'host_channel_op',
    0x2F3C: 'p3_lines_low',
    0x2F41: 'link_iwrite_channel',
    0x2F68: 'send_06_a',
    0x2FA3: 'send_26_a',
    0x2FDE: 'send_06_b',
    0x3019: 'send_26_8F',
    0x3054: 'send_06_c',
    0x35A7: 'debug_monitor',
}

# One-line summaries, used as comments on calls.
SUMMARY = {
    0x0177: 'configure channel R7',
    0x04DA: 'copy WIN_E1..E8 to FIFO, send to 30h+n-1',
    0x0504: 'verify window checksum, else mark channel bad',
    0x052F: 'wait for reply, sum R6 bytes, verify checksum',
    0x0584: 'prepare link for a new message',
    0x07E1: 'checksum whole ROM',
    0x08BC: 'reset and configure link controller',
    0x0BC2: 'per-channel link handshake (26 04 88, 66, 30 11 2B 11 2B)',
    0x0CBE: 'flag link error for channel R7',
    0x0CDA: 'link test for channel R7 (26 55 55 / 66)',
    0x0DA8: 'write R2 x 55h to FIFO',
    0x0DB4: 'expect R2 x 55h from FIFO',
    0x0DCD: 'write R2 x AAh to FIFO',
    0x0DD9: 'expect R2 x AAh from FIFO',
    0x0DF2: 'echo test for channel R7',
    0x0F5F: 'short delay',
    0x0F63: 'short delay',
    0x0F67: 'short delay',
    0x0F7C: 'send channel R7 readings (30 hh ll hh ll)',
    0x105B: 'recompute per-channel status',
    0x13F3: 'link loopback test, all channels',
    0x160C: 'send 26 MSG_PARAM MSG_FLAGS',
    0x163E: 'send 06 MSG_PARAM MSG_FLAGS if needed',
    0x1679: 'main poll: 100 passes over all channels',
    0x178D: 'jump to handler for state in A',
    0x2DD2: 'read P1 with P3.1 pulsed: A = channel R7 bit',
    0x2DE4: 'read P1 with P3.0+P3.1 pulsed: A = channel R7 bit',
    0x2DFA: 'verify checksum of window block',
    0x2E71: 'host channel operation',
    0x2F3C: 'P3.0 and P3.1 low',
    0x2F41: 'wait link ready, indirect write R3 -> 10h+n-1',
    0x2F68: 'send 06 MSG_PARAM MSG_FLAGS',
    0x2FA3: 'send 26 MSG_PARAM MSG_FLAGS',
    0x2FDE: 'send 06 MSG_PARAM MSG_FLAGS',
    0x3019: 'send 26 MSG_PARAM 8Fh',
    0x3054: 'send 06 MSG_PARAM MSG_FLAGS',
}

# ---------------------------------------------------------------------------
# Block comments, printed before the given address.

BLOCKS = {
0x0000: """\
MSM83C154 internal mask ROM, 16 KB. Annotated disassembly.

Generated by tools/annotate.py from romdump.bin and
tools/romdump_annotations.py. All names and comments are inferred from how
the code uses each address. See ROM_ANALYSIS.md for the overall picture.

Interrupt vectors: reset, INT0 and the Timer 1/Timer 2 tick.""",

0x0030: """\
INT0: external hardware interrupt. Uses register bank 1.
IRQ_STATUS bit 0: a channel has a command byte. Bit 1: host request.""",

0x0049: """\
Channel receive. Find the first channel with a byte ready, read it, check
odd parity, strip bit 7. If the channel's command slot (37h+n) is empty,
store it there and, unless it is 15h, 16h or a data request (2xh), flip the
channel's toggle bit. If the slot is full, mark the channel pending, and
remember data requests in CH_DEFER_REQ.""",

0x00B2: """\
Host request. Dispatch on HOST_STATUS bits:
  b4 -> host_channel_command   b2 -> host_status_read   b3 -> debug_monitor
  b5 -> host_start             b7 -> ACK_E5             b6 -> ACK_E4""",

0x00DA: """\
Host channel command (HOST_CHCMD). Bits 0-2: channel - 1.
  00xxxxxx: send that channel's readings.
  01x0Cxxx: mark channel (C=0) or all channels (C=1) in 2Ch.
  01x1xxxx: host_channel_op.
  11x0Cxxx: mark channel or all channels in 1Dh.
  11x1Cxxx: configure channel or all channels, reply 01h/81h on HOST_FE_OUT.""",

0x0177: """\
Configure channel R7. Only in states 4Eh-5Dh, otherwise a protocol error.
Sends 27 MSG_FLAGS, then reads the mode byte at WIN_E0 (bits 0-2) and sends
one of six message pairs: 03/43, 0B/4B, 13/53, 18/58, 23/63, 2B/6B. The
first carries the window block, WIN_E1..E8 checked against the checksum at
WIN_E9 (type 3, 18h: WIN_E1..E4 and the checksum at WIN_E5). The second
reads the block back, and the reply must match the same checksum. Success moves the channel to the next state.""",

0x0584: """\
Prepare the link for a new message: command 04h, then wait for STATUS bit 4.
Gives up after 100 tries and flags FAULT.""",

0x05A4: """\
Host status read: host writes an iRAM address to HOST_ADDR, we return the
byte on HOST_REPLY_DATA and the address on HOST_REPLY_ADDR. Status bytes
20h, 22h-25h and 2Eh clear when read. 21h keeps only bits 0 and 6-7.""",

0x05F1: """\
Host start (HOST_START = 01h). Clears the toggle bits, rebuilds the channel
masks from the timeout counters, reports STAT21.""",

0x0637: """\
Timer 2 tick (reload FE80h = 384 machine cycles). Decimal counters:
TICK every tick, TICK_10 every 10, TICK_100 every 100, TICK_1000 every
1000.""",

0x0654: """\
Initialisation. Reads the reset cause and records it in STAT20/STAT21 for
the host:
  IRQ_STATUS b2 -> 08h   IRQ_STATUS b3 -> 04h   HOST_STATUS b1 -> 02h
  IRQ_STATUS b4 -> reinitialise the link and channels only.
Then clears iRAM (keeping the reset cause), sets up the host registers,
checksums the ROM, tests iRAM, configures the link controller and starts
Timer 2 and INT0.""",

0x07E1: """\
Checksum 0000h-3FFCh: 16-bit sum, compared with 3FFEh (low) and 3FFFh
(high).""",

0x0822: """\
iRAM test: each byte 01h-FFh is saved, written DAh and 25h, read back and
restored. Then byte 00h.""",

0x08BC: """\
Link controller setup. Pulse P3.3 to reset it, then write its indirect
registers: config C2h=28h, C4h=37h, table 80h-87h = 81h-88h,
table A0h-A7h = 97h, 80h-86h, C3h=01h. Everything except C4h is read
back. Any mismatch goes to link_error.""",

0x0BC2: """\
Per-channel handshake. For each channel, an indirect write 10h+n-1 = C0h.
Then for each channel: send 26 04 88 to 30h+n-1, send 66 to n-1 and expect
66 04 88 back (the value just written), then send 30 11 2B 11 2B (readings
invalid) to 30h+n-1.""",

0x0F7C: """\
Send channel R7's two readings. Message: 30, then two bytes for the reading
at WIN_E1+2(n-1), then two for WIN_E0+2(n-1), to destination 30h+n-1.
Each reading is 7 bits + odd parity, looked up in the conversion curve.
R5 bit 0 picks the range for the first, bit 1 for the second.
Parity error on the first reading: 30 11 2B 11 2B (5 bytes). On the second,
the first value is already in the FIFO and 11 2B 11 2B is appended, giving a
7-byte message (suspected bug, at 1005h).
Curve values: byte 0's low nibble is a decimal exponent, 60 entries per
decade. The other 3 nibbles are a mantissa whose encoding is unresolved.""",

0x10E8: """\
Reset entry. Clear REG_FC and CH_TOGGLE, set the stack, initialise, read the
config byte at 3FFDh.""",

0x1117: """\
Background loop. Runs the main poll between steps of a rolling self-test:
  1. ROM checksum, 20 bytes per step.
  2. R0/R1 test.
  3. iRAM write/read test (FFh, 00h), 16 bytes per step.
  4. iRAM 80h-DFh checksum, compared with the first pass.
  5. Link controller config read-back.
  6. Link loopback test.
  7. Stack sentinel: iRAM FFh must still be FFh.
Each failure sets error bits for the host.""",

0x1679: """\
Main poll. One pass: for each channel 8..1, if there is a command, a data
request (2xh) is answered immediately with send_readings, anything else
goes to the channel's state handler with R5 = command. A handler accepts the
command by clearing R5; a byte that arrived meanwhile is then fetched from
CHn_CMD. With no command, the handler runs with R5 = 0. Deferred data
requests are answered at the end of each channel's turn.

Passes repeat (via debug_mode_poll) and the routine only returns every 100
passes. In debug mode it never returns, which suspends the self-test.""",

0x1751: """\
End of a main poll pass (also entered directly in debug mode). Kick the
watchdog and start another pass. Every 100 passes, unless in debug mode:
report STAT21 to the host, update HEALTH_OUT (low if any channel is faulty,
toggling while ERROR/FAULT is set, otherwise high) and return.""",

0x178D: """\
State dispatch: the state value is a byte offset into the jump table, so
state = 3 x entry. R7 = channel, R5 = command byte (0 if none).""",

0x2CEC: """\
Handler for states 4Eh, 51h, 54h, 57h, 5Ah, 5Dh (channel not yet running).
Command 07h restarts the handshake.""",

0x2E34: """\
Fill channel n's 12-byte record at 80h + 12(n-1) from the window block:
  +0 type (WIN_E0 bits 6-4)   +1 WIN_E0 bits 3-0   +2..+7 WIN_E1..E6
  +8 WIN_E7 bits 5-4          +9 WIN_E8 bits 7-6   +A WIN_E8 bits 5-4
  +B WIN_E9
Bit fields are shifted down to the low bits.""",

0x35A7: """\
Debug monitor. Enter: host writes FCh to HOST_DBGCMD, we answer FCh.
Exit: FAh. In debug mode:
  8xh = write, Axh = read. Bits 0-3: iRAM, XRAM (@R0), link register,
  port (address < 2: P1, = 2: P2, > 2: P3).
Address from HOST_DBGADDR, data from HOST_DATA, reply on HOST_REPLY.
Address and data are echoed to ACK_E4/ACK_E5. SFRs other than the ports,
and program memory, are not reachable.""",
}

# Line comments.
COMMENTS = {
    0x2C60: 'BUG? writes bank 0 register R(n-1); 0788h uses code[n] here',
    0x000B: 'unused vectors: NOPs fall through to TIMER1',
    0x0F8E: 'R1 -> WIN_E1 + 2(n-1)',
    0x0F94: 'parity error: append 11 2B 11 2B',
    0x1005: 'BUG? first value already sent: message becomes 7 bytes',
    0x0FBB: 'strip parity, x2 for 2-byte entries',
    0x0FFF: 'R1 -> WIN_E0 + 2(n-1)',
    0x005B: 'R1 -> CHn_CMD',
    0x0067: 'R0 -> cmd[n]',
    0x0069: 'slot full?',
    0x0704: 'iRAM E0h/E1h preserved across the clear',
    0x070D: 'clear iRAM 01h-FFh',
    0x072E: 'A7h: signature for the host?',
    0x0038: 'register bank 1',
    0x005E: 'P=0: even parity -> error',
    0x10EF: 'stack in upper iRAM',
    0x10FD: 'config byte at 3FFDh',
    0x110F: 'stack sentinel',
    0x1111: 'stack sentinel',
    0x111A: 'CFG_BIT2: stay in the main poll, skip self-tests',
    0x1690: 'data request?',
    0x2DD4: 'pulse P3.1 while reading P1',
    0x2DE6: 'pulse P3.0+P3.1 while reading P1',
    0x08BF: 'reset pulse to link controller (P3.3)',
    0x08C6: 'end of reset pulse',
    0x07CE: 'Timer 2: high priority, enabled',
    0x07D2: 'reload FE80h',
    0x07DA: 'INT0: level triggered',
    0x0F91: 'parity odd?',
    0x1002: 'parity odd?',
}

# ---------------------------------------------------------------------------
# Data regions: (start, end, kind, title).
#  'bytes'  : DB rows of 16
#  'curve'  : 128 two-byte entries
#  'masks'  : DB row with per-byte comment

DATA = [
    (0x0006, 0x000B, 'bytes', 'Padding'),
    (0x001E, 0x0023, 'bytes', 'Padding'),
    (0x002E, 0x0030, 'bytes', 'Padding'),
    (0x0F70, 0x0F7C, 'bytes', 'Unreached code fragment'),
    (0x308F, 0x318E, 'bytes', 'Bit-reverse table: byte i holds i with its bits reversed (unreferenced)'),
    (0x318E, 0x3196, 'bytes', 'Channel masks: index n -> bit n-1 (index 0: FFh).\nIndex 8 (80h) is the first byte of the next table.'),
    (0x3196, 0x319F, 'bytes', 'Inverted channel masks: index n -> ~(bit n-1) (index 0: 80h)'),
    (0x319F, 0x31A7, 'bytes', 'Unreferenced'),
    (0x31A7, 0x32A7, 'curve', 'Conversion curve, entries 0-127 (second reading, R5 b1 = 0)'),
    (0x32A7, 0x33A7, 'curve', 'Conversion curve, entries 128-255 (second reading, R5 b1 = 1)'),
    (0x33A7, 0x34A7, 'curve', 'Conversion curve, entries -110..17 (first reading, R5 b0 = 0)'),
    (0x34A7, 0x35A7, 'curve', 'Conversion curve, entries 18-145 (first reading, R5 b0 = 1)'),
    (0x36C2, 0x36CA, 'bytes', 'Inverted bit masks (unreferenced)'),
    (0x36CA, 0x3FFD, 'bytes', 'Unused (zero)'),
    (0x3FFD, 0x3FFE, 'bytes', 'Config byte: b1 -> CFG_BIT1, b2 -> CFG_BIT2, nonzero -> 81h replies'),
    (0x3FFE, 0x4000, 'bytes', 'ROM checksum: 16-bit sum of 0000h-3FFCh, low byte first'),
]
