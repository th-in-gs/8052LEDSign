#!/usr/bin/env python3
# Minimal recursive-descent 8051 disassembler for analysing a ROM dump.
import sys, collections

SFR = {0x80:'P0',0x81:'SP',0x82:'DPL',0x83:'DPH',0x87:'PCON',0x88:'TCON',0x89:'TMOD',
0x8A:'TL0',0x8B:'TL1',0x8C:'TH0',0x8D:'TH1',0x90:'P1',0x98:'SCON',0x99:'SBUF',0xA0:'P2',
0xA8:'IE',0xB0:'P3',0xB8:'IP',0xC8:'T2CON',0xCA:'RCAP2L',0xCB:'RCAP2H',0xCC:'TL2',0xCD:'TH2',
0xD0:'PSW',0xE0:'ACC',0xF0:'B',0xF8:'IOCON'}
BITSFR = {0x88:['IT0','IE0','IT1','IE1','TR0','TF0','TR1','TF1'],
0x98:['RI','TI','RB8','TB8','REN','SM2','SM1','SM0'],
0xA8:['EX0','ET0','EX1','ET1','ES','ET2','IE.6','EA'],
0xB0:['RXD','TXD','INT0','INT1','T0','T1','WR','RD'],
0xB8:['PX0','PT0','PX1','PT1','PS','PT2','IP.6','IP.7'],
0xC8:['CP_RL2','C_T2','TR2','EXEN2','TCLK','RCLK','EXF2','TF2'],
0xD0:['P','PSW.1','OV','RS0','RS1','F0','AC','CY']}

# Optional symbol names, filled in by tools that import this module.
IRAM_NAMES = {}   # direct address (< 0x80) -> name
BIT_NAMES = {}    # bit address -> name

def dname(a):
    if a in SFR: return SFR[a]
    if a in IRAM_NAMES: return IRAM_NAMES[a]
    if a < 0x80: return f'{a:02X}h'
    return f'SFR_{a:02X}'
def bname(b):
    if b in BIT_NAMES: return BIT_NAMES[b]
    if b < 0x80: return f'{0x20 + (b>>3):02X}h.{b&7}'
    base = b & 0xF8
    if base in BITSFR: return BITSFR[base][b&7]
    return f'{dname(base)}.{b&7}'

