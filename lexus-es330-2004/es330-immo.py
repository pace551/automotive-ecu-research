#!/usr/bin/env python3
"""
Toyota/Lexus ES330 Immobilizer EEPROM Tool
Manipulate transponder key slots in 93C66 EEPROM dumps.

Module: 89780-33110
Chip: 93C66 (512 bytes, 16-bit mode)
"""

import sys
import os
import copy

# EEPROM Structure Constants
EEPROM_SIZE = 512
KEY_SLOT_SIZE = 26
NUM_KEY_SLOTS = 6

# Key slot definitions
KEY_SLOTS = [
    {"num": 1, "start": 0x00, "name": "Key 1 (Master)"},
    {"num": 2, "start": 0x1A, "name": "Key 2 (Master)"},
    {"num": 3, "start": 0x34, "name": "Key 3 (Master)"},
    {"num": 4, "start": 0x4E, "name": "Key 4 (Master)"},
    {"num": 5, "start": 0x68, "name": "Key 5 (Spare)"},
    {"num": 6, "start": 0x82, "name": "Key 6 (Valet)"},
]

# Non-key region definitions
ECU_PAIRING_START = 0x1AC
ECU_PAIRING_END = 0x1B5

FIRMWARE_CONST_REGIONS = [
    (0x1A2, 0x1AB, "Firmware Const 1"),
    (0x1C0, 0x1C5, "Firmware Const 2"),
    (0x1C6, 0x1CB, "Firmware Const 3"),
    (0x1CC, 0x1D5, "Firmware Const 4"),
]

DYNAMIC_REGIONS = [
    (0x1B6, 0x1BF, "Unknown Dynamic 1"),
    (0x1EA, 0x1EF, "Unknown Dynamic 2"),
]

TERMINATOR_OFFSET = 0x1FF


