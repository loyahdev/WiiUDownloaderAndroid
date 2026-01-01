#!/usr/bin/env python3
# wiiu_decryptor.py

import binascii
import hashlib
import math
import os
import struct
import sys
import argparse

# Hardcoded Wii U Common Key
WIIU_COMMON_KEY = 'D7B00402659BA2ABD2CB0DB27FA2B656'

# Try to import AES implementations
AES_AVAILABLE = False
AES_LIBRARY = None

try:
    # First try: pycryptodome (usually works well)
    from Crypto.Cipher import AES
    AES_AVAILABLE = True
    AES_LIBRARY = 'pycryptodome'
    print("✓ Using pycryptodome for AES")
except ImportError:
    try:
        # Second try: cryptography (original)
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        AES_AVAILABLE = True
        AES_LIBRARY = 'cryptography'
        print("✓ Using cryptography for AES")
    except ImportError:
        try:
            # Third try: pyaes (pure Python, slow but works everywhere)
            import pyaes
            AES_AVAILABLE = True
            AES_LIBRARY = 'pyaes'
            print("✓ Using pyaes (pure Python AES)")
        except ImportError:
            print("❌ No AES library found! Install one of:")
            print("   pip install pycryptodome  (recommended)")
            print("   pip install cryptography")
            print("   pip install pyaes")
            AES_AVAILABLE = False


def validate_common_key():
    """Validate the hardcoded common key"""
    wiiu_common_key_hash = hashlib.sha1(WIIU_COMMON_KEY.encode('utf-8').upper())
    expected_hash = 'e3fbc19d1306f6243afe852ab35ed9e1e4777d3a'
    
    if wiiu_common_key_hash.hexdigest() != expected_hash:
        print(f"⚠ Warning: Key hash mismatch!")
        print(f"  Expected: {expected_hash}")
        print(f"  Got:      {wiiu_common_key_hash.hexdigest()}")
        return False
    return True


def aes_cbc_decrypt(key, iv, data):
    """Decrypt data using available AES library"""
    if not AES_AVAILABLE:
        raise RuntimeError("No AES library available")
    
    if AES_LIBRARY == 'pycryptodome':
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.decrypt(data)
    
    elif AES_LIBRARY == 'cryptography':
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend()).decryptor()
        return cipher.update(data) + cipher.finalize()
    
    elif AES_LIBRARY == 'pyaes':
        # pyaes needs exactly 16-byte IV
        if len(iv) != 16:
            iv = iv.ljust(16, b'\x00')[:16]
        
        aes = pyaes.AESModeOfOperationCBC(key, iv=iv)
        decrypted = b''
        
        # Decrypt in 16-byte blocks
        for i in range(0, len(data), 16):
            block = data[i:i+16]
            if len(block) < 16:
                block = block.ljust(16, b'\x00')
            decrypted += aes.decrypt(block)
        
        return decrypted
    
    else:
        raise RuntimeError(f"Unknown AES library: {AES_LIBRARY}")


def show_progress(val, maxval, cid):
    """Show progress percentage"""
    if maxval > 0:
        percent = (val / maxval) * 100
        sys.stdout.write(f'\rDecrypting {cid}... {percent:5.1f}%')
        sys.stdout.flush()


def show_chunk(num, count, cid):
    """Show chunk progress"""
    sys.stdout.write(f'\rDecrypting {cid}... Chunk {num+1}/{count}')
    sys.stdout.flush()


def parse_tmd(tmd_path):
    """Parse TMD file to get title ID and content list"""
    with open(tmd_path, 'rb') as tmd:
        # Read title ID (offset 0x18C)
        tmd.seek(0x18C)
        title_id = tmd.read(8)
        
        # Read content count (offset 0x1DE)
        tmd.seek(0x1DE)
        content_count = struct.unpack('>H', tmd.read(2))[0]
        
        contents = []
        for c in range(content_count):
            tmd.seek(0xB04 + (0x30 * c))
            content_id = tmd.read(0x4).hex()
            
            tmd.seek(0xB08 + (0x30 * c))
            content_index = tmd.read(0x2)
            
            tmd.seek(0xB0A + (0x30 * c))
            content_type = struct.unpack('>H', tmd.read(2))[0]
            
            tmd.seek(0xB0C + (0x30 * c))
            content_size = struct.unpack('>Q', tmd.read(8))[0]
            
            tmd.seek(0xB14 + (0x30 * c))
            content_hash = tmd.read(0x14)
            
            contents.append([content_id, content_index, content_type, content_size, content_hash])
    
    return title_id, contents


def get_encrypted_titlekey(tik_path):
    """Get encrypted titlekey from title.tik or cetk file"""
    for tik_file in [tik_path, tik_path.replace('title.tik', 'cetk')]:
        if os.path.isfile(tik_file):
            try:
                with open(tik_file, 'rb') as f:
                    f.seek(0x1BF)  # Encrypted titlekey offset
                    return f.read(0x10)
            except:
                continue
    return None


