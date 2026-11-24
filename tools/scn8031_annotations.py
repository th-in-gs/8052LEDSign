# Annotations for the Signetics SCN8031H ROM dump (scn8031/scn8031.bin),
# used by tools/annotate.py:
#
#   python3 tools/annotate.py --annotations scn8031_annotations
#
# Everything here is inferred from how the code uses each address. Names are
# descriptive guesses, not names from any original source. See
# scn8031/ROM_ANALYSIS.md.
#
# The program runs entirely from internal ROM (no MOVX), so P0 and P2 are
# plain I/O ports, and P3.6/P3.7 (WR/RD) are used as outputs.

ROM = 'scn8031/scn8031.bin'
OUTPUT = 'scn8031/scn8031_annotated.lst'

IRAM = {
    0x3A: 'TX_BYTE',        # byte to send (serial_send)
    0x3B: 'OPTION_P23',     # A5h if P2.3 read high at reset, A0h if low
    0x10: 'B_STEPS',        # motor B: positions to move
    0x35: 'B_POSITION',     # motor B: carousel position, 01h-60h
    0x36: 'C_POS_HI',       # motor C: position, 0000h-0C60h
    0x37: 'C_POS_LO',
    0x41: 'PHASE_B',        # motor B pattern, P0 bits 0-3 (bit 3 always set)
    0x42: 'P1_SHADOW',      # P1 copy: low nibble = motor C pattern
    0x43: 'PHASE_A',        # motor A pattern, P0 bits 4-7
    0x44: 'P0_SHADOW',      # P0 copy
    0x0D: 'D_STEPS',        # motor D: steps to move (bank 1 R5)
    0x0E: 'PHASE_D',        # motor D pattern, P1 bits 4-7 (bank 1 R6)
    0x11: 'PHASE_C',        # motor C pattern, P1 bits 0-3 (bank 2 R1)
    0x38: 'C_SAVED_HI',     # motor C: position to return to after parking
    0x39: 'C_SAVED_LO',
}

BITS = {
    0x0A: 'PARITY_ODD',     # 21h.2: parity sense for the 9th serial bit
    0x2D: 'READ_MODE',      # 20h.5: D-commands return registers
    0x45: 'CMD_ERROR',      # 28h.5: command rejected
    0x50: 'SPEED0',         # 2Ah.0: speed class bit 0
    0x51: 'SPEED1',         # 2Ah.1: speed class bit 1
    0x55: 'B_DIR',          # 2Ah.5: motor B direction
    0x56: 'C_DIR',          # 2Ah.6: motor C direction
    0x57: 'A_DIR',          # 2Ah.7: motor A direction
    0xA0: 'SR_LOAD',        # P2.0: shift register load
    0xA1: 'SR_CLK',         # P2.1: shift register clock
    0xA2: 'SR_DATA',        # P2.2: shift register data in
    0xA4: 'PULSE_OUT',      # P2.4: pulsed during motor A's 0xC1 0x04 action
    0xA5: 'D_STOP_IN',      # P2.5: low = stop motor D, report an error
    0xA7: 'C_MOVING',       # P2.7: high while motor C moves
    0xB3: 'C_HOME',         # P3.3 (INT1 pin): motor C home switch, low = home
    0xB4: 'INTERLOCK',      # P3.4 (T0 pin): low = wait / restart
    0x16: 'PARKED',         # 22h.6: parked; host motion refused, panel keys live
    0x18: 'A_UNKNOWN',      # 23h.0: motor A position unknown or flag low
    0x19: 'A_FAULT',        # 23h.1: motor A flag edge not found
    0x1B: 'D_FAULT',        # 23h.3: P2.5 went low; motor D blocked
    0x42: 'D_STATE',        # 28h.2: motor D state (0 or 1)
    0x4E: 'ST_PARKED',      # 29h.6: status bit: parked
    0x58: 'A_STOP_ON_LOW',  # 2Bh.0: stop motor A 16 steps after flag goes low
    0x59: 'A_STOP_ON_HIGH', # 2Bh.1: stop motor A 16 steps after flag goes high
    0x5A: 'A_CAM_STATE',    # 2Bh.2: set by the 0xC1 0x04 action, cleared by 0x08
    0x60: 'C_HOMING',       # 2Ch.0: cut the motor C move short at the home switch
    0x66: 'D_DIR',          # 2Ch.6: motor D direction (1 = towards state 1)
    0x76: 'C_HOME_HIT',     # 2Eh.6: home switch seen during a motor C move
}

