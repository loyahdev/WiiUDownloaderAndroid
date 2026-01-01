#!/usr/bin/env python3

# fst parser by ihaveamac, with assistance from MarcusD

import binascii
import os
import struct
import sys


def read_int(f, s):
    return int.from_bytes(f.read(s), byteorder='big')


def read_string(f):
    buf = b''
    while True:
        char = f.read(1)
        if char == b'\0' or char == b'':
            return buf.decode('utf-8')
        buf += char


def file_chunk_offset(offset):
    chunks = (offset // 0xFC00)
    single_chunk_offset = offset % 0xFC00
    actual_offset = single_chunk_offset + ((chunks + 1) * 0x400) + (chunks * 0xFC00)
    return actual_offset


def iterate_directory(f, iter_start, count, names_offset, depth, topdir, content_records, can_extract, tree=[]):
    i = iter_start

    while i < count:
        entry_offset = f.tell()
        f_type = ord(f.read(1))
        isdir = f_type & 1

        name_offset = read_int(f, 3) + names_offset
        orig_offset = f.tell()
        f.seek(name_offset)
        f_name = read_string(f)
        f.seek(orig_offset)

        f_offset = read_int(f, 4)
        f_size = read_int(f, 4)
        f_flags = read_int(f, 2)
        if not f_flags & 4:
            f_offset <<= 5

        content_index = read_int(f, 2)

        # this should be based on f_flags, but I'm not sure if there is a reliable way to determine this yet.
        has_hash_tree = content_records[content_index][2] & 2
        f_real_offset = file_chunk_offset(f_offset) if has_hash_tree else f_offset

        to_print = ''
        if '--dump-info' in sys.argv:
            to_print += '{:05} entryO={:08X} type={:02X} flags={:03X} O={:010X} realO={:010X} size={:08X} cidx={:04X} cid={} '.format(i, entry_offset, f_type, f_flags, f_offset, f_real_offset, f_size, content_index, content_records[content_index][0].upper())
        if '--full-paths' in sys.argv:
            to_print += ''.join(tree) + f_name
        else:
            to_print += ('  ' * depth) + ('* ' if isdir else '- ') + f_name
        if not (f_type & 0x80) or '--all' in sys.argv:
            print(to_print + (' (deleted)' if f_type & 0x80 else ''))

        if isdir:
            if f_offset <= topdir:
                return
            tree.append(f_name + '/')
            if can_extract and '--no-extract' not in sys.argv:
                os.makedirs(''.join(tree), exist_ok=True)
            iterate_directory(f, i + 1, f_size, names_offset, depth + 1, f_offset, content_records, can_extract, tree=tree)
            del tree[-1]
            i = f_size - 1

        elif can_extract and '--no-extract' not in sys.argv:
            # Try multiple file extensions since decryption might create different file types
            content_id = content_records[content_index][0]
            content_file = None
            
            # Try different possible file extensions
            for ext in ['.app.dec', '.dec']:
                test_path = content_id + ext
                if os.path.exists(test_path):
                    content_file = test_path
                    break
            
            if content_file:
                output_file = ''.join(tree) + f_name
                
                try:
                    print(f"  Extracting {f_name} from {content_file}")
                    with open(content_file, 'rb') as c, open(output_file, 'wb') as o:
                        c.seek(f_real_offset)
                        buf = b''
                        left = f_size
                        while left > 0:
                            to_read = min(0x20, left)
                            buf += c.read(to_read)
                            left -= to_read
                            if len(buf) >= 0x200:
                                o.write(buf)
                                buf = b''
                            if has_hash_tree and c.tell() % 0x10000 < 0x400:
                                c.seek(0x400, 1)
                        o.write(buf)
                except FileNotFoundError:
                    print(f"  ⚠ Could not find content file: {content_file}")
                except Exception as e:
                    print(f"  ⚠ Error extracting {f_name}: {e}")
            else:
                print(f"  ⚠ Could not find any content file for {content_id}")

        i += 1


def main(game_dir):
    # Change to the game directory first - this is critical!
    original_dir = os.getcwd()
    
    # Check if we need to change directory
    if game_dir != '.' and game_dir != original_dir:
        print(f"Changing to directory: {game_dir}")
        os.chdir(game_dir)
    
    # Now check for TMD in current directory
    if not os.path.isfile('title.tmd'):
        print(f'❌ No TMD (title.tmd) was found in current directory')
        os.chdir(original_dir)  # Change back
        return False
    
    with open('title.tmd', 'rb') as f:
        # find title id and content id
        contents = []
        content_count = 0

        f.seek(0x1DE)
        content_count = struct.unpack('>H', f.read(0x2))[0]

        f.seek(0x204)
        tmd_index = f.read(0x2)[::-1]

        for c in range(content_count):
            f.seek(0xB04 + (0x30 * c))
            content_id = f.read(0x4).hex()

            f.seek(0xB08 + (0x30 * c))
            content_index = f.read(0x2).hex()

            f.seek(0xB0A + (0x30 * c))
            content_type = struct.unpack('>H', f.read(0x2))[0]

            contents.append([content_id, content_index, content_type])

        # Try to find the FST header file with different extensions
        fst_found = False
        fst_header_filename = None
        
        for ext in ['.app.dec', '.dec']:
            test_file = contents[0][0] + ext
            if os.path.isfile(test_file):
                fst_header_filename = test_file
                fst_found = True
                print(f'FST header file: {fst_header_filename}')
                break
        
        if not fst_found:
            print(f'❌ Couldn\'t find FST header file, ensure decryption is complete.')
            os.chdir(original_dir)  # Change back
            return False
        
        can_extract = True
        for content in contents[1:]:
            content_found = False
            for ext in ['.app.dec', '.dec']:
                if os.path.isfile(content[0] + ext):
                    content_found = True
                    break
            if not content_found:
                print(f'⚠ Couldn\'t find {content[0]}.app.dec or .dec, extraction will be partial.')
                can_extract = False
        
        with open(fst_header_filename, 'rb') as s:
            s.seek(4)
            exh_size = read_int(s, 4)
            exh_count = read_int(s, 4)

            print(f'unknown: 0x{exh_size:X}')
            print(f'exheader count: {exh_count}')

            s.seek(0x14, 1)

            for i in range(exh_count):
                print(f'#{i} ({i:X})')
                print('- DiscOffset?: 0x' + s.read(4).hex())
                print('- Unknown2:    0x' + s.read(4).hex())
                print('- TitleID:     0x' + s.read(8).hex())
                print('- GroupID:     0x' + s.read(4).hex())
                print('- Flags?:      0x' + s.read(2).hex())
                print('')
                s.seek(10, 1)

            # what is this again?
            file_entries_offset = s.tell()
            s.seek(8, 1)
            total_entries = read_int(s, 4)
            s.seek(4, 1)
            names_offset = file_entries_offset + (total_entries * 0x10)

            iterate_directory(s, 1, total_entries, names_offset, 0, -1, contents, can_extract)
    
    # Change back to original directory
    if game_dir != '.' and game_dir != original_dir:
        os.chdir(original_dir)
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract files from Wii U game FST')
    parser.add_argument('game_dir', nargs='?', default='.', help='Game directory containing decrypted files (default: current directory)')
    parser.add_argument('--no-extract', action='store_true', help='Don\'t extract files, just list contents')
    parser.add_argument('--all', action='store_true', help='Show all entries including deleted ones')
    parser.add_argument('--dump-info', action='store_true', help='Show detailed entry information')
    parser.add_argument('--full-paths', action='store_true', help='Show full paths instead of tree structure')
    
    args = parser.parse_args()
    
    # Add arguments to sys.argv for the existing logic
    if args.no_extract:
        sys.argv.append('--no-extract')
    if args.all:
        sys.argv.append('--all')
    if args.dump_info:
        sys.argv.append('--dump-info')
    if args.full_paths:
        sys.argv.append('--full-paths')
    
    print(f"Extracting from directory: {args.game_dir}")
    success = main(args.game_dir)
    
    if success:
        print("\n✅ Extraction complete!")
    else:
        print("\n❌ Extraction failed")
        sys.exit(1)