def decrypt_game(game_dir, output_dir=None, delete_encrypted=False):
    """Main decryption function"""
    
    if not AES_AVAILABLE:
        print("❌ No AES library available!")
        return False
    
    if not validate_common_key():
        print("⚠ Continuing with potentially incorrect key...")
    
    # Check for required files
    tmd_path = os.path.join(game_dir, 'title.tmd')
    tik_path = os.path.join(game_dir, 'title.tik')
    
    if not os.path.isfile(tmd_path):
        print(f'❌ No TMD (title.tmd) found in {game_dir}')
        return False
    
    # Use input directory as output if not specified
    if output_dir is None:
        output_dir = game_dir
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Game directory: {game_dir}")
    print(f"Output directory: {output_dir}")
    print(f"AES library: {AES_LIBRARY}")
    print(f"Common key: {WIIU_COMMON_KEY[:8]}...{WIIU_COMMON_KEY[-8:]}")
    
    # Parse TMD
    try:
        title_id, contents = parse_tmd(tmd_path)
        print(f'Title ID: {title_id.hex().upper()}')
        print(f'Content count: {len(contents)}')
    except Exception as e:
        print(f'❌ Error parsing TMD: {e}')
        return False
    
    # Get encrypted titlekey
    encrypted_titlekey = get_encrypted_titlekey(tik_path)
    if not encrypted_titlekey:
        print('❌ Missing CETK/title.tik file or cannot read titlekey.')
        return False
    
    print(f'Encrypted Titlekey: {encrypted_titlekey.hex().upper()}')
    
    # Decrypt titlekey
    try:
        ckey = binascii.unhexlify(WIIU_COMMON_KEY)
        iv = title_id + bytes(8)  # Title ID + 8 zero bytes
        decrypted_titlekey = aes_cbc_decrypt(ckey, iv, encrypted_titlekey)
        
        # Trim to 16 bytes if needed
        if len(decrypted_titlekey) > 16:
            decrypted_titlekey = decrypted_titlekey[:16]
            
        print(f'Decrypted Titlekey: {decrypted_titlekey.hex().upper()}')
    except Exception as e:
        print(f'❌ Failed to decrypt titlekey: {e}')
        return False
    
    # Decrypt each content
    successful = 0
    total = len(contents)
    readsize = 8 * 1024 * 1024  # 8MB chunks
    
    for idx, (content_id, content_index, content_type, content_size, content_hash) in enumerate(contents):
        print(f'[{idx+1}/{total}] Decrypting {content_id}...', end='')
        
        app_file = os.path.join(game_dir, content_id + '.app')
        output_file = os.path.join(output_dir, content_id + '.app.dec')
        
        if not os.path.exists(app_file):
            print(f'\n  ⚠ File {app_file} not found, skipping')
            continue
        
        try:
            if content_type & 2:  # Has hash tree
                # Decrypt with hash tree
                chunk_count = os.path.getsize(app_file) // 0x10000
                
                # Check for h3 file
                h3_file = os.path.join(game_dir, content_id + '.h3')
                h3_hashes = b''
                if os.path.exists(h3_file):
                    with open(h3_file, 'rb') as f:
                        h3_hashes = f.read()
                    if hashlib.sha1(h3_hashes).digest() != content_hash:
                        print(f'\n  ⚠ H3 Hash mismatch for {content_id}')
                else:
                    print(f'\n  ⚠ Missing H3 file: {h3_file}')
                
                h0_hash_num = 0
                h1_hash_num = 0
                h2_hash_num = 0
                h3_hash_num = 0
                
                with open(app_file, 'rb') as encrypted, open(output_file, 'wb') as decrypted:
                    for chunk_num in range(chunk_count):
                        show_chunk(chunk_num, chunk_count, content_id)
                        
                        # Decrypt hash tree (0x400 bytes)
                        hash_tree_data = encrypted.read(0x400)
                        hash_tree = aes_cbc_decrypt(decrypted_titlekey, bytes(16), hash_tree_data)
                        
                        # Extract hashes
                        h0_hashes = hash_tree[0:0x140]
                        h1_hashes = hash_tree[0x140:0x280] if h3_hashes else b''
                        h2_hashes = hash_tree[0x280:0x3c0] if h3_hashes else b''
                        
                        # Get h0 hash for this chunk
                        h0_hash = h0_hashes[(h0_hash_num * 0x14):((h0_hash_num + 1) * 0x14)]
                        
                        # Verify hash tree if h3 file exists
                        if h3_hashes:
                            h1_hash = h1_hashes[(h1_hash_num * 0x14):((h1_hash_num + 1) * 0x14)]
                            h2_hash = h2_hashes[(h2_hash_num * 0x14):((h2_hash_num + 1) * 0x14)]
                            h3_hash = h3_hashes[(h3_hash_num * 0x14):((h3_hash_num + 1) * 0x14)]
                            
                            if hashlib.sha1(h0_hashes).digest() != h1_hash:
                                print(f'\n  ⚠ H0 Hashes invalid in chunk {chunk_num}')
                            if hashlib.sha1(h1_hashes).digest() != h2_hash:
                                print(f'\n  ⚠ H1 Hashes invalid in chunk {chunk_num}')
                            if hashlib.sha1(h2_hashes).digest() != h3_hash:
                                print(f'\n  ⚠ H2 Hashes invalid in chunk {chunk_num}')
                        
                        # Decrypt content data (0xFC00 bytes)
                        content_data = encrypted.read(0xFC00)
                        iv = h0_hash[0:0x10]
                        decrypted_data = aes_cbc_decrypt(decrypted_titlekey, iv, content_data)
                        
                        # Verify data hash
                        if hashlib.sha1(decrypted_data).digest() != h0_hash:
                            print(f'\n  ⚠ Data block hash invalid in chunk {chunk_num}')
                        
                        # Write decrypted data
                        decrypted.write(hash_tree)
                        decrypted.write(decrypted_data)
                        
                        # Update hash indices
                        h0_hash_num += 1
                        if h0_hash_num >= 16:
                            h0_hash_num = 0
                            h1_hash_num += 1
                        if h1_hash_num >= 16:
                            h1_hash_num = 0
                            h2_hash_num += 1
                        if h2_hash_num >= 16:
                            h2_hash_num = 0
                            h3_hash_num += 1
                
                print('')
                
            else:
                # Decrypt without hash tree
                file_size = os.path.getsize(app_file)
                
                # Create IV: content_index + 14 zero bytes
                iv = content_index + bytes(14)
                
                content_hash_calc = hashlib.sha1()
                left = file_size
                
                with open(app_file, 'rb') as encrypted, open(output_file, 'wb') as decrypted:
                    chunk_num = 0
                    while left > 0:
                        to_read = min(readsize, left)
                        
                        # Show progress
                        if chunk_num % 10 == 0:
                            show_progress(file_size - left, file_size, content_id)
                        
                        encrypted_content = encrypted.read(to_read)
                        decrypted_content = aes_cbc_decrypt(decrypted_titlekey, iv, encrypted_content)
                        
                        # Update hash
                        actual_bytes = min(to_read, len(decrypted_content))
                        content_hash_calc.update(decrypted_content[:actual_bytes])
                        
                        # Write decrypted data
                        decrypted.write(decrypted_content[:actual_bytes])
                        left -= to_read
                        chunk_num += 1
                
                # Show final progress
                show_progress(file_size, file_size, content_id)
                print('')
                
                # Verify hash
                if content_hash != content_hash_calc.digest():
                    print(f'  ⚠ Content Hash mismatch for {content_id}')
                    print(f'    TMD:    {content_hash.hex().upper()}')
                    print(f'    Result: {content_hash_calc.hexdigest().upper()}')
            
            successful += 1
            print(f'  ✓ Successfully decrypted')
            
            # Delete encrypted file if requested
            if delete_encrypted:
                try:
                    os.remove(app_file)
                    print(f'  ✓ Deleted encrypted file')
                    h3_file = os.path.join(game_dir, content_id + '.h3')
                    if os.path.exists(h3_file):
                        os.remove(h3_file)
                except Exception as e:
                    print(f'  ⚠ Could not delete {app_file}: {e}')
                    
        except Exception as e:
            print(f'\n  ❌ Error decrypting {content_id}: {e}')
            import traceback
            traceback.print_exc()
            continue
    
    print(f'\n✅ Decryption complete! {successful}/{total} files decrypted successfully')
    return successful > 0


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(description='Decrypt Wii U game files')
    parser.add_argument('game_dir', help='Directory containing the downloaded game')
    parser.add_argument('--key', '-k', help='Path to Wii U common key file (uses hardcoded key by default)')
    parser.add_argument('--output', '-o', help='Output directory for decrypted files')
    parser.add_argument('--delete', '-d', action='store_true', help='Delete encrypted files after decryption')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Print startup info
    print("=" * 60)
    print("Wii U Game Decryptor")
    print("=" * 60)
    
    if not os.path.exists(args.game_dir):
        print(f"❌ Game directory not found: {args.game_dir}")
        sys.exit(1)
    
    if args.verbose:
        print(f"Python version: {sys.version}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Game directory: {args.game_dir}")
        print(f"Files in game directory: {os.listdir(args.game_dir)[:10]}...")
    
    try:
        success = decrypt_game(args.game_dir, args.output, args.delete)
        if not success:
            print("\n❌ Decryption failed!")
            sys.exit(1)
        else:
            print("\n✅ Success! Decrypted files have .dec extension")
    except Exception as e:
        print(f"\n❌ Decryption failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()