LABELS = {
    0x0000: 'RESET',
    0x0003: 'VEC_INT0',
    0x000B: 'VEC_TIMER0',
    0x001B: 'VEC_TIMER1',
    0x0023: 'VEC_SERIAL',
    0x0026: 'outputs_off',
    0x0064: 'motion_init',
    0x0129: 'run_move',
    0x0151: 'TIMER0_ISR',
    0x0185: 'TIMER1_ISR',
    0x01A6: 'post_move_timing',
    0x02DC: 'next_phase_a',
    0x02EE: 'output_phase_a',
    0x038A: 'next_phase_b',
    0x04C4: 'table_nibble',
    0x04DB: 'count_step',
    0x0B05: 'motion_command',
    0x0D5E: 'command_dispatch',
    0x09FC: 'cmd_C0',
    0x09BB: 'cmd_C1',
    0x0A54: 'cmd_Dx',
    0x0DCE: 'combined_move',
    0x0DF5: 'set_c_target',
    0x0F77: 'set_b_target',
    0x0F9F: 'sequence_speed_class',
    0x0CFD: 'auto_sequence',
    0x0D05: 'carousel_sequence',
    0x0AE7: 'park',
    0x01E8: 'd_to_state0_overdrive',
    0x01EE: 'd_to_state0',
    0x01F4: 'd_to_state1',
    0x01FE: 'run_d_move',
    0x0256: 'step_d',
    0x026C: 'd_step_tick',
    0x027C: 'check_d_stop',
    0x0325: 'check_a_flag',
    0x033B: 'a_stop_in_16',
    0x04B3: 'c_home_cutoff',
    0x053F: 'scan_keys',
    0x0567: 'check_interlock',
    0x0601: 'jog_a',
    0x0861: 'rehome_all',
    0x0896: 'a_pulse_and_advance',
    0x0A38: 'c0_park_bits',
    0x0B6F: 'key_handler',
    0x0C4C: 'start_auto_sequence',
    0x0E29: 'check_a_flag_idle',
    0x0E46: 'a_action_04',
    0x0E9D: 'a_action_08',
    0x0FE0: 'c_to_saved',
    0x0FE9: 'c_to_park',
    0x0FF2: 'short_delay',
    0x031A: 'ramp_a',
    0x03A1: 'output_phase_b',
    0x0434: 'next_phase_c',
    0x0443: 'output_phase_c',
    0x044D: 'check_int1_sensor',
    0x04CB: 'rotate_phase',
    0x04ED: 'ramp_lookup',
    0x067E: 'SERIAL_ISR',
    0x06F4: 'sweep_step',
    0x0736: 'loopback_test',
    0x074C: 'send_and_check_echo',
    0x076E: 'check_p25_input',
    0x0800: 'int0_soft_reset',
    0x080A: 'start',
    0x087C: 'serial_init',
    0x08AF: 'serial_send',
    0x08BF: 'main_loop',
    0x0969: 'timer0_alt',
    0x098A: 'read_shift_register',
    0x0CBF: 'move_to_target',
    0x0ED7: 'wait_polling_inputs',
    0x0F15: 'clear_ram',
}

