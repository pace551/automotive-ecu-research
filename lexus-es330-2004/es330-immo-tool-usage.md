# ES330 Immobilizer Tool Usage

Command-line tool for manipulating Toyota/Lexus ES330 immobilizer EEPROM files.

## Requirements

- Python 3.6+
- No external dependencies

## Running the Tool

```bash
python3 es330-immo-tool.py
```

## Main Menu

```
----------------------------------------
Main Menu
----------------------------------------
  1. Create new (virgin) immobilizer file
  2. Validate existing file
  3. Manipulate existing file
  4. Compare two files
  5. Exit
```

### Option 1: Create New File

*Not yet implemented.* Will create a blank immobilizer file template.

### Option 2: Validate Existing File

Loads a bin file and displays its contents without entering edit mode. Useful for quick inspection.

**Example output:**
```
------------------------------------------------------------
File: jace-immo.bin
------------------------------------------------------------

Key Slots: 4 of 6 occupied

  Key 1 (Master): C8D77062  (delimiter: CC)
  Key 2 (Master): ABE5505D  (delimiter: CC)
  Key 3 (Master): A94D305D  (delimiter: CC)
  Key 4 (Master): EMPTY
  Key 5 (Spare): EMPTY
  Key 6 (Valet): 390C8C7D  (delimiter: CC)

ECU Pairing (?): A4 FA (repeated 5x)

Dynamic Blocks:
  Unknown Dynamic 1: FF D8
  Unknown Dynamic 2: 95 95

✓ File structure is valid
```

### Option 3: Manipulate Existing File

Opens a file for editing with the following operations:

```
----------------------------------------
Manipulation Options:
----------------------------------------
  1. Erase a key slot
  2. Write new key to slot
  3. Copy key to another slot
  4. Swap two key slots
  5. Save changes
  6. Save as new file
  7. Discard changes
  8. Back to main menu
```

#### Erase a Key Slot
Fills the selected slot with `FF` bytes, effectively removing the key.

#### Write New Key to Slot
Manually enter a 4-byte key ID (8 hex characters) and select a delimiter:
- `CC` - Factory programmed
- `CD` - Alternative valid delimiter
- `95` - Diagnostic tool programmed
- Custom - Enter your own 6-byte delimiter

#### Copy Key to Another Slot
Copies key data from one slot to another. Optionally erases the source slot after copying. This is the primary operation for converting a valet key to a master key.

#### Swap Two Key Slots
Exchanges the contents of two slots.

#### Save / Save As
Writes changes to disk. The tool validates file structure before saving and warns of any issues.

#### Discard Changes
Reverts to the last saved state.

### Option 4: Compare Two Files

Side-by-side comparison of two immobilizer files showing:
- Key slot differences
- ECU pairing comparison
- Firmware constants check (should match across units)
- Dynamic block differences
- Total byte difference count

**Example output:**
```
============================================================
FILE COMPARISON
============================================================
File 1: jace-immo.bin
File 2: ebay-immo.bin

----------------------------------------
Key Slot Comparison
----------------------------------------
  Slot 1: C8D77062     vs AEFA307F      [DIFFERENT]
  Slot 2: ABE5505D     vs 9221309D      [DIFFERENT]
  Slot 3: A94D305D     vs AEFA307F      [DIFFERENT]
  Slot 4: EMPTY        vs EMPTY         [SAME]
  Slot 5: EMPTY        vs EMPTY         [SAME]
  Slot 6: 390C8C7D     vs A12D908C      [DIFFERENT]

----------------------------------------
ECU Pairing Comparison
----------------------------------------
  File 1: A4 FA
  File 2: E3 5E
  Status: DIFFERENT

----------------------------------------
Firmware Constants Comparison
----------------------------------------
  Firmware Const 1: SAME
  Firmware Const 2: SAME
  Firmware Const 3: SAME
  Firmware Const 4: SAME
  ✓ All firmware constants match (expected)

----------------------------------------
Dynamic Blocks Comparison
----------------------------------------
  Unknown Dynamic 1: FF D8 vs FF FC  [DIFFERENT]
  Unknown Dynamic 2: 95 95 vs 68 68  [DIFFERENT]

----------------------------------------
Overall Comparison
----------------------------------------
  Total bytes different: 115 of 512
```

## Common Workflows

### Convert Valet Key to Master Key

1. Run tool: `python3 es330-immo-tool.py`
2. Select **3** (Manipulate existing file)
3. Enter path to your EEPROM dump
4. Select **3** (Copy key to another slot)
5. Source slot: **6** (valet key location)
6. Destination slot: **1** (master key location)
7. Confirm overwrite if slot 1 has data
8. Choose whether to erase source slot 6
9. Optionally erase other unwanted keys (option 1)
10. Select **6** (Save as new file) - recommended to keep original
11. Write new file to EEPROM chip

### Verify a Dump Before/After Modification

1. Run tool: `python3 es330-immo-tool.py`
2. Select **2** (Validate existing file)
3. Enter path to bin file
4. Review output for expected key positions and validity

### Compare Original vs Modified

1. Run tool: `python3 es330-immo-tool.py`
2. Select **4** (Compare two files)
3. Enter paths to both files
4. Review differences

## Input Validation

- Key IDs must be exactly 8 hex characters (4 bytes)
- Custom delimiters must be exactly 12 hex characters (6 bytes)
- File must be exactly 512 bytes
- All destructive operations require confirmation

## File Structure Validation

Before saving, the tool checks:
- Correct file size (512 bytes)
- Terminator byte at 0x1FF is 0x00
- Key slot data patterns are properly repeated
- ECU pairing pattern is properly repeated

Warnings are displayed for any structural issues, but saves are still allowed if confirmed.
