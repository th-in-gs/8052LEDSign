#!/usr/bin/env python3
# Produce an annotated disassembly of an 8051 ROM dump.
#
# Usage:
#   python3 tools/annotate.py [--annotations MODULE] [rom.bin] [output.lst]
#
# MODULE is an annotation module in this directory (default:
# romdump_annotations, for the OKI MSM83C154 dump). It supplies names,
# comments and data layouts, plus the ROM and output paths used when they
# are not given. Every field is optional; see DEFAULTS below.
#
# Besides the hand-written annotations, recognisable patterns are annotated
# automatically when the module enables them: external and link controller
# register accesses, per-channel array pointers, table lookups and state
# assignments through a jump table.

import importlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dis51                          # noqa: E402

DEFAULTS = dict(
    ROM=None,               # dump path, relative to the repository root
    OUTPUT=None,            # listing path, relative to the repository root
    ENTRIES=[],             # extra trace entry points
    JUMP_TABLE=None,        # address of an LJMP table indexed by state value
    JUMP_TABLE_ENTRIES=0,
    HANDLER_NOTE='',        # appended to automatic state handler headers
    CHANNEL_ARRAYS={},      # base (MOV A,#base / ADD A,R7) -> array name
    EXT_READ={},            # MOVX @Ri address -> register name (reads)
    EXT_WRITE={},           # ...and writes
    LINK_REGS={},           # MOVX @DPTR with DPH = 00h: register -> name
    LINK_COMMANDS={},
    TABLE_COMMENTS={},      # MOVC A,@A+DPTR table address -> comment
    RECORD_BASE=None,       # 'MUL AB / ADD A,#base' record pattern
    RECORD_COMMENT='',
    IRAM={},
    BITS={},
    LABELS={},
    SUMMARY={},
    BLOCKS={},
    COMMENTS={},
    DATA=[],
)


class Annotations:
    def __init__(self, module):
        self.module = module

    def __getattr__(self, name):
        return getattr(self.module, name, DEFAULTS[name])


A = None   # set in main()

COMMENT_COLUMN = 44


HANDLER_NAMES = {}   # filled in by main(): handler address -> state_XXh


def label_name(addr):
    if addr in A.LABELS:
        return A.LABELS[addr]
    return HANDLER_NAMES.get(addr, f'L{addr:04X}')


def rename_labels(text):
    return re.sub(r'\bL([0-9A-F]{4})\b',
                  lambda m: label_name(int(m.group(1), 16)), text)


def state_target(rom, state):
    """Handler address for a state value (a byte offset into the jump table)."""
    if A.JUMP_TABLE is None or state % 3 or state // 3 >= A.JUMP_TABLE_ENTRIES:
        return None
    a = A.JUMP_TABLE + state
    if rom[a] != 0x02:
        return None
    return (rom[a + 1] << 8) | rom[a + 2]


