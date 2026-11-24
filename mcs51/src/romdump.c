// Internal mask ROM dumper for the MSM83C154 (and other 8051-family parts
// whose EA pin isn't latched at reset).
//
// How it works (see also avr_host/src/main.cpp):
//
//  1. The AVR host loads this program at code address 0x4000, plus a stub
//     'LJMP 0x4000' at code address 0x0000.
//  2. The AVR holds EA low and releases reset. With EA low, the 8052 fetches
//     everything externally, so runs the stub, and jumps here.
//  3. Code at 0x4000 and above is always fetched externally, whatever EA is.
//     The AVR raises EA ~10ms after releasing reset. From then on, code
//     addresses 0x0000-0x3FFF read the internal ROM.
//  4. We wait (well over 10ms) to be sure EA is high, then copy code
//     0x0000-0x3FFF (MOVC) to data 0x0000-0x3FFF (MOVX).
//  5. The AVR puts us back into reset after ~2s, then reads the data back.
//
// With the current RAM/ROM decode (NAND(A14, ~RD, ~WR)), data
// 0x0000-0x3FFF lands in the same SRAM half as code 0x0000-0x3FFF, which is
// a different half from this program's code at 0x4000. So the copy can't
// overwrite this program. It does overwrite the reset stub, but we're
// finished with it by then.
//
// This must be linked with --code-loc 0x4000 (see custom_code_loc in
// platformio.ini).

#define MICROCONTROLLER_8052
#define MCS51REG_EXTERNAL_ROM
#define MCS51REG_EXTERNAL_RAM
#define MCS51REG_ENABLE_WARNINGS

#include <mcs51reg.h>

#include <stdint.h>

#define INTERNAL_ROM_SIZE 0x4000

static void wait_for_ea(void)
{
    // Very roughly 200ms at 13.875MHz - not critical, the AVR raises EA after
    // 10ms and waits 2s before putting us back into reset.
    for(volatile uint8_t outer = 0; outer < 20; ++outer) {
        for(volatile uint16_t inner = 0; inner < 1000; ++inner) {
        }
    }
}

void main(void)
{
    // LED on P1.0 off while we work.
    P1 = 0x00;

    wait_for_ea();

    const __code uint8_t *source = (const __code uint8_t *)0x0000;
    __xdata uint8_t *destination = (__xdata uint8_t *)0x0000;
    for(uint16_t i = 0; i < INTERNAL_ROM_SIZE; ++i) {
        destination[i] = source[i];
    }

    // Done - LED on.
    P1 = 0xFF;

    for(;;) {
    }
}