class ImmoFile:
    """Represents an immobilizer EEPROM file."""
    
    def __init__(self, filepath=None):
        self.filepath = filepath
        self.data = None
        self.original_data = None
        self.modified = False
        
        if filepath:
            self.load(filepath)
    
    def load(self, filepath):
        """Load an immobilizer bin file."""
        with open(filepath, 'rb') as f:
            self.data = bytearray(f.read())
        
        if len(self.data) != EEPROM_SIZE:
            raise ValueError(f"Invalid file size: {len(self.data)} bytes (expected {EEPROM_SIZE})")
        
        self.filepath = filepath
        self.original_data = bytearray(self.data)
        self.modified = False
    
    def save(self, filepath=None):
        """Save the immobilizer bin file."""
        if filepath is None:
            filepath = self.filepath
        
        with open(filepath, 'wb') as f:
            f.write(self.data)
        
        self.filepath = filepath
        self.original_data = bytearray(self.data)
        self.modified = False
    
    def get_key_slot(self, slot_num):
        """Get the raw data for a key slot (1-6)."""
        slot = KEY_SLOTS[slot_num - 1]
        start = slot["start"]
        return self.data[start:start + KEY_SLOT_SIZE]
    
    def set_key_slot(self, slot_num, data):
        """Set the raw data for a key slot (1-6)."""
        if len(data) != KEY_SLOT_SIZE:
            raise ValueError(f"Invalid key slot data size: {len(data)} (expected {KEY_SLOT_SIZE})")
        
        slot = KEY_SLOTS[slot_num - 1]
        start = slot["start"]
        self.data[start:start + KEY_SLOT_SIZE] = data
        self.modified = True
    
    def is_slot_empty(self, slot_num):
        """Check if a key slot is empty."""
        slot_data = self.get_key_slot(slot_num)
        return slot_data[0:2] == b'\xff\xff'
    
    def get_key_id(self, slot_num):
        """Extract the 4-byte key ID from a slot."""
        if self.is_slot_empty(slot_num):
            return None
        
        slot_data = self.get_key_slot(slot_num)
        # Key ID is bytes 0-1 and bytes 10-11
        return bytes([slot_data[0], slot_data[1], slot_data[10], slot_data[11]])
    
    def get_key_id_str(self, slot_num):
        """Get key ID as a hex string."""
        key_id = self.get_key_id(slot_num)
        if key_id is None:
            return None
        return key_id.hex().upper()
    
    def get_delimiter(self, slot_num):
        """Get the delimiter bytes for a key slot."""
        slot_data = self.get_key_slot(slot_num)
        return slot_data[20:26]
    
    def get_delimiter_str(self, slot_num):
        """Get delimiter as a hex string."""
        return self.get_delimiter(slot_num).hex().upper()
    
    def erase_slot(self, slot_num):
        """Erase a key slot (fill with 0xFF)."""
        self.set_key_slot(slot_num, b'\xff' * KEY_SLOT_SIZE)
    
    def create_key_slot_data(self, key_id_hex, delimiter_hex="CCCCCCCCCCCC"):
        """Create a 26-byte key slot from a key ID and delimiter."""
        if len(key_id_hex) != 8:
            raise ValueError(f"Key ID must be 8 hex characters (4 bytes), got {len(key_id_hex)}")
        
        if len(delimiter_hex) != 12:
            raise ValueError(f"Delimiter must be 12 hex characters (6 bytes), got {len(delimiter_hex)}")
        
        key_id = bytes.fromhex(key_id_hex)
        delimiter = bytes.fromhex(delimiter_hex)
        
        # Build the slot data
        # Part 1: bytes 0-1 repeated 5 times
        part1 = key_id[0:2] * 5
        # Part 2: bytes 2-3 repeated 5 times  
        part2 = key_id[2:4] * 5
        
        return bytearray(part1 + part2 + delimiter)
    
    def get_ecu_pairing(self):
        """Get the ECU pairing data."""
        return self.data[ECU_PAIRING_START:ECU_PAIRING_END + 1]
    
    def get_ecu_pairing_str(self):
        """Get ECU pairing as a 2-byte pattern string."""
        data = self.get_ecu_pairing()
        return f"{data[0]:02X} {data[1]:02X}"
    
    def get_dynamic_block(self, index):
        """Get a dynamic block (0 or 1)."""
        start, end, _ = DYNAMIC_REGIONS[index]
        return self.data[start:end + 1]
    
    def get_firmware_const(self, index):
        """Get a firmware constant block."""
        start, end, _ = FIRMWARE_CONST_REGIONS[index]
        return self.data[start:end + 1]
    
    def validate(self):
        """Validate the EEPROM structure. Returns (is_valid, list_of_issues)."""
        issues = []
        
        # Check file size
        if len(self.data) != EEPROM_SIZE:
            issues.append(f"Invalid file size: {len(self.data)} (expected {EEPROM_SIZE})")
        
        # Check terminator
        if self.data[TERMINATOR_OFFSET] != 0x00:
            issues.append(f"Invalid terminator at 0x1FF: {self.data[TERMINATOR_OFFSET]:02X} (expected 00)")
        
        # Check key slot structure
        for slot in KEY_SLOTS:
            slot_num = slot["num"]
            if not self.is_slot_empty(slot_num):
                slot_data = self.get_key_slot(slot_num)
                
                # Check Part 1 repetition (bytes 0-9 should be 2-byte pattern repeated 5x)
                part1_pattern = slot_data[0:2]
                for i in range(1, 5):
                    if slot_data[i*2:i*2+2] != part1_pattern:
                        issues.append(f"Slot {slot_num}: Part 1 pattern not repeated correctly at offset {i*2}")
                
                # Check Part 2 repetition (bytes 10-19 should be 2-byte pattern repeated 5x)
                part2_pattern = slot_data[10:12]
                for i in range(1, 5):
                    if slot_data[10+i*2:10+i*2+2] != part2_pattern:
                        issues.append(f"Slot {slot_num}: Part 2 pattern not repeated correctly at offset {10+i*2}")
                
                # Check delimiter repetition (bytes 20-25 should be consistent pattern)
                delim = slot_data[20:26]
                # Common delimiters repeat a 2-byte or 1-byte pattern
                if not (delim[0:2] * 3 == delim or bytes([delim[0]]) * 6 == delim):
                    # Less strict check - just warn if unusual
                    issues.append(f"Slot {slot_num}: Unusual delimiter pattern: {delim.hex().upper()}")
        
        # Check ECU pairing structure (should be 2-byte pattern repeated 5x)
        ecu_data = self.get_ecu_pairing()
        ecu_pattern = ecu_data[0:2]
        for i in range(1, 5):
            if ecu_data[i*2:i*2+2] != ecu_pattern:
                issues.append(f"ECU pairing: Pattern not repeated correctly at offset {i*2}")
        
        return (len(issues) == 0, issues)
    
    def has_changes(self):
        """Check if there are unsaved changes."""
        return self.data != self.original_data


def print_header():
    """Print program header."""
    print("=" * 60)
    print("Toyota/Lexus ES330 Immobilizer EEPROM Tool")
    print("Module: 89780-33110 | Chip: 93C66 (512 bytes)")
    print("=" * 60)


