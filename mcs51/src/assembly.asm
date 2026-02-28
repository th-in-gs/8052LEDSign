    .globl _P1

    .globl _blink_loop


.area CSEG    (CODE)

_blink_loop:
    mov _P1, #0     ; Switch off all Port 1 pins.
    acall _stall_for_1s
    mov _P1, #0xFF  ; Switch on all Port 1 pins.
    acall _stall_for_1s
    sjmp _blink_loop


_stall_for_1s:
    ; Save the registers we're going to use on the stack.
    push a
    push 0
    push 1

    ; Need to stall for (13875000 / 12) = 1,156,250 cycles.
    ; Here, I use three nested loops to accomplish this.
    ; 9 * 255 * 255 = 585,225 - so, at 2 cycles per jump instruction,
    ; very roughly correct. Good enough for testing.

    mov a, #9
outer:
    mov r0, #255
middle:
    mov r1, #255
inner:
    djnz r1, inner
    djnz r0, middle
    dec a
    jnz outer

    ; Restore the saved registers before returning.
    pop 1
    pop 0
    pop a
    ret