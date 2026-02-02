# Lexus ES330 (2004) Immobilizer EEPROM Research

Reverse engineering the Toyota/Lexus immobilizer module to enable key programming when only a valet key is available. This process may also be used to selectively add or remove registered keys.

## Background

Purchased this vehicle with only a single valet key. Toyota/Lexus requires a master key to program additional transponder keys via standard diagnostic tools. Without a master key, options are expensive (dealer) or limited (key cloning). Neither of these approaches were satisfactory to me.

**Alternative approach:** Read the immobilizer EEPROM, identify the key slot structure, move the valet key data into a master slot, and rewrite the chip. This allows subsequent standard key programming via diagnostic tools like TechStream, ThinkDiag, etc.

## Hardware

| Component | Details |
|-----------|---------|
| Vehicle | 2004 Lexus ES330 |
| Immobilizer Module | 89780-33110 |
| EEPROM Chip | 93C66 (512 bytes, 16-bit mode) |
| CH341a EEPROM Chip Programmer | ACEIRMC brand on Amazon ~$12 |
| Diagnostic Tool | ThinkDiag (for key programming after EEPROM modification) |

## Files

| File | Description |
|------|-------------|
| [immobilizer-eeprom-structure.md](immobilizer-eeprom-structure.md) | Detailed technical documentation of the EEPROM layout |
| [immobilizer-eeprom-map.png](./immobilizer-eeprom-map.png) | Visual diagram of the 512-byte EEPROM with color-coded regions |

## Quick Summary

### Key Slot Layout

The EEPROM contains 6 key slots (26 bytes each including 6 byte delimeter):

| Slot | Offset | Type |
|------|--------|------|
| 1 | 0x00 - 0x19 | Master |
| 2 | 0x1A - 0x33 | Master |
| 3 | 0x34 - 0x4D | Master |
| 4 | 0x4E - 0x67 | Master |
| 5 | 0x68 - 0x81 | Spare (unknown) |
| 6 | 0x82 - 0x9B | Valet |

### Key ID Structure

Each 26-byte slot contains:
- Bytes 0-9: Key ID Part 1 (2-byte word repeated 5×)
- Bytes 10-19: Key ID Part 2 (2-byte word repeated 5×)
- Bytes 20-25: Delimiter (CC, CD, or 95 depending on programming method)

The 4-byte Key ID is reconstructed as: `byte[0:2] + byte[10:12]`

### Procedure

1. Locate and remove immobilizer module (behind glovebox, above and to the right)
2. Remove circuit board from case, locate 93C66 EEPROM 
3. Read contents of chip in-circuit with CH341 and SOP8 clip, ASProgrammer software
4. Identify valet key in Slot 6
5. Copy valet key data to Slot 1 (master position)
6. Clear unwanted keys from other slots
7. Write modified EEPROM back to chip
8. Use diagnostic tool to program additional keys normally

## Results

Successfully converted valet key to master and programmed an additional transponder key using ThinkDiag. Both keys now function as masters, enabling future key programming without EEPROM manipulation.

## Disclaimer

This research is provided for educational purposes. Ensure you have legal ownership of any vehicle before modifying immobilizer systems. Improper modification can leave your vehicle unable to start.

## See Also

- [Full EEPROM structure documentation](immobilizer-eeprom-structure.md)
- [Visual EEPROM map](./immobilizer-eeprom-map.png)
- [YouTube vid showing the procedure on a Lexus IS - different file structure](https://www.youtube.com/watch?v=xbpU2LXYT_Q)
- [YouTube vid showing necessary modifications to the CH341a programmer for automotive use](https://www.youtube.com/watch?v=hPKckby54uA)