def print_file_summary(immo):
    """Print a summary of the immobilizer file."""
    print("\n" + "-" * 60)
    print(f"File: {immo.filepath}")
    print("-" * 60)
    
    # Count keys
    key_count = sum(1 for i in range(1, 7) if not immo.is_slot_empty(i))
    print(f"\nKey Slots: {key_count} of {NUM_KEY_SLOTS} occupied")
    print()
    
    for slot in KEY_SLOTS:
        slot_num = slot["num"]
        if immo.is_slot_empty(slot_num):
            print(f"  {slot['name']}: EMPTY")
        else:
            key_id = immo.get_key_id_str(slot_num)
            delim = immo.get_delimiter(slot_num)
            delim_short = f"{delim[0]:02X}"
            print(f"  {slot['name']}: {key_id}  (delimiter: {delim_short})")
    
    print(f"\nECU Pairing (?): {immo.get_ecu_pairing_str()} (repeated 5x)")
    
    print("\nDynamic Blocks:")
    for i, (start, end, name) in enumerate(DYNAMIC_REGIONS):
        data = immo.get_dynamic_block(i)
        pattern = f"{data[0]:02X} {data[1]:02X}" if len(data) >= 2 else data.hex().upper()
        print(f"  {name}: {pattern}")
    
    # Validation status
    is_valid, issues = immo.validate()
    if is_valid:
        print("\n✓ File structure is valid")
    else:
        print(f"\n⚠ File has {len(issues)} structural issue(s):")
        for issue in issues:
            print(f"  - {issue}")
    
    if immo.has_changes():
        print("\n*** UNSAVED CHANGES ***")


def confirm(prompt):
    """Ask for user confirmation."""
    while True:
        response = input(f"{prompt} (y/n): ").strip().lower()
        if response in ('y', 'yes'):
            return True
        if response in ('n', 'no'):
            return False
        print("Please enter 'y' or 'n'")


def get_slot_choice(prompt="Select slot (1-6): ", allow_cancel=True):
    """Get a valid slot number from user."""
    while True:
        suffix = " or 'c' to cancel" if allow_cancel else ""
        response = input(f"{prompt}{suffix}: ").strip().lower()
        
        if allow_cancel and response == 'c':
            return None
        
        try:
            slot = int(response)
            if 1 <= slot <= 6:
                return slot
            print("Please enter a number between 1 and 6")
        except ValueError:
            print("Invalid input")


def get_hex_input(prompt, expected_length):
    """Get a valid hex string of expected length from user."""
    while True:
        response = input(f"{prompt} ({expected_length} hex chars) or 'c' to cancel: ").strip().upper()
        
        if response.lower() == 'c':
            return None
        
        # Remove any spaces
        response = response.replace(" ", "")
        
        if len(response) != expected_length:
            print(f"Expected {expected_length} hex characters, got {len(response)}")
            continue
        
        try:
            bytes.fromhex(response)
            return response
        except ValueError:
            print("Invalid hex characters")


