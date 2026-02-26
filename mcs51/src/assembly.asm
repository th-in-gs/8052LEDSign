    .globl _P1
    .globl _P1_0


    .globl _blink_loop
.area CSEG    (CODE)

_blink_loop:
    mov _P1, #0
    acall _stall_for_1s
    mov _P1, #0xFF
    acall _stall_for_1s
    sjmp _blink_loop


_stall_for_1s:
    push a
    push 0
    push 1

; Need to stall for (13875000 / 12) = 1,156,250  cycles
; 9 * 255 * 255 = 585,225 - so _roughly_ correct at 2 cycles per mov.
; Roughly correct...
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

    pop 1
    pop 0
    pop a
    ret