SUMMARY = {
    0x0026: 'all outputs to idle',
    0x0129: 'run a move, waiting for it to finish',
    0x02DC: 'step phase A in the current direction',
    0x02EE: 'P0 high nibble <- motor A pattern',
    0x03A1: 'P0 low nibble <- motor B pattern',
    0x038A: 'next 3-phase pattern for motor B',
    0x04C4: 'A = table entry, high nibble if C=0, low if C=1',
    0x04DB: 'count down a step; C = 1 when done',
    0x0DF5: 'motor C target = position +/- 16h:17h, checked',
    0x0F77: 'motor B: shortest path to target A (1-60h)',
    0x0F9F: 'speed class for R7 in the carousel sequence (R7 <= 52h)',
    0x0434: 'step phase C in the current direction',
    0x0443: 'P1 low nibble <- phase C',
    0x04CB: 'next half-step pattern (table 04CCh)',
    0x06F4: 'next position of a back-and-forth sweep',
    0x074C: 'send TX_BYTE and check it comes back',
    0x087C: 'UART: mode 3, 9600 baud at 11.0592 MHz',
    0x08AF: 'send TX_BYTE with parity in the 9th bit',
    0x098A: 'read 8 bits from the external shift register',
    0x0CBF: 'move towards target position',
    0x0ED7: 'wait, polling the shift register inputs',
    0x0F15: 'clear iRAM 08h-42h, keep some flags',
    0x0AE7: 'carousel to 1, C to 960, D to state 1',
    0x01E8: 'motor D 96 steps towards state 0',
    0x01EE: 'motor D 74 steps towards state 0',
    0x01F4: 'motor D 74 steps towards state 1',
    0x0E46: 'motor A to flag rising edge, pulse P2.4',
    0x0E9D: 'motor A to flag falling edge',
    0x0FE0: 'motor C back to its saved position',
    0x0FE9: 'motor C to 960',
    0x0FF2: 'short delay',
    0x0861: 'outputs idle, wait for interlock, home C and B',
    0x0896: 'pulse P2.4, then motor A 88 steps',
    0x0601: 'jog motor A while key 5 or 6 is held',
    0x01A6: 'P3.5, P2.6 pulse, then settle timing',
    0x031A: 'motor A step period from ramp 057Dh',
    0x0A54: 'status byte reads',
}

