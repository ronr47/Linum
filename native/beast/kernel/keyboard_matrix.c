#include <stdint.h>
#include <stddef.h>

#define SCANCODE_MAX        84
#define SHIFT_MASK          0x01
#define CAPS_MASK           0x02

static const uint8_t scancode_ascii_matrix[2][SCANCODE_MAX] = {
    {
        0,  27, '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '\b',
      '\t', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\n',
        0,  'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', '`',
        0, '\\', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/',   0,
      '*',   0, ' ',   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
        0,   0,   0,   0,   0,   0, '-',   0,   0,   0, '+',   0,   0,   0
    },
    {
        0,  27, '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '\b',
      '\t', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', '\n',
        0,  'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"', '~',
        0, '|', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?',   0,
      '*',   0, ' ',   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
        0,   0,   0,   0,   0,   0, '-',   0,   0,   0, '+',   0,   0,   0
    }
};

static uint8_t keyboard_modifiers = 0;

uint8_t translate_scancode(uint8_t scancode) {
    if (scancode & 0x80) {
        uint8_t released_code = scancode & 0x7F;
        if (released_code == 0x2A || released_code == 0x36) {
            keyboard_modifiers &= ~SHIFT_MASK;
        }
        return 0;
    }

    switch (scancode) {
        case 0x2A:
        case 0x36:
            keyboard_modifiers |= SHIFT_MASK;
            return 0;
        case 0x3A:
            keyboard_modifiers ^= CAPS_MASK;
            return 0;
        default:
            break;
    }

    if (scancode >= SCANCODE_MAX) {
        return 0;
    }

    uint8_t use_shift = (keyboard_modifiers & SHIFT_MASK) ? 1 : 0;
    uint8_t ascii_char = scancode_ascii_matrix[use_shift][scancode];

    if (keyboard_modifiers & CAPS_MASK) {
        if (ascii_char >= 'a' && ascii_char <= 'z' && !use_shift) {
            ascii_char -= 0x20;
        } else if (ascii_char >= 'A' && ascii_char <= 'Z' && use_shift) {
            ascii_char += 0x20;
        }
    }

    return ascii_char;
}
