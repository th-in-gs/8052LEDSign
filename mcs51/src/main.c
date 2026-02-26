
#define MICROCONTROLLER_8052
#define MCS51REG_EXTERNAL_ROM
#define MCS51REG_EXTERNAL_RAM
#define MCS51REG_ENABLE_WARNINGS

#include <mcs51reg.h>

#include <stdint.h>
#include <stdbool.h>

// This is defined in 'assembly.asm'.
extern void blink_loop(void);

void main(void) {
    blink_loop();
}