BLOCKS = {
0x0000: """\
Signetics SCN8031H internal 4 KB ROM (marked ROMless; functionally an 8051). Annotated disassembly.

Generated by tools/annotate.py from scn8031/scn8031.bin and
tools/scn8031_annotations.py. All names and comments are inferred from how
the code uses each address. See scn8031/ROM_ANALYSIS.md.

Interrupt vectors: reset, INT0 (forces a reset), Timer 0, Timer 1 and the
serial port.""",

0x0003: """\
INT0: disable interrupts and jump to int0_soft_reset, which 'returns' to
address 0000h.""",

0x0026: """\
Put all outputs in their idle state: P0 and P1 high, P2 = E7h.""",

0x0064: """\
Homing at reset (called with motors idle, after the interlock is high).
Motor C: back off 50 half-steps, then drive up to 0D98h (3480) towards home
with C_HOMING set; c_home_cutoff ends the move 36-37 half-steps after the
switch (INT1) trips. Motor B: 99 single-step moves (just over one turn of
96) while C is parked past its switch; no sensor is read, so B probably
stalls against something C's overtravel puts in its path. Motor C: creep
back 2 half-steps at a time until the switch releases, then 12 more.
Position 0 is there.""",

0x01E8: """\
Motor D, P1 bits 4-7: a two-position mechanism about 74 half-steps between
states, state in D_STATE. Stepped from the motion loop (d_step_tick) at a
fixed rate. 96 steps towards state 0 overdrives it, presumably against a
hard stop. A move is refused once D_FAULT is set.""",

0x026C: """\
Motor D step, from the motion loop: count down a fixed delay (R4), then
check P2.5 and step. D_STEPS counts the steps.""",

0x027C: """\
P2.5 low on two successive steps: report it (check_p25_input) and cut the
remaining motor D move to at most 12 steps.""",

0x0325: """\
Motor A position flag: shift register bit 0 (in C). With A_STOP_ON_LOW set,
stop 16 steps after it goes low; with A_STOP_ON_HIGH, after it goes high.""",

0x033B: """\
Cut the remaining motor A move to 16 steps. If fewer remain, set 2Fh.3 so
run_move makes a second pass for the rest.""",

0x04B3: """\
While homing, once the switch has been seen, cut the remaining motor C
count to 24h steps, keeping the phase (bit 0).""",

0x053F: """\
Front-panel keys: report a change once the same non-zero value has been
read 5 times in a row (flag 2Ch.7 for key_handler).""",

0x0567: """\
Interlock: INTERLOCK (T0 pin) low, read twice, while not parked -> restart
the firmware, which re-homes everything.""",

0x0601: """\
Jog motor A while key 5 (one way) or key 6 (the other) is held: a short
move, then longer moves as long as the key stays down.""",

0x0A38: """\
For every accepted C0h command: second byte bit 6 = parity sense, bit 2 set
= unpark (clear PARKED, motor C back to its saved position), bit 2 clear =
park if not parked.""",

0x0B6F: """\
Front-panel key handler (keys = shift register bits 1-6, active-low).
While parked: keys 5/6 jog motor A, keys 3+4 start the automatic sequence,
key 3 cycles motor D, key 2 pulses P2.4 and advances motor A. With no host,
key 1 moves motor A 1056 steps. With a host connected, presses are reported
in status bit 29h.2 and byte 24h. While the automatic sequence runs, key 4
stops it (re-home and restart) and key 2 switches sequence.""",

0x0E29: """\
With the motor A option fitted, report motor A's flag reading low twice
(A_UNKNOWN and status error bits).""",

0x0E46: """\
C1h 04h: motor A forward until its flag goes high (at most 240h steps),
16 + 116 more, pulse P2.4, 88 more; sets A_CAM_STATE. Runs a_action_08 first
if A_CAM_STATE is set. No edge: A_FAULT, status error, park. Motor C goes
to 960 first and back afterwards. Refused without the P2.3 option.""",

0x0E9D: """\
C1h 08h: motor A forward (same direction as 04h) until its flag goes low
(at most 526h steps), then 16 + 900 more; clears A_CAM_STATE. No edge:
A_FAULT, status error, park. Refused without the P2.3 option.""",

0x0151: """\
Timer 0: steps motor A (P0 high nibble) or motor B (P0 low nibble),
whichever is moving. When bit 27h.7 is set, timer0_alt (post-move timing)
runs instead.""",

0x0185: """\
Timer 1: steps motor C (P1 low nibble). Register bank 2.""",

0x02DC: """\
Phase outputs. Each motor has a coil pattern, replaced by the next one from
a lookup table on each timer interrupt, and written to its nibble of P0 or
P1 through a shadow copy so the other nibble is kept. Outputs idle high, so
coils appear to be active-low.
  Motor A: P0 bits 4-7, half-step table at 04CCh.
  Motor B: P0 bits 0-3, 3-phase table at 039Ah, bit 3 always set.
  Motor C: P1 bits 0-3, half-step table at 04CCh.
  Motor D: P1 bits 4-7, half-step table at 04CCh (step_d).""",

0x038A: """\
Motor B, 3-phase: next pattern from the table at 039Ah, indexed by the low
3 bits. One direction cycles 1, 3, 2, 6, 4, 5 (6-step commutation). Entry 0
is the RET at 039Ah and entry 7 the first byte at 03A1h: overlapping code,
used only for invalid patterns.""",

0x04CB: """\
Half-step table at 04CCh, indexed by the current pattern: high nibble = next
pattern one way, low nibble = the other. From Eh: E 6 7 5 D 9 B A, i.e.
inverted 1 9 8 A 2 6 4 5, an 8-state half-step sequence. Entries 0-4 and F
overlap the instruction bytes at 04CCh-04D0h and 04DBh; they are invalid
patterns and still lead back into the cycle.""",

0x0B05: """\
Motion commands (first byte 00h-BFh):
  00-7F: motor B to target (second byte) and motor C by (bits 0-4) x 2,
         direction bit 6; speed class from bit 5 and second byte bit 7.
  80-8F: motor A, count (bits 0-2):second byte, direction bit 3.
  90-9F: motor C, count (bits 0-2):second byte, direction bit 3.
  A0-AF: motor B to target (second byte), speed class bits 0-1.
  B0-BF: rejected.""",

0x0D5E: """\
Command dispatch on the first byte: 00h-BFh motion_command, C0h cmd_C0,
C1h cmd_C1, D0h-DFh cmd_Dx, anything else rejected. Then a 1-byte reply:
TX_BYTE, normally the status byte at 29h.""",

0x09FC: """\
C0h xx: 00 = nothing else; 80 or C0 = enter echo mode; 01 = re-initialise
and accept all frames; 02 = leave read mode. Bits 2 and 6 are masked off
here and applied by c0_park_bits.""",

0x09BB: """\
C1h xx: 40 = enter read mode; 20 = motor D to state 1; 10 = park;
08, 04 = motor A actions (a_action_08, a_action_04). Refused while parked,
in read mode or after a motor A fault.""",

0x0A54: """\
Dxh 00: status reads. Normally: reply with 22h (D0, summary), 23h (D1,
errors), 24h (D2, keys), 25h (D4, communication), 26h (D8, fault code) or
OPTION_P23 (DE), copy it to the snapshot at 30h-34h, and clear what was
read (0A93h). In read mode: reply with the snapshot, clearing nothing.""",

0x01A6: """\
After a motor B/C move at speed class 1-3: P3.5 = class 1, P2.6 low for one
Timer 0 period (byte 0 of the entry at 01DFh), then mark the mechanism busy.
timer0_alt then runs byte 1's period (then P0.3 high, ending motor B's
settle) and byte 2's (then the busy flag clears). Class 0 uses a fixed
delay instead (00C9h).""",

0x04ED: """\
Step period from a ramp table: acceleration index R4 (rising to the ramp
length R1) or steps remaining R3, whichever is smaller. For motor B
(2Dh.3), the step where they are equal uses entry R4 + R1, from the second
table at 05E3h. The entry x B is subtracted from Timer 0.""",

0x0928: """\
Unprompted status report: when an event is pending (28h.3) and the
transmitter is free, send 29h with bit 5 clear (unless a command reply is
pending), then reset 29h to 20h.""",

0x0F77: """\
Motor B, 96-position circular axis. Target must be 01h-60h. Distance from
B_POSITION; if more than 30h, go the other way (60h - distance) and flip
the direction. Result in B_STEPS.""",

0x0F9F: """\
Speed class for R7 in the scripted carousel sequence (0D05h), where R7 never
exceeds 52h: byte R7/4 of the table at 0FBEh (at most byte 14h of 25), bit
pair R7 mod 4, into SPEED0/SPEED1. The sweep at 06F4h does not use it.""",

0x0CFD: """\
Automatic sequences, chosen by flag 20h.2: set = sweep (sweep_step), clear =
scripted carousel sequence (carousel_sequence).""",

0x0D05: """\
Scripted carousel sequence. R6 counts down from 30h per call while R7 counts
up, and motor C moves 18h half-steps per call, its direction flipping each
cycle. When R6 runs out, the carousel moves by a fixed amount: 26h positions
at R7 = 1, 10h at R7 = 2, 18h at R7 = 32h, otherwise 23h back the other way
with R7 reset to 0. R7 peaks at 52h. Purpose open (homing, self-test or a
fixed presentation pattern).""",

0x067E: """\
Serial interrupt. Register bank 1. The UART runs in mode 3: 8 data bits plus
a 9th bit used as parity (sense set by PARITY_ODD).
  Transmit done: flag 21h.1.
  Echo mode (20h.4): received bytes are sent straight back out with the same
  9th bit. With 20h.7 set (loopback test), the first byte is captured in 00h
  instead. After 8 echoed bytes, echo mode ends and 21h.0 is set. main_loop
  enters echo mode after a C0h 80h or C0h C0h frame.
  Otherwise: check parity, then store a 2-byte frame: first byte at 07h,
  second at 06h: R7 and R6 of bank 0, the main loop's registers. Until 21h.0 is set, frames whose first byte
  is not C0h are ignored.""",

0x06F4: """\
Sweep: step a position index between 01h and 83h, reversing direction at
each end. Used for a back-and-forth scanning motion.""",

0x0736: """\
Loopback test: send AAh, 00h, FEh and 55h, and check each comes back.""",

0x080A: """\
Reset entry. Clear RAM (keeping a few flags), then check for a loopback on
the serial pins: TXD is toggled and RXD watched. With a loopback, measure
the INT0 pulse with Timer 0 and run loopback_test, then stop. Otherwise
start normally.""",

0x087C: """\
UART setup: Timer 1 auto-reload with TH1 = FDh (9600 baud at 11.0592 MHz),
SCON = D0h (mode 3, receive enabled), serial interrupt enabled, Timer 0 at
high priority.""",

0x08BF: """\
Main loop. Reads the shift-register inputs, runs any pending motion, checks
the P2.5 input, and handles received frames. Frame C0h 80h or C0h C0h sets
the parity sense from bit 6, enters echo mode and replies. Status is driven on P3.7 (RD pin)
and, inverted, on P3.6 (WR pin).""",

0x098A: """\
Read an external parallel-in shift register (e.g. a 74x165): pulse SR_LOAD,
then clock in 8 bits from SR_DATA, MSB first.""",

0x0F15: """\
Clear iRAM 08h-42h, keeping flags 2Bh.2 and 28h.2. Then test P2.3: if it
reads high, OPTION_P23 = A5h, otherwise A0h (an option or presence input).""",
}

