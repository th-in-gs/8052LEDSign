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

// A 'fake' 8051 write or read:
//
// place_address_on_bus():
//  • Put address onto bus
//  • Strobe the Address Latch Enable pin to latch the lower eight bits of the
//    address.
//
// write_byte() or read_byte():
//  • Replace lower 8 bits of address with byte to write.
//  • Strobe write signal.

void place_address_on_bus(uint16_t i)
{
    uint8_t lowByte = i & 0xff;
    uint8_t highByte = ((i >> 8) & 0xff);

    // Set shared data/address bus to output.
    DDRB = 0b11111111;

    // Place all 15 address bits onto the bus (see comments above for layout)
    PORTB = lowByte;
    PORTC = (PORTC & ~0b00111111) | (highByte & 0b00111111);
    PORTD = (PORTD & ~0b10000000) | ((highByte & 0b01000000) << 1);

    // Strobe ALE to latch the lower eight bits.
    PORTD |= (1 << 3) ;
    PORTD &= ~(1 << 3);

    // Shared data/address lines back to input (tri-stated).
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

    // Pre-charge the bus to 0xFF, then release it with the pull-ups enabled.
    // Without this, if the RAM fails to drive the bus, the charge left on
    // the bus lines from the last thing we wrote (usually the low byte of the
    // address) is read back, which looks deceptively like valid data.
    // With it, an undriven bus reads as 0xFF.
    PORTB = 0xFF;
    DDRB = 0xFF;
    DDRB = 0;

    // Strobe read signal (active low)
    PORTD &= ~(1 << 5);
    // Give the RAM time to respond: the read signal passes through the 7408,
    // plus the RAM's access time. PINB also has a one-cycle synchroniser delay.
    __asm__("nop\n\tnop");
    byte = PINB;
    PORTD |= (1 << 5);

    // Pull-ups off.
    PORTB = 0;
    return byte;
}

// Byte to write at `address` for RAM test pass `pass`. The final pass uses a
// value derived from the address, so that faulty address lines (which make
// different addresses alias the same RAM cell) are detected.
static const uint8_t RAM_TEST_FIXED_PATTERNS[] PROGMEM = { 0x55, 0xAA, 0xFF, 0x00 };
static const uint8_t RAM_TEST_PASSES = sizeof(RAM_TEST_FIXED_PATTERNS) + 1;

uint8_t ram_test_pattern(uint8_t pass, uint16_t address)
{
    if(pass < sizeof(RAM_TEST_FIXED_PATTERNS)) {
        return pgm_read_byte(&RAM_TEST_FIXED_PATTERNS[pass]);
    }
    return (uint8_t)(address ^ (address >> 8) ^ 0xA5);
}