class Tracker:
    """Very small linear tracker of constant register values. Reset at every
    branch target, so it only reasons about straight-line code."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.A = None          # int constant, or ('chan', base)
        self.R = {0: None, 1: None}
        self.DPH = None
        self.DPL = None
        self.DPTR_TABLE = None
        self.prev = None
        self.record = False

    def dptr_link_reg(self):
        if self.DPH == 0 and isinstance(self.DPL, int):
            return self.DPL
        return None


def channel_desc(base, kind='ptr'):
    if base in A.CHANNEL_ARRAYS:
        return f'{A.CHANNEL_ARRAYS[base]}[n]'
    if base == 0xEF:
        return 'CHn_CMD'
    if base == 0xE7:
        return 'CHn_CFG'
    if base == 0xFF:
        return 'n-1'
    return f'{base:02X}h+n'


def auto_comment(rom, addr, text, t, facts):
    """Return an automatic comment for the instruction, updating tracker t."""
    c = None
    prev, t.prev = t.prev, text
    if (A.RECORD_BASE is not None and prev == 'MUL AB'
            and text == f'ADD A,#{A.RECORD_BASE:02X}h'):
        t.A = None
        t.record = True
        return A.RECORD_COMMENT
    m = re.match(r'ADD A,#([0-9A-F]{2})h$', text)
    if m and t.record:
        t.record = False
        t.A = None
        return f'record byte {int(m.group(1), 16):X}'
    t.record = False
    m = re.match(r'MOV A,#([0-9A-F]{2})h$', text)
    if m:
        t.A = int(m.group(1), 16)
        return None
    m = re.match(r'(SETB|CLR) ACC\.([0-7])$', text)
    if m:
        if isinstance(t.A, int):
            bit = 1 << int(m.group(2))
            t.A = (t.A | bit) if m.group(1) == 'SETB' else (t.A & ~bit)
        else:
            t.A = None
        return None
    if text == 'CLR A':
        t.A = 0
        return None
    if text == 'ADD A,R7' and isinstance(t.A, int) and A.CHANNEL_ARRAYS:
        t.A = ('chan', t.A)
        return 'A = n-1' if t.A[1] == 0xFF else f'A = {t.A[1]:02X}h+n'
    m = re.match(r'MOV R([01]),#([0-9A-F]{2})h$', text)
    if m:
        t.R[int(m.group(1))] = int(m.group(2), 16)
        return None
    m = re.match(r'MOV R([01]),A$', text)
    if m:
        t.R[int(m.group(1))] = t.A
        if isinstance(t.A, tuple):
            return f'R{m.group(1)} -> {channel_desc(t.A[1])}'
        return None
    m = re.match(r'MOV R([01]),', text)
    if m:
        t.R[int(m.group(1))] = None
    m = re.match(r'MOV DPH,#([0-9A-F]{2})h$', text)
    if m:
        t.DPH = int(m.group(1), 16)
        t.DPTR_TABLE = None
        return None
    m = re.match(r'MOV DPL,#([0-9A-F]{2})h$', text)
    if m:
        t.DPL = int(m.group(1), 16)
        return None
    m = re.match(r'MOV DPTR,#([0-9A-F]{4})h$', text)
    if m:
        v = int(m.group(1), 16)
        t.DPH, t.DPL, t.DPTR_TABLE = v >> 8, v & 0xFF, v
        return None
    if text.startswith(('MOV DPL,', 'MOV DPH,', 'INC DPTR')):
        t.DPH = t.DPL = t.DPTR_TABLE = None

    # External register accesses through @R0/@R1.
    m = re.match(r'MOVX (A,@R([01])|@R([01]),A)$', text)
    if m and not (A.EXT_READ or A.EXT_WRITE):
        if m.group(2) is not None:
            t.A = None
        return None
    if m:
        reading = m.group(2) is not None
        r = int(m.group(2) or m.group(3))
        v = t.R[r]
        names = A.EXT_READ if reading else A.EXT_WRITE
        if isinstance(v, int):
            name = names.get(v, f'ext {v:02X}h')
            facts.setdefault('ext', set()).add(name)
            if reading:
                c = f'A <- {name}'
            else:
                c = f'{name} <- ' + (f'{t.A:02X}h' if isinstance(t.A, int) else 'A')
        elif isinstance(v, tuple):
            base = v[1]
            if base == 0xEF:
                c = 'A <- CHn_CMD' if reading else 'CHn_CMD <- A'
            elif base == 0xE7:
                c = 'CHn_CFG <- A' if not reading else 'A <- WIN'
            else:
                c = f'ext {base:02X}h+n'
        if reading:
            t.A = None
        return c

    # Link controller accesses through DPTR.
    if text in ('MOVX @DPTR,A', 'MOVX A,@DPTR'):
        reg = t.dptr_link_reg() if A.LINK_REGS else None
        if reg is None:
            if text == 'MOVX A,@DPTR':
                t.A = None
            return None
        name = A.LINK_REGS.get(reg, f'LINK_{reg:02X}')
        if text == 'MOVX A,@DPTR':
            t.A = None
            return f'A <- {name}'
        v = t.A
        if reg == 0x03 and isinstance(v, int):
            return f'{name} <- {v:02X}h: {A.LINK_COMMANDS.get(v, "?")}'
        if reg == 0x08 and isinstance(v, int):
            facts.setdefault('fifo', []).append(v)
            return f'{name} <- {v:02X}h'
        if reg == 0x02 and isinstance(v, int):
            if v & 0x08:
                return f'{name} <- {v:02X}h: select indirect {v & ~0x08:02X}h for read'
            return f'{name} <- {v:02X}h: write LINK_IDATA to indirect {v:02X}h'
        if reg == 0x02 and isinstance(v, tuple):
            return f'{name} <- {v[1]:02X}h+n: write LINK_IDATA to indirect {v[1] + 1:02X}h+n-1'
        if reg == 0x0A and isinstance(v, tuple):
            dest = '30h+n-1' if v[1] == 0x2F else ('n-1' if v[1] == 0xFF else '?')
            return f'{name} <- {dest}'
        return f'{name} <- ' + (f'{v:02X}h' if isinstance(v, int) else 'A')

    if text == 'MOVC A,@A+DPTR':
        tbl = t.DPTR_TABLE
        t.A = None
        return A.TABLE_COMMENTS.get(tbl)

    # Per-channel array accesses through R0.
    m = re.match(r'MOV @R0,#([0-9A-F]{2})h$', text)
    if m and isinstance(t.R[0], tuple):
        v = int(m.group(1), 16)
        arr = A.CHANNEL_ARRAYS.get(t.R[0][1])
        if arr == 'state':
            facts.setdefault('states', set()).add(v)
            tgt = state_target(rom, v)
            return f'state[n] := {v:02X}h' + (f' -> {label_name(tgt)}' if tgt else '')
        if arr:
            return f'{arr}[n] := {v:02X}h'
    if text == 'MOV @R0,A' and isinstance(t.R[0], tuple):
        arr = A.CHANNEL_ARRAYS.get(t.R[0][1])
        if arr:
            return f'{arr}[n] := A'
    if text == 'MOV A,@R0' and isinstance(t.R[0], tuple):
        arr = A.CHANNEL_ARRAYS.get(t.R[0][1])
        t.A = None
        if arr:
            return f'A = {arr}[n]'
        return None

    m = re.match(r'LCALL L([0-9A-F]{4})$', text)
    if m:
        tgt = int(m.group(1), 16)
        facts.setdefault('calls', []).append(tgt)
        t.A = None
        return A.SUMMARY.get(tgt)

    # Anything else that writes A makes it unknown.
    if re.match(r'(MOV A,|ADD|ADDC|SUBB|ORL A|ANL A|XRL A|INC A|DEC A|RL|RR|'
                r'SWAP|CPL A|DA|MUL|DIV|XCH|POP ACC|MOVC)', text):
        t.A = None
    return None


def format_line(addr, rom, n, text, comment):
    hexb = ' '.join(f'{rom[addr + i]:02X}' for i in range(n))
    line = f'  {addr:04X}  {hexb:<9}  {rename_labels(text)}'
    if comment:
        line = line.ljust(COMMENT_COLUMN) + f' ; {comment}'
    return line


def block(text):
    return [''] + [f'; {l}'.rstrip() for l in text.split('\n')]


def data_lines(rom, start, end, kind, title):
    out = block(title)
    if kind == 'curve':
        for i in range(0, (end - start) // 2, 4):
            ents = []
            for j in range(i, min(i + 4, (end - start) // 2)):
                a = start + 2 * j
                ents.append(f'{rom[a]:02X} {rom[a + 1]:02X}')
            out.append(f'  {start + 2 * i:04X}  DB {",  ".join(ents):<34} ; idx {i:3d}-{i + len(ents) - 1}')
        return out
    chunk = rom[start:end]
    if len(chunk) > 32 and not any(chunk):
        out.append(f'  {start:04X}  DS {len(chunk)}  ; {len(chunk)} zero bytes, to {end - 1:04X}h')
        return out
    for i in range(0, len(chunk), 16):
        out.append(f'  {start + i:04X}  DB ' + ', '.join(f'{b:02X}h' for b in chunk[i:i + 16]))
    return out


def main():
    global A
    args = sys.argv[1:]
    module = 'romdump_annotations'
    if len(args) >= 2 and args[0] == '--annotations':
        module, args = args[1], args[2:]
    A = Annotations(importlib.import_module(module))
    root = os.path.join(HERE, '..')
    rom_path = args[0] if len(args) > 0 else (A.ROM and os.path.join(root, A.ROM))
    out_path = args[1] if len(args) > 1 else (A.OUTPUT and os.path.join(root, A.OUTPUT))
    if not rom_path or not out_path:
        sys.exit('ROM and output paths are needed (or ROM/OUTPUT in the annotation module).')
    rom = open(rom_path, 'rb').read()

    dis51.IRAM_NAMES.update(A.IRAM)
    dis51.BIT_NAMES.update(A.BITS)
    code, labels, xrefs, _ = dis51.trace(rom, A.ENTRIES)

    data_at = {d[0]: d for d in A.DATA}
    handler_states = {}
    for k in range(A.JUMP_TABLE_ENTRIES):
        tgt = state_target(rom, 3 * k)
        if tgt is not None:
            handler_states.setdefault(tgt, []).append(3 * k)
    for tgt, states in handler_states.items():
        HANDLER_NAMES[tgt] = f'state_{states[0]:02X}h'

    # Pass 1: comments and per-routine facts.
    comments = {}
    facts_by_routine = {}
    routine = None
    t = Tracker()
    for addr in sorted(code):
        if addr in labels:
            t.reset()
        if addr in A.BLOCKS or addr in handler_states or 'call' in labels.get(addr, ()):
            routine = addr
        facts = facts_by_routine.setdefault(routine, {})
        n, text, _, kind = code[addr]
        c = auto_comment(rom, addr, text, t, facts)
        if addr in A.COMMENTS:
            hand = A.COMMENTS[addr]
            c = hand + (f' ({c})' if c and c != hand else '')
        comments[addr] = c
        if kind in ('jmp', 'ret', 'ijmp'):
            t.reset()

    # Pass 2: output.
    out = []
    addr = 0
    while addr < len(rom):
        if addr in data_at and addr not in code:
            s, e, kind, title = data_at[addr]
            out += data_lines(rom, s, e, kind, title)
            addr = e
            continue
        if addr in code:
            n, text, _, kind = code[addr]
            header = []
            if addr in A.BLOCKS:
                header += block(A.BLOCKS[addr])
            if addr in handler_states and addr not in A.BLOCKS:
                st = ', '.join(f'{s:02X}h' for s in handler_states[addr])
                header += block(f'State handler for state {st}.' + (f' {A.HANDLER_NOTE}' if A.HANDLER_NOTE else ''))
            if addr in handler_states or (addr in labels and 'call' in labels[addr]):
                f = facts_by_routine.get(addr, {})
                summary = []
                if f.get('states'):
                    summary.append('Sets state: ' + ', '.join(f'{s:02X}h' for s in sorted(f['states'])))
                if f.get('calls'):
                    seen = []
                    for c in f['calls']:
                        if c not in seen:
                            seen.append(c)
                    summary.append('Calls: ' + ', '.join(label_name(c) for c in seen))
                if summary:
                    if not header:
                        header.append('')
                    header += [f';   {s}' for s in summary]
            out += header
            if addr in labels:
                xs = sorted(xrefs[addr])
                more = f' +{len(xs) - 6}' if len(xs) > 6 else ''
                frm = ' '.join(f'{x:04X}' for x in xs[:6])
                if out and out[-1] != '' and not out[-1].startswith(';'):
                    out.append('')
                lab = f'{label_name(addr)}:'
                out.append(f'{lab:<24}; from {frm}{more}' if xs else lab)
            out.append(format_line(addr, rom, n, text, comments.get(addr)))
            if kind in ('jmp', 'ret'):
                out.append('')
            addr += n
            continue
        # Unreached bytes not covered by a DATA entry.
        start = addr
        while addr < len(rom) and addr not in code and addr not in data_at:
            addr += 1
        out += data_lines(rom, start, addr, 'bytes', f'{addr - start} bytes not reached by the trace')

    text = '\n'.join(re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).split('\n'))
    with open(out_path, 'w') as fh:
        fh.write(text.lstrip('\n') + '\n')
    print(f'Wrote {out_path}: {len(text.splitlines())} lines, '
          f'{sum(code[a][0] for a in code)} code bytes.', file=sys.stderr)


if __name__ == '__main__':
    main()