COMMENTS = {
    0x0003: 'disable interrupts',
    0x0805: 'interrupts off; RETI pops 0000h',
    0x080C: 'stack above the variables',
    0x0819: 'P2.3 option present?',
    0x06A8: 'echo with the same 9th bit',
    0x06AC: 'echo the byte',
    0x0904: 'echo mode on, other 20h flags cleared',
    0x06B3: 'parity of the data byte...',
    0x06B5: '...compared with the 9th bit',
    0x08B3: 'parity of TX_BYTE...',
    0x08B9: '...into the 9th bit',
    0x095E: 'status out on P3.7',
    0x0965: 'inverted status out on P3.6',
    0x044D: 'debounced: read INT1 twice',
    0x02AF: 'motor A count x 3: one unit = 3 half-steps',
    0x035E: 'motor B: 2 steps per position',
    0x03B9: 'P0.3 low: motor B settling',
}

TABLE_COMMENTS = {
    0x057D: 'A = ramp table 057Dh',
    0x058A: 'A = motor C period adjustment',
    0x05C5: 'A = ramp table 05C5h',
    0x039A: 'A = 3-phase table entry',
    0x04CC: 'A = half-step table entry',
    0x01DF: 'A = post-move timing',
    0x01E2: 'A = post-move timing',
    0x01E5: 'A = post-move timing',
    0x0FBE: 'A = packed speed classes',
}