int main(void)
{
    power_off_unused_peripherals();

    serialInit(38400);
    serialPrint("\n\nAVR Host starting up...\n\n", true);

    // The AVR is connected to the 8051 like this:
    //
    // Port B bits 0-7: Bits 0-7 of bus (the dual-purpose address/data lines).
    // Port C bits 0-5: Bits 8-13 of bus (address lines 8-13).
    //
    // Bits 6 and 7 of Port C are not exposed on the ATmega328, so we can't
    // use them. :-(
    //
    // Even though all of Port D is in theory externally accessible, we don't
    // want to use that because bits 1 and 2 are used for serial
    // communication. And if we ever want to signal to the AVR with an
    // interrupt, they are on bits 3 and 4.
    //
    // So, we'll put bit 14 of the bus onto Port D (below).
    //
    // Control lines on Port D:
    //  Port D bit    2: UNUSED
    //  Port D bit    3: Address Latch Enable (ALE).
    //  Port D bit    4: /WR write line.
    //  Port D bit    5: /RD READ line.
    //  Port D bit    6: /RESET (of the 8051)
    //
    // The remaining address bus bit also on Port D:
    //  Port D bit    7: Bit 14 of bus (address line 14).


    // Set up the AVR's data lines.
    //
    // The AVR starts with all ports set up as inputs, carrying a '0'.
    //
    // On DDRx, 0 is input, 1 is output.
    // On input lines, 1 on the port means 'pull up'.
    //
    // We'll initially set the lines we're driving to '1' (which will activate
    // pull-ups) then switch them to output (which will actually start
    // driving them).
    //
    // ...except not on Port B! It's the shared data/address bus, so we need to
    // drive it _only_ when we're outputting to it. Leave it as input for now
    // and switch on/off output driving over the times we'll need to write to it.
    // PORTB = 0b11111111;
    // DDRB  = 0b11111111;

    PORTC = 0b00111111;
    DDRC  = 0b00111111;

    // Control lines should all rest high, except ALE (bit 3).
    // Bits 0 and 1 are the serial interface, so we leave them alone.
    PORTD = 0b11110000;
    DDRD  = 0b11111000;


    // RAM test
    serialPrint("RAM test...\n", true);
    {
        // Write the whole RAM, then read it all back. Reading back
        // immediately after each write can't distinguish working RAM from
        // the written byte still lingering on the bus.
        static const uint16_t RAM_SIZE = (uint16_t)1 << 15;
        static const uint8_t MAX_ERRORS_TO_PRINT = 8;
        uint32_t errorCount = 0;

        for(uint8_t pass = 0; pass < RAM_TEST_PASSES; ++pass) {
            for(uint16_t address = 0; address < RAM_SIZE; ++address) {
                place_address_on_bus(address);
                write_byte(ram_test_pattern(pass, address));
            }
            for(uint16_t address = 0; address < RAM_SIZE; ++address) {
                place_address_on_bus(address);
                uint8_t expected = ram_test_pattern(pass, address);
                uint8_t actual = read_byte();
                if(actual != expected) {
                    if(errorCount < MAX_ERRORS_TO_PRINT) {
                        serialPrint("  Pass ", true);
                        serialPrintDec(pass, true);
                        serialPrint(" @", true);
                        serialPrintHex16(address, true);
                        serialPrint(": expected ", true);
                        serialPrintHex(expected, true);
                        serialPrint(", read ", true);
                        serialPrintHex(actual, true);
                        serialPrint('\n', true);
                    }
                    ++errorCount;
                }
            }
        }
        if(errorCount != 0) {
            serialPrint("FAIL! ", true);
            serialPrintDec(errorCount, true);
            serialPrint(" errors in ", true);
        } else {
            serialPrint("Passed - ", true);
        }
        serialPrintDec(RAM_SIZE, true);
        serialPrint(" bytes x ", true);
        serialPrintDec(RAM_TEST_PASSES, true);
        serialPrint(" passes tested.", true);
        serialPrint("\n\n", true);
    }


    serialPrint("Writing ");
    serialPrintDec(firmware_len);
    serialPrint(" bytes to 'ROM'...", true);

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
        uint16_t errorCount = 0;
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
        serialPrint("\n");
        if(errorCount != 0) {
            serialPrint("FAIL! ");
            serialPrintDec(errorCount);
            serialPrint(" errors!");
        } else {
            serialPrint("Passed - ");
            serialPrintDec(i);
            serialPrint(" bytes tested!");
        }
        serialPrint("\n\n", true);
    }


    // Tri-state the bus lines (by setting them to 'input')
    // to let the 8052 take over when it comes out of reset.

    // PORTB/DDRB is already all set to zero.

    PORTC = 0;
    DDRC = 0;

    // On PORT D, we still want to be able drive the reset line of the 8052 low,
    // so leave pin 6 as output (but leave the line high for the moment).
    // Our Write and Read signals should also be held high (they're ANDed with
    // the 8052's)
    PORTD = 0b01110000;
    DDRD = 0b01110000;

    serialPrint("Letting 8052 take control.\n");

    // Okay, everything is stable and we are but an observer on the bus and
    // control lines now. Lower the 8051 reset line and allow it to run!
    PORTD &= ~(1 << 6);

    serialPrint("8052 reset released.\n\n", true);

    // Keep draining the serial output buffer.
    while(true) {
        serialPoll();
    }
}

