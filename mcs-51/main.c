
#define MICROCONTROLLER_8052
#define MCS51REG_EXTERNAL_ROM
// #define MCS51REG_EXTERNAL_RAM
// #define MCS51REG_ENABLE_WARNINGS
#include <mcs51reg.h>

#include <stdint.h>
#include <stdbool.h>

#include "CharacterSet.h"

extern void scroll_text(const char *str, const uint8_t *font);

void main() {
    const char *str = "Hello, World!";
    while(true) {
        scroll_text(str, CharacterSet);
    }
}