DATA = [
    (0x0008, 0x000B, 'bytes', 'Padding'),
    (0x000E, 0x0013, 'bytes', 'Padding'),
    (0x001E, 0x0023, 'bytes', 'Padding'),
    (0x01DF, 0x01E8, 'bytes', 'Post-move timing for speed classes 1-3: P2.6 pulse length, then two Timer 0 periods\n(bank 1 R2: until P0.3 goes high; R3: until the busy flag clears)'),
    (0x039B, 0x03A1, 'bytes', 'Motor B 3-phase table, entries 1-6 (entry 0 is the RET at 039Ah, entry 7 the byte at 03A1h)'),
    (0x04D1, 0x04DB, 'bytes', 'Half-step table at 04CCh, entries 5-14 (the other entries overlap code)'),
    (0x057D, 0x058A, 'bytes', 'Motor A ramp, 13 entries: 98h, 3Fh, 31h, 24h ... 14h (used by ramp_a)'),
    (0x058A, 0x05C5, 'bytes', 'Motor C period profile, indexed by R5: each move uses three consecutive entries\n'
                              '(start, after 12 steps, last 7 steps). Entry x B0h or 40h is subtracted from Timer 1.\n'
                              'The repeating 1Ch 12h 0Bh run looks like filler. Index 39h = 00h, 3Ah = B7h.'),
    (0x05C5, 0x0601, 'bytes', 'Motor B ramp tables.\n'
                              '05C5h, 29 entries: C9h, 64h, 4Ah, 3Eh, 36h ... about 96/sqrt(n) + 4.\n'
                              'Step delays proportional to 1/sqrt(n) give constant acceleration.\n'
                              '05E3h: ACh, 7Eh, 78h, 6Dh, 64h ... for the one step where acceleration\n'
                              'turns into deceleration (index R4 + R1). 0600h (48h): the last step.'),
    (0x07BB, 0x0800, 'bytes', 'Unprogrammed (FFh) up to the 2 KB boundary at 0800h'),
    (0x0FBE, 0x0FD7, 'bytes', 'Carousel sequence speed classes: 2 bits per R7 value, 4 per byte, 100 entries\n(R7 only reaches 52h; see sequence_speed_class)'),
    (0x0FFA, 0x1000, 'bytes', 'Padding (FFh) and a final 00h'),
]