def decode(rom, pc):
    """Return (length, text, targets, kind) kind in {'', 'jmp','ret','call','cond','ijmp'}"""
    op = rom[pc]
    b1 = rom[(pc+1) % len(rom)]; b2 = rom[(pc+2) % len(rom)]
    rel = lambda x, n: (pc + n + (x - 256 if x > 127 else x)) & 0xFFFF
    rn = f'R{op & 7}'; ri = f'@R{op & 1}'
    lo = op & 0x0F; hi = op >> 4
    if lo == 1:
        t = ((pc + 2) & 0xF800) | ((op & 0xE0) << 3) | b1
        return (2, f'{"AJMP" if not (op & 0x10) else "ACALL"} L{t:04X}', [t], 'jmp' if not (op & 0x10) else 'call')
    A = {0x00:(1,'NOP'),0x03:(1,'RR A'),0x04:(1,'INC A'),0x13:(1,'RRC A'),0x14:(1,'DEC A'),
         0x22:(1,'RET'),0x23:(1,'RL A'),0x32:(1,'RETI'),0x33:(1,'RLC A'),0x73:(1,'JMP @A+DPTR'),
         0x83:(1,'MOVC A,@A+PC'),0x84:(1,'DIV AB'),0x93:(1,'MOVC A,@A+DPTR'),0xA3:(1,'INC DPTR'),
         0xA4:(1,'MUL AB'),0xA5:(1,'DB A5h ; reserved'),0xB3:(1,'CPL C'),0xC3:(1,'CLR C'),0xC4:(1,'SWAP A'),
         0xD3:(1,'SETB C'),0xD4:(1,'DA A'),0xE0:(1,'MOVX A,@DPTR'),0xE4:(1,'CLR A'),
         0xF0:(1,'MOVX @DPTR,A'),0xF4:(1,'CPL A')}
    if op in A:
        n, t = A[op]
        kind = {'RET':'ret','RETI':'ret','JMP @A+DPTR':'ijmp'}.get(t, '')
        return (n, t, [], kind)
    if op == 0x02: t = (b1<<8)|b2; return (3, f'LJMP L{t:04X}', [t], 'jmp')
    if op == 0x12: t = (b1<<8)|b2; return (3, f'LCALL L{t:04X}', [t], 'call')
    if op == 0x90: return (3, f'MOV DPTR,#{(b1<<8)|b2:04X}h', [], '')
    if op == 0x80: t = rel(b1,2); return (2, f'SJMP L{t:04X}', [t], 'jmp')
    if op in (0x40,0x50,0x60,0x70):
        t = rel(b1,2); return (2, f'{ {0x40:"JC",0x50:"JNC",0x60:"JZ",0x70:"JNZ"}[op]} L{t:04X}', [t], 'cond')
    if op in (0x10,0x20,0x30):
        t = rel(b2,3); return (3, f'{ {0x10:"JBC",0x20:"JB",0x30:"JNB"}[op]} {bname(b1)},L{t:04X}', [t], 'cond')
    bitops = {0x72:'ORL C,{}',0x82:'ANL C,{}',0x92:'MOV {},C',0xA0:'ORL C,/{}',0xA2:'MOV C,{}',
              0xB0:'ANL C,/{}',0xB2:'CPL {}',0xC2:'CLR {}',0xD2:'SETB {}'}
    if op in bitops: return (2, bitops[op].format(bname(b1)), [], '')
    if op == 0x75: return (3, f'MOV {dname(b1)},#{b2:02X}h', [], '')
    if op == 0x85: return (3, f'MOV {dname(b2)},{dname(b1)}', [], '')
    if op in (0x43,0x53,0x63):
        return (3, f'{ {0x43:"ORL",0x53:"ANL",0x63:"XRL"}[op]} {dname(b1)},#{b2:02X}h', [], '')
    if op in (0x42,0x52,0x62):
        return (2, f'{ {0x42:"ORL",0x52:"ANL",0x62:"XRL"}[op]} {dname(b1)},A', [], '')
    if op == 0xB4: t = rel(b2,3); return (3, f'CJNE A,#{b1:02X}h,L{t:04X}', [t], 'cond')
    if op == 0xB5: t = rel(b2,3); return (3, f'CJNE A,{dname(b1)},L{t:04X}', [t], 'cond')
    if op in (0xB6,0xB7): t = rel(b2,3); return (3, f'CJNE {ri},#{b1:02X}h,L{t:04X}', [t], 'cond')
    if 0xB8 <= op <= 0xBF: t = rel(b2,3); return (3, f'CJNE {rn},#{b1:02X}h,L{t:04X}', [t], 'cond')
    if op == 0xD5: t = rel(b2,3); return (3, f'DJNZ {dname(b1)},L{t:04X}', [t], 'cond')
    if 0xD8 <= op <= 0xDF: t = rel(b1,2); return (2, f'DJNZ {rn},L{t:04X}', [t], 'cond')
    if op in (0xC0,0xD0): return (2, f'{"PUSH" if op==0xC0 else "POP"} {dname(b1)}', [], '')
    if op in (0xE2,0xE3): return (1, f'MOVX A,{ri}', [], '')
    if op in (0xF2,0xF3): return (1, f'MOVX {ri},A', [], '')
    if op in (0xD6,0xD7): return (1, f'XCHD A,{ri}', [], '')
    # Regular ALU rows: lo 4=#imm (or A), 5=dir, 6/7=@Ri, 8-F=Rn
    rows = {0x0:'INC',0x1:'DEC',0x2:'ADD A,',0x3:'ADDC A,',0x4:'ORL A,',0x5:'ANL A,',0x6:'XRL A,',
            0x9:'SUBB A,',0xC:'XCH A,',0xE:'MOV A,'}
    if hi in rows:
        m = rows[hi]
        if hi in (0x0,0x1):
            if lo == 5: return (2, f'{m} {dname(b1)}', [], '')
            if lo in (6,7): return (1, f'{m} {ri}', [], '')
            if lo >= 8: return (1, f'{m} {rn}', [], '')
        else:
            if lo == 4: return (2, f'{m}#{b1:02X}h', [], '')
            if lo == 5: return (2, f'{m}{dname(b1)}', [], '')
            if lo in (6,7): return (1, f'{m}{ri}', [], '')
            if lo >= 8: return (1, f'{m}{rn}', [], '')
    if hi == 0x7:
        if lo == 4: return (2, f'MOV A,#{b1:02X}h', [], '')
        if lo in (6,7): return (2, f'MOV {ri},#{b1:02X}h', [], '')
        if lo >= 8: return (2, f'MOV {rn},#{b1:02X}h', [], '')
    if hi == 0x8:
        if lo in (6,7): return (2, f'MOV {dname(b1)},{ri}', [], '')
        if lo >= 8: return (2, f'MOV {dname(b1)},{rn}', [], '')
    if hi == 0xA:
        if lo in (6,7): return (2, f'MOV {ri},{dname(b1)}', [], '')
        if lo >= 8: return (2, f'MOV {rn},{dname(b1)}', [], '')
    if hi == 0xF:
        if lo == 5: return (2, f'MOV {dname(b1)},A', [], '')
        if lo in (6,7): return (1, f'MOV {ri},A', [], '')
        if lo >= 8: return (1, f'MOV {rn},A', [], '')
    return (1, f'DB {op:02X}h ; ???', [], '')