def manipulate_menu(immo):
    """Submenu for manipulating an existing file."""
    while True:
        print_file_summary(immo)
        
        print("\n" + "-" * 40)
        print("Manipulation Options:")
        print("-" * 40)
        print("  1. Erase a key slot")
        print("  2. Write new key to slot")
        print("  3. Copy key to another slot")
        print("  4. Swap two key slots")
        print("  5. Save changes")
        print("  6. Save as new file")
        print("  7. Discard changes")
        print("  8. Back to main menu")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            # Erase slot
            slot = get_slot_choice("Select slot to erase")
            if slot is None:
                continue
            
            if immo.is_slot_empty(slot):
                print(f"Slot {slot} is already empty")
                continue
            
            key_id = immo.get_key_id_str(slot)
            if confirm(f"Erase slot {slot} (Key ID: {key_id})?"):
                immo.erase_slot(slot)
                print(f"Slot {slot} erased")
        
        elif choice == '2':
            # Write new key
            slot = get_slot_choice("Select slot to write")
            if slot is None:
                continue
            
            if not immo.is_slot_empty(slot):
                key_id = immo.get_key_id_str(slot)
                if not confirm(f"Slot {slot} contains key {key_id}. Overwrite?"):
                    continue
            
            key_id = get_hex_input("Enter key ID", 8)
            if key_id is None:
                continue
            
            print("\nDelimiter options:")
            print("  1. CC (factory)")
            print("  2. CD (alternative)")
            print("  3. 95 (diagnostic tool)")
            print("  4. Custom")
            
            delim_choice = input("Select delimiter (1-4): ").strip()
            
            if delim_choice == '1':
                delimiter = "CCCCCCCCCCCC"
            elif delim_choice == '2':
                delimiter = "CDCDCDCDCDCD"
            elif delim_choice == '3':
                delimiter = "959595959595"
            elif delim_choice == '4':
                delimiter = get_hex_input("Enter delimiter", 12)
                if delimiter is None:
                    continue
            else:
                print("Invalid choice")
                continue
            
            if confirm(f"Write key {key_id} to slot {slot} with delimiter {delimiter[:2]}?"):
                slot_data = immo.create_key_slot_data(key_id, delimiter)
                immo.set_key_slot(slot, slot_data)
                print(f"Key written to slot {slot}")
        
        elif choice == '3':
            # Copy key
            src_slot = get_slot_choice("Select source slot to copy FROM")
            if src_slot is None:
                continue
            
            if immo.is_slot_empty(src_slot):
                print(f"Slot {src_slot} is empty, nothing to copy")
                continue
            
            dst_slot = get_slot_choice("Select destination slot to copy TO")
            if dst_slot is None:
                continue
            
            if src_slot == dst_slot:
                print("Source and destination cannot be the same")
                continue
            
            src_key = immo.get_key_id_str(src_slot)
            
            if not immo.is_slot_empty(dst_slot):
                dst_key = immo.get_key_id_str(dst_slot)
                if not confirm(f"Destination slot {dst_slot} contains key {dst_key}. Overwrite?"):
                    continue
            
            erase_src = confirm(f"Erase source slot {src_slot} after copy?")
            
            action_desc = f"Copy key {src_key} from slot {src_slot} to slot {dst_slot}"
            if erase_src:
                action_desc += f", then erase slot {src_slot}"
            
            if confirm(f"{action_desc}?"):
                src_data = immo.get_key_slot(src_slot)
                immo.set_key_slot(dst_slot, src_data)
                if erase_src:
                    immo.erase_slot(src_slot)
                print("Copy completed")
        
        elif choice == '4':
            # Swap keys
            slot1 = get_slot_choice("Select first slot")
            if slot1 is None:
                continue
            
            slot2 = get_slot_choice("Select second slot")
            if slot2 is None:
                continue
            
            if slot1 == slot2:
                print("Cannot swap a slot with itself")
                continue
            
            key1 = immo.get_key_id_str(slot1) or "EMPTY"
            key2 = immo.get_key_id_str(slot2) or "EMPTY"
            
            if confirm(f"Swap slot {slot1} ({key1}) with slot {slot2} ({key2})?"):
                data1 = immo.get_key_slot(slot1)
                data2 = immo.get_key_slot(slot2)
                immo.set_key_slot(slot1, data2)
                immo.set_key_slot(slot2, data1)
                print("Swap completed")
        
        elif choice == '5':
            # Save
            if not immo.has_changes():
                print("No changes to save")
                continue
            
            is_valid, issues = immo.validate()
            if not is_valid:
                print(f"\n⚠ Warning: File has {len(issues)} structural issue(s):")
                for issue in issues:
                    print(f"  - {issue}")
                if not confirm("Save anyway?"):
                    continue
            
            if confirm(f"Save changes to {immo.filepath}?"):
                immo.save()
                print("File saved")
        
        elif choice == '6':
            # Save as
            new_path = input("Enter new filename (or 'c' to cancel): ").strip()
            if new_path.lower() == 'c':
                continue
            
            if os.path.exists(new_path):
                if not confirm(f"File {new_path} exists. Overwrite?"):
                    continue
            
            is_valid, issues = immo.validate()
            if not is_valid:
                print(f"\n⚠ Warning: File has {len(issues)} structural issue(s):")
                for issue in issues:
                    print(f"  - {issue}")
                if not confirm("Save anyway?"):
                    continue
            
            immo.save(new_path)
            print(f"File saved as {new_path}")
        
        elif choice == '7':
            # Discard changes
            if not immo.has_changes():
                print("No changes to discard")
                continue
            
            if confirm("Discard all unsaved changes?"):
                immo.data = bytearray(immo.original_data)
                immo.modified = False
                print("Changes discarded")
        
        elif choice == '8':
            # Back to main menu
            if immo.has_changes():
                if not confirm("You have unsaved changes. Discard and exit?"):
                    continue
            return
        
        else:
            print("Invalid option")


