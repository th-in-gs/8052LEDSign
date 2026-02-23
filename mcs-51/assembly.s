; SDCC 8052 assembly code for scrolling text

    .globl _P1
    .globl _P1_0


; C function: extern void scroll_text(const char *str, const uint8_t *font);

    .globl _scroll_text_PARM_2
    .globl _scroll_text
    .area OSEG
_scroll_text_PARM_2:
    .ds 2
    .area CSEG

_scroll_text:
    ; _scroll_text_PARM_2 contains the base address for the font data
    ; (second argument).

    ; Save string pointer in R2:R3 (R3=high, R2=low)
    mov r2, dpl
    mov r3, dph

    ; Save font pointer in R4:R5 (R5=high, R4=low)
    mov r4, _scroll_text_PARM_2      ; Low byte
    mov r5, (_scroll_text_PARM_2+1)  ; High byte


loop_through_string:
    ; Get the character from the string and store it in r6.
    clr a
    mov dpl, r2
    mov dph, r3
    movc a, @a+dptr
    mov r6, a

    ; If we've got the string-ending '\0', we're done.
    jz end

    ; Increment string pointer
    inc r2                          ; Increment low byte
    cjne r2, #0, skip_carry
    inc r3                          ; Carry to high byte
skip_carry:

    ; Font starts at 0x20 (ascii space), so subtract that from the character.
    mov a, r6                       ; Restore character
    clr c                           ; Clear carry before subtraction
    subb a, #0x20                   ; Subtract ASCII space (0x20)

    ; Now multiply by eight (each character is eight byte-size columns wide)
    ; Calculate (character - 0x20) * 8
    mov b, #8
    mul ab              ; BA = offset * 8 (16-bit result)

    ; Add font base address to get actual address.
    add a, r4           ; A = A + font_base_low
    mov dpl, a
    mov a, b            ; Get high byte of offset
    addc a, r5          ; A = B + font_base_high + carry
    mov dph, a
    ; Now DPTR points to first column of this character.

    ; Now loop through 8 columns.
    mov r7, #8
column_loop:
    clr a
    movc a, @a+dptr
    mov _P1, a
    inc dptr

    ; Output the entire 24-bit RGB pattern.
    mov b, #24
pixel_loop:
    setb _P1_0
    clr _P1_0
    djnz b, pixel_loop

    djnz r7, column_loop

    sjmp loop_through_string

end:
    ret
