#include <avr/pgmspace.h>
#include <avr/io.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>

#include "serial.h"

extern const uint8_t firmware[] PROGMEM;
extern const uint16_t firmware_len;

void power_off_unused_peripherals(void)
{
    // May as well use the Power Reduction Register to switch everything off.
    PRR = 0xFF;
    // And the analog comparator.
    ACSR |= _BV(ACD);
}

void place_address_on_bus(uint16_t i)
{
    // Load address to bus
    uint8_t lowByte = i & 0xff;
    uint8_t highByte = ((i >> 8) & 0xff);

    // Set shared data/address bus to output.
    DDRB = 0b11111111;

    PORTB = lowByte;
    PORTC = (PORTC & ~0b00111111) | (highByte & 0b00111111);
    PORTD = (PORTD & ~0b10000000) | ((highByte & 0b01000000) << 1);

    // Strobe ALE
    PORTD |= (1 << 3) ;
    PORTD &= ~(1 << 3);

    // Data/Address back to input (tri-stated).
    DDRB = 0;
    PORTB = 0;
}

void write_byte(uint8_t byte)
{
    // Set shared data/address bus to output.
    DDRB = 0b11111111;

    // Load data to lower 8 bits of bus
    PORTB = byte;

    // Strobe write signal (active low)
    PORTD &= ~(1 << 4);
    PORTD |= (1 << 4);

    // Data/Address back to input (tri-stated).
    DDRB = 0;
    PORTB = 0;
}

uint8_t read_byte(void)
{
    uint8_t byte;
    // Strobe read signal (active low)
    PORTD &= ~(1 << 5);
    __asm__("nop"); // Need to give a cycle or so for the RAM to respond.
    byte = PINB;
    PORTD |= (1 << 5);
    return byte;
}

bool test_ram(uint16_t start, uint16_t len) {
    static const uint8_t patterns[] = { 0x55, 0xAA, 0xFF, 0x00 };

    for (uint8_t p = 0; p < sizeof(patterns); p++) {
        uint8_t pat = patterns[p];

        // Write pass
        for (uint16_t i = 0; i < len; i++) {
            place_address_on_bus(start + i);
            write_byte(pat);
        }

        // Read back pass
        for (uint16_t i = 0; i < len; i++) {
            place_address_on_bus(start + i);
            uint8_t val = read_byte();
            if (val != pat)
                return false;
        }
    }
    return true;
}

int main(void)
{
    power_off_unused_peripherals();

    // The AVR is connected to the 8051 like this:
    //
    // Port B bits 0-7: Bits 0-7 of bus.
    // Port C bits 0-5: Bits 8-13 of bus.
    //
    // Port D bit    2: UNUSED
    // Port D bit    3: Address Latch Enable (ALE).
    // Port D bit    4: /WR write line.
    // Port D bit    5: /RD READ line.
    // Port D bit    6: /RESET (of the 8051)
    //
    // Port D bit    7: Bit 14 of bus.

    serialInit(250000);

    serialPrint("\n\nAVR Host Starting up...\n", true);


    // AVR starts with all ports as inputs, carrying a '0'.

    // Set up output lines - On DDRx, 0 is input, 1 is output.
    // On input lines, 1 on the port means 'pull up'.

    // We'll initially set the address lines to '1'.
    // ... but not on Port B! It's the shared data/address bus, so we need to
    // drive it _only_ when we're outputting to it.
    // PORTB = 0b11111111;
    // DDRB  = 0b11111111;

    // Bits 6 and 7 are not exposed on the ATmega328.
    PORTC = 0b00111111;
    DDRC = 0b00111111;

    // Active lines should all rest high, except ALE (bit 3)
    // Bits 0 and 1 are the serial interface, so we leave them alone.
    PORTD = 0b11110000;
    DDRD = 0b11111000;

    // RAM test
    serialPrint("\n\nRAM test...\n", true);
    {
        uint8_t errorCount = 0;
        uint16_t byteCount = 0;
        for(; byteCount < (((uint16_t)1 << 15) - 1); ++byteCount) {
            static const uint8_t patterns[] PROGMEM = { 0x55, 0xAA, 0xFF, 0x00 };

            for(uint8_t p = 0; p < sizeof(patterns); p++) {
                uint8_t pat = pgm_read_byte(&patterns[p]);

                place_address_on_bus(byteCount);
                write_byte(pat);
                uint8_t val = read_byte();
                if(val != pat) {
                    ++errorCount;
                }
            }
        }
        if(errorCount != 0) {
            serialPrint("FAIL! ");
            serialPrintDec(errorCount);
            serialPrint(" errors!\n", true);
        } else {
            serialPrint("Passed - ");
            serialPrintDec(byteCount);
            serialPrint(" bytes tested!\n", true);
        }
    }

    // A 'fake' 8051 write:
    // • Put address onto bus
    // • Strobe the Address Latch Enable pin to latch the lower 8 bits.
    // • Replace lower 8 bits of address with byte to write.
    // • Strobe write signal.

    serialPrint("Writing ");
    serialPrintDec(firmware_len);
    serialPrint(" bytes to 'ROM'...\n", true);

    for(uint16_t i = 0; i < firmware_len; ++i) {
        if((i % 4) == 0) {
            serialPrint(' ', true);
        }
        if((i % 64) == 0) {
            serialPrint('\n');
        }

        place_address_on_bus(i);

        uint8_t byte = pgm_read_byte(&firmware[i]);

        write_byte(byte);
        serialPrintHex(byte, true);
    }

    serialPrint("\n\nVerifying ");
    serialPrintDec(firmware_len);
    serialPrint(" bytes in 'ROM'...", true);

    // Verify write by reading back from RAM.
    {
        uint16_t i = 0;
        uint8_t errorCount = 0;
        for(; i < firmware_len; ++i) {
            if((i % 4) == 0) {
                serialPrint(' ', true);
            }
            if((i % 64) == 0) {
                serialPrint('\n');
            }

            place_address_on_bus(i);
            uint8_t byte = read_byte();

            if(byte != pgm_read_byte(&firmware[i])) {
                ++errorCount;
            }
            serialPrintHex(byte, true);
        }
        serialPrint("\n\n");
        if(errorCount != 0) {
            serialPrint("FAIL! ");
            serialPrintDec(errorCount);
            serialPrint(" errors!\n\n", true);
        } else {
            serialPrint("Passed - ");
            serialPrintDec(i);
            serialPrint(" bytes tested!\n\n", true);
        }
    }

    // Tri-state the bus lines to let the 8052 take over when it comes out
    // of reset.
    PORTC = 0;
    DDRC = 0;

    // On PORT D, we still want to be able drive the reset line of the 8052 low,
    // so leave pin 6 as output (but leave the line high for the moment).
    // Our Write and Read signals should also be held high (they're ANDed with
    // the 8052's)
    PORTD = 0b01110000;
    DDRD = 0b01110000;

    serialPrint("Letting 8052 take control.\n");

    // Lower the 8051 reset line (allow it to run)
    PORTD &= ~(1 << 6);

    serialPrint("8052 reset released.\n\n", true);

    while(true);
    return 0;
}