VECTORS = [0x0000, 0x0003, 0x000B, 0x0013, 0x001B, 0x0023, 0x002B]

def trace(rom, extra):
    """Recursive-descent trace from the vectors plus `extra` entry points.
    Returns (code, labels, xrefs, ijmps): code maps address ->
    (length, text, targets, kind)."""
    entries = VECTORS + list(extra)
    code = {}            # addr -> (len, text, targets, kind)
    labels = collections.defaultdict(set)   # addr -> {'call','jmp',...}
    xrefs = collections.defaultdict(set)
    ijmps = []
    work = list(entries)
    for e in entries: labels[e].add('entry')
    while work:
        pc = work.pop()
        while 0 <= pc < len(rom) and pc not in code:
            n, t, tg, kind = decode(rom, pc)
            code[pc] = (n, t, tg, kind)
            for x in tg:
                labels[x].add(kind or 'jmp'); xrefs[x].add(pc)
                if x < len(rom): work.append(x)
            if kind == 'ijmp': ijmps.append(pc)
            if kind in ('jmp', 'ret', 'ijmp'): break
            pc += n
    return code, labels, xrefs, ijmps

def main():
    rom = open(sys.argv[1], 'rb').read()
    extra = [int(x, 16) for x in sys.argv[2:]]
    code, labels, xrefs, ijmps = trace(rom, extra)
    covered = set()
    for a, (n, *_rest) in code.items(): covered.update(range(a, a+n))
    out = []
    a = 0
    while a < len(rom):
        if a in code:
            n, t, tg, kind = code[a]
            if a in labels:
                kinds = ','.join(sorted(labels[a]))
                xs = ' '.join(f'{x:04X}' for x in sorted(xrefs[a])[:8])
                out.append(f'\nL{a:04X}:  ; [{kinds}] from {xs}')
            hexb = ' '.join(f'{rom[a+i]:02X}' for i in range(n))
            out.append(f'  {a:04X}  {hexb:<9} {t}')
            a += n
        else:
            start = a
            while a < len(rom) and a not in code: a += 1
            chunk = rom[start:a]
            out.append(f'  {start:04X}  ; --- {a-start} bytes not reached as code ---')
            for i in range(0, min(len(chunk), 64), 16):
                out.append(f'  {start+i:04X}  DB ' + ' '.join(f'{b:02X}' for b in chunk[i:i+16]))
            if len(chunk) > 64: out.append('        ...')
    print('\n'.join(out))
    print(f'\n; {len(covered)} of {len(rom)} bytes reached as code. '
          f'{sum(1 for l in labels.values() if "call" in l)} called routines. '
          f'Indirect jumps (JMP @A+DPTR) at: {" ".join(f"{x:04X}" for x in ijmps)}', file=sys.stderr)

if __name__ == "__main__":
    main()
