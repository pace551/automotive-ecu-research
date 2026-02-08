# Toyota/Lexus IC3 Immobilizer EEPROM Structure Analysis
## 2004 Lexus ES330 - Module 89780-33110

### Overview

This document details the EEPROM structure of the Toyota/Lexus IC3 immobilizer module used in the 2004 Lexus ES330, specifically for the purpose of understanding transponder key slot locations and enabling key programming when only a valet key is available.

**Hardware Details:**
- Immobilizer Module Part Number: 89780-33110
- EEPROM Chip: 93C66 (512 bytes, 16-bit mode)
- Total EEPROM Size: 512 bytes (0x000 - 0x1FF)

---

## Key Slot Structure

Each key slot occupies **26 bytes** with the following internal structure:

| Relative Offset | Size (bytes) | Description |
|-----------------|--------------|-------------|
| +0x00 - +0x09   | 10           | Key ID Part 1 (2-byte word repeated 5 times) |
| +0x0A - +0x13   | 10           | Key ID Part 2 (2-byte word repeated 5 times) |
| +0x14 - +0x19   | 6            | Delimiter/Status bytes |

**Key ID Reconstruction:**
The 4-byte key ID is assembled from:
- Bytes 0-1 of the slot (first word of Part 1)
- Bytes 10-11 of the slot (first word of Part 2)

Example: `D0 2E D0 2E D0 2E D0 2E D0 2E 90 65 90 65 90 65 90 65 90 65` → Key ID = **D02E9065**

**Delimiter Values:**
The delimiter varies by programming method:
| Value | Meaning |
|-------|---------|
| `CC CC CC CC CC CC` | Factory programmed key |
| `CD CD CD CD CD CD` | Alternative valid delimiter |
| `95 95 95 95 95 95` | Key programmed via diagnostic tool (e.g., ThinkDiag) |
| `FF FF FF FF FF FF` | Empty slot |

---

## Memory Map - Key Slots

| Slot | Absolute Offset | Delimiter Offset | Key Type |
|------|-----------------|------------------|----------|
| **Slot 1** | 0x00 - 0x19 | 0x14 - 0x19 | Master Key 1 |
| **Slot 2** | 0x1A - 0x33 | 0x2E - 0x33 | Master Key 2 |
| **Slot 3** | 0x34 - 0x4D | 0x48 - 0x4D | Master Key 3 |
| **Slot 4** | 0x4E - 0x67 | 0x62 - 0x67 | Spare/Additional |
| **Slot 5** | 0x68 - 0x81 | 0x7C - 0x81 | Spare/Additional |
| **Slot 6** | 0x82 - 0x9B | 0x96 - 0x9B | Valet Key |

**Key Programming Requirement:** At least one Master Key (Slots 1-3) must be present and physically available to program additional keys via standard diagnostic procedures.

---

## Memory Map - Non-Key Regions

| Offset Range | Description | Notes |
|--------------|-------------|-------|
| 0x09C - 0x1A1 | Unused | All 0xFF |
| 0x1A2 - 0x1AB | Firmware Constant | `03 00` repeated 5x - identical across units |
| 0x1AC - 0x1B5 | **ECU Pairing (?)** | 2-byte value repeated 5x - differs per vehicle, likely immobilizer-to-ECU marriage data |
| 0x1B6 - 0x1BF | Unknown (Dynamic) | Changes during key programming by diagnostic tool |
| 0x1C0 - 0x1C5 | Firmware Constant | `FC` repeated 6x - identical across units |
| 0x1C6 - 0x1CB | Firmware Constant | `04` repeated 6x - identical across units |
| 0x1CC - 0x1D5 | Firmware Constant | `03 10` repeated 5x - identical across units |
| 0x1D6 - 0x1E9 | Unused | All 0xFF |
| 0x1EA - 0x1EF | Unknown (Dynamic) | Changes during key programming by diagnostic tool |
| 0x1F0 - 0x1FE | Unused | All 0xFF |
| 0x1FF | Terminator | Always 0x00 |

### Static vs Dynamic Blocks

**Firmware Constants (Static):** The blocks at 0x1A2-0x1AB, 0x1C0-0x1C5, 0x1C6-0x1CB, and 0x1CC-0x1D5 contain identical values across different immobilizer units. These appear to be firmware-related constants that do not change.

**ECU Pairing (?):** The block at 0x1AC-0x1B5 contains a 2-byte value repeated 5 times that differs between immobilizer units but remains static within a unit. This is likely the ECU-to-immobilizer marriage data established during initial pairing. This represents only 65,536 possible combinations (2^16).

**Unknown Dynamic Blocks:** The blocks at 0x1B6-0x1BF and 0x1EA-0x1EF change when keys are programmed via a diagnostic tool. Their exact purpose is unknown - they do not appear to be simple key counters, as units with the same number of keys have different values.

---

## File Analysis

### Original File (orig-immo.bin)
The EEPROM as received with the vehicle - only had the valet key physically.

| Slot | Key ID | Status | Notes |
|------|--------|--------|-------|
| Slot 1 | C8D77062 | VALID | Previous owner's key (not in possession) |
| Slot 2 | ABE5505D | VALID | Previous owner's key (not in possession) |
| Slot 3 | A94D305D | VALID | Previous owner's key (not in possession) |
| Slot 4 | EMPTY | - | |
| Slot 5 | EMPTY | - | |
| **Slot 6** | **390C8C7D** | **VALID** | **YOUR VALET KEY** |

### After Modification
Valet key moved to Master Slot 1, all other slots cleared.

| Slot | Key ID | Status |
|------|--------|--------|
| **Slot 1** | **390C8C7D** | **VALID** |
| Slot 2 | EMPTY | - |
| Slot 3 | EMPTY | - |
| Slot 4 | EMPTY | - |
| Slot 5 | EMPTY | - |
| Slot 6 | EMPTY | - |

### After Programming New Key
New transponder key programmed via ThinkDiag.

| Slot | Key ID | Status | Notes |
|------|--------|--------|-------|
| **Slot 1** | **390C8C7D** | VALID | Your original valet key (now master) |
| Slot 2 | EMPTY | - | |
| Slot 3 | EMPTY | - | |
| **Slot 4** | **54A2B9F8** | VALID | Your NEW transponder key |
| Slot 5 | EMPTY | - | |
| Slot 6 | EMPTY | - | |

---

## Procedure Summary

1. **Problem:** Vehicle purchased with only a valet key. Toyota/Lexus requires a master key to program additional keys via diagnostic tools.

2. **Solution:** 
   - Read EEPROM from immobilizer module (93C66 chip)
   - Identify the valet key by its slot position (Slot 6)
   - Copy the valet key data to Slot 1 (master position)
   - Clear old keys from Slots 1-3 (previous owner's keys)
   - Write modified EEPROM back to chip

3. **Result:** Valet key now recognized as master, enabling standard key programming via ThinkDiag or similar diagnostic tool.

---

## Tools Used

- **EEPROM Programmer:** For reading/writing 93C66 chip
- **ThinkDiag:** For programming new transponder key after master key restoration
- **Analysis:** Hex comparison of before/after dumps, comparison with second immobilizer unit

---

*Document generated from analysis of actual EEPROM dumps from 2004 Lexus ES330, validated against a second immobilizer unit. Real key values obfuscated*