def compare_files(file1_path, file2_path):
    """Compare two immobilizer files."""
    try:
        immo1 = ImmoFile(file1_path)
        immo2 = ImmoFile(file2_path)
    except Exception as e:
        print(f"Error loading files: {e}")
        return
    
    print("\n" + "=" * 60)
    print("FILE COMPARISON")
    print("=" * 60)
    print(f"File 1: {file1_path}")
    print(f"File 2: {file2_path}")
    
    # Compare key slots
    print("\n" + "-" * 40)
    print("Key Slot Comparison")
    print("-" * 40)
    
    for slot in KEY_SLOTS:
        slot_num = slot["num"]
        key1 = immo1.get_key_id_str(slot_num) or "EMPTY"
        key2 = immo2.get_key_id_str(slot_num) or "EMPTY"
        
        if key1 == key2:
            status = "SAME"
        else:
            status = "DIFFERENT"
        
        print(f"  Slot {slot_num}: {key1:12} vs {key2:12}  [{status}]")
    
    # Compare ECU pairing
    print("\n" + "-" * 40)
    print("ECU Pairing Comparison")
    print("-" * 40)
    
    ecu1 = immo1.get_ecu_pairing_str()
    ecu2 = immo2.get_ecu_pairing_str()
    status = "SAME" if ecu1 == ecu2 else "DIFFERENT"
    print(f"  File 1: {ecu1}")
    print(f"  File 2: {ecu2}")
    print(f"  Status: {status}")
    
    # Compare firmware constants
    print("\n" + "-" * 40)
    print("Firmware Constants Comparison")
    print("-" * 40)
    
    all_same = True
    for i, (start, end, name) in enumerate(FIRMWARE_CONST_REGIONS):
        data1 = immo1.get_firmware_const(i)
        data2 = immo2.get_firmware_const(i)
        
        if data1 == data2:
            status = "SAME"
        else:
            status = "DIFFERENT"
            all_same = False
        
        print(f"  {name}: {status}")
    
    if all_same:
        print("  ✓ All firmware constants match (expected)")
    else:
        print("  ⚠ Some firmware constants differ (unexpected)")
    
    # Compare dynamic blocks
    print("\n" + "-" * 40)
    print("Dynamic Blocks Comparison")
    print("-" * 40)
    
    for i, (start, end, name) in enumerate(DYNAMIC_REGIONS):
        data1 = immo1.get_dynamic_block(i)
        data2 = immo2.get_dynamic_block(i)
        
        pattern1 = f"{data1[0]:02X} {data1[1]:02X}"
        pattern2 = f"{data2[0]:02X} {data2[1]:02X}"
        
        status = "SAME" if data1 == data2 else "DIFFERENT"
        print(f"  {name}: {pattern1} vs {pattern2}  [{status}]")
    
    # Overall byte comparison
    print("\n" + "-" * 40)
    print("Overall Comparison")
    print("-" * 40)
    
    diff_count = sum(1 for a, b in zip(immo1.data, immo2.data) if a != b)
    print(f"  Total bytes different: {diff_count} of {EEPROM_SIZE}")
    
    if diff_count == 0:
        print("  Files are identical")


def main_menu():
    """Main program menu."""
    print_header()
    
    while True:
        print("\n" + "-" * 40)
        print("Main Menu")
        print("-" * 40)
        print("  1. Create new (virgin) immobilizer file")
        print("  2. Validate existing file")
        print("  3. Manipulate existing file")
        print("  4. Compare two files")
        print("  5. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            print("\n[Not yet implemented]")
            print("This feature will create a blank immobilizer file template.")
        
        elif choice == '2':
            filepath = input("Enter path to immobilizer bin file (or 'c' to cancel): ").strip()
            if filepath.lower() == 'c':
                continue
            
            try:
                immo = ImmoFile(filepath)
                print_file_summary(immo)
            except FileNotFoundError:
                print(f"File not found: {filepath}")
            except ValueError as e:
                print(f"Error: {e}")
            except Exception as e:
                print(f"Error loading file: {e}")
        
        elif choice == '3':
            filepath = input("Enter path to immobilizer bin file (or 'c' to cancel): ").strip()
            if filepath.lower() == 'c':
                continue
            
            try:
                immo = ImmoFile(filepath)
                manipulate_menu(immo)
            except FileNotFoundError:
                print(f"File not found: {filepath}")
            except ValueError as e:
                print(f"Error: {e}")
            except Exception as e:
                print(f"Error loading file: {e}")
        
        elif choice == '4':
            file1 = input("Enter path to first file (or 'c' to cancel): ").strip()
            if file1.lower() == 'c':
                continue
            
            file2 = input("Enter path to second file: ").strip()
            if file2.lower() == 'c':
                continue
            
            try:
                compare_files(file1, file2)
            except FileNotFoundError as e:
                print(f"File not found: {e}")
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == '5':
            print("\nGoodbye!")
            sys.exit(0)
        
        else:
            print("Invalid option")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
        sys.exit(0)
