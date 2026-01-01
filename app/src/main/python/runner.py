#!/usr/bin/env python3

import base64
import binascii
import os
import struct
import sys
import zlib
import time
import json
import subprocess
import re
from urllib.request import urlopen, Request


# PASTE YOUR titlecert HERE (one line, no whitespace)
titlecert = ''

# App categories (needs to be defined at module level)
app_categories = {
    '0000',  # application
    '0002',  # demo
    '000C',  # DLC
}


def download_with_retry(url, max_retries=3, retry_delay=2, **kwargs):
    """Download with automatic retry on failure"""
    for attempt in range(max_retries):
        try:
            return download(url, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  ↻ Retry {attempt + 1}/{max_retries} in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"  ✗ Failed after {max_retries} attempts: {e}")
                raise
    return None


def download(url, printprogress=False, outfile=None, message_prefix='', message_suffix='', bridge=None, chunk_callback=None, token=None):
    """Download a single file with progress tracking"""
    try:
        cn = urlopen(url)
        totalsize = int(cn.headers['content-length'])
        totalread = 0
        
        if not outfile:
            ct = b''
            
        while totalsize > totalread:
            # Check for cancellation
            if token and hasattr(token, 'is_cancelled') and token.is_cancelled():
                print("\nDownload cancelled by user")
                if bridge:
                    bridge.update(0, "Download cancelled", 0, 0, 0, 0)
                return None
            
            # Read in chunks
            toread = min(totalsize - totalread, 64 * 1024)  # 64KB chunks
            co = cn.read(toread)
            if not co:  # End of stream
                break
                
            totalread += len(co)
            
            # Update progress callback
            if chunk_callback and callable(chunk_callback):
                chunk_callback(totalread, totalsize)
            
            # Print progress to console
            if printprogress:
                percent = min(totalread * 100 / totalsize, 100) if totalsize > 0 else 0
                print(f'\r{message_prefix} {percent:5.1f}% {totalread:10} / {totalsize:10} {message_suffix}', end='')
                sys.stdout.flush()
            
            # Write to file
            if outfile:
                outfile.write(co)
            else:
                ct += co
        
        if printprogress:
            print()  # New line after progress
            
        return ct if not outfile else None
        
    except Exception as e:
        print(f"\nDownload error for {url}: {e}")
        if bridge:
            bridge.update(0, f"Download error: {e}", 0, 0, 0, 0)
        raise


def run_decryptor(game_dir, bridge=None, token=None, delete_encrypted=False):
    """
    Run the wiiu_decryptor.py script on the downloaded game directory
    """
    if bridge:
        # For decryption phase, we'll handle it differently
        pass
    
    print(f"\n{'='*60}")
    print(f"STARTING AUTOMATIC DECRYPTION")
    print(f"{'='*60}")
    
    # First try to import directly (works better on Android)
    try:
        import wiiu_decryptor
        
        print(f"✓ Imported wiiu_decryptor module directly")
        print(f"Decrypting files in place: {game_dir}")
        
        if hasattr(wiiu_decryptor, 'main'):
            print(f"Calling wiiu_decryptor.main() directly...")
            
            import sys
            original_argv = sys.argv
            
            try:
                # Set up argv for the decryptor
                sys.argv = ['wiiu_decryptor.py', game_dir]
                if delete_encrypted:
                    sys.argv.append('--delete')
                
                # Run the decryptor
                wiiu_decryptor.main()
                print(f"\n✅ Direct decryption complete!")
                
                if bridge:
                    bridge.update(100, "Decryption complete!", 0, 0, 0, 0)
                    bridge.updateDecryptionProgress(100, "Decryption complete")
                
                return game_dir
            finally:
                # Restore original argv
                sys.argv = original_argv
        else:
            print(f"⚠ wiiu_decryptor doesn't have a main() function, trying subprocess")
            
    except ImportError as e:
        print(f"⚠ Could not import wiiu_decryptor directly: {e}")
        print(f"Falling back to subprocess method...")
    except Exception as e:
        print(f"⚠ Error with direct import: {e}")
        print(f"Falling back to subprocess method...")
    
    # Fallback to subprocess method
    # Get the path to wiiu_decryptor.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    decryptor_script = os.path.join(script_dir, "wiiu_decryptor.py")
    
    # Check multiple possible locations
    if not os.path.exists(decryptor_script):
        print(f"Looking for decryptor at: {decryptor_script}")
        
        # Try current working directory
        cwd_script = os.path.join(os.getcwd(), "wiiu_decryptor.py")
        if os.path.exists(cwd_script):
            decryptor_script = cwd_script
            print(f"Found decryptor in current directory: {decryptor_script}")
        
        # Try looking in parent directories
        elif script_dir:
            parent_dir = os.path.dirname(script_dir)
            parent_script = os.path.join(parent_dir, "wiiu_decryptor.py")
            if os.path.exists(parent_script):
                decryptor_script = parent_script
                print(f"Found decryptor in parent directory: {decryptor_script}")
    
    if not os.path.exists(decryptor_script):
        print(f"❌ Decryptor script not found at: {decryptor_script}")
        print(f"❌ Also tried:")
        print(f"   - {os.path.join(os.getcwd(), 'wiiu_decryptor.py')}")
        print(f"   - {os.path.join(os.path.dirname(script_dir), 'wiiu_decryptor.py')}")
        if bridge:
            bridge.update(0, "Decryptor script missing", 0, 0, 0, 0)
        return None
    
    print(f"✓ Found decryptor script at: {decryptor_script}")
    print(f"Decrypting files in place: {game_dir}")
    
    # Build command - decrypt in the same folder
    cmd = [
        sys.executable, 
        decryptor_script,
        game_dir
    ]
    
    if delete_encrypted:
        cmd.append("--delete")
    
    print(f"Running decryptor: {' '.join(cmd)}")
    
    try:
        # Start the decryptor process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )
        
        # Monitor output for progress
        line_count = 0
        total_files = 0
        current_file = 0
        
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            
            # Check for cancellation
            if token and hasattr(token, 'is_cancelled') and token.is_cancelled():
                process.terminate()
                print("Decryption cancelled by user")
                if bridge:
                    bridge.update(0, "Decryption cancelled", 0, 0, 0, 0)
                return None
            
            line_count += 1
            
            # Show decryptor messages to Android
            if bridge:
                # Clean up the message for Android
                message = line
                
                # Extract meaningful parts
                if "Decrypting" in line and "..." in line:
                    # Extract content ID
                    content_match = re.search(r'Decrypting (\w+)\.\.\.', line)
                    if content_match:
                        message = f"Decrypting: {content_match.group(1)}"
                        current_file += 1
                elif "Chunk" in line:
                    message = line
                elif "%" in line:
                    # Progress line - show as is
                    message = line
                    
                    # Try to extract percentage
                    match = re.search(r'(\d+\.\d+)%', line)
                    if match:
                        percent = float(match.group(1))
                        # Send decryption progress to Android
                        bridge.updateDecryptionProgress(percent, message)
                        
                        # Also send as regular update for compatibility
                        bridge.update(int(percent), message, current_file, total_files, 0, 0)
                elif "Title ID:" in line or "Titlekey" in line:
                    continue  # Skip informational lines
                elif "Found" in line and "files" in line:
                    # Extract total file count
                    match = re.search(r'Found (\d+)', line)
                    if match:
                        total_files = int(match.group(1))
                elif "Successfully decrypted" in line:
                    message = "File decrypted successfully"
                
                # Truncate long messages
                if len(message) > 40:
                    message = message[:37] + "..."
                
                # Update decryption progress
                if not ("%" in line) and not ("Decrypting" in line):
                    bridge.updateDecryptionProgress(0, message)
            
            # Also print to console
            print(f"  [Decryptor] {line}")
        
        # Wait for process to complete
        return_code = process.wait()
        
    except Exception as e:
        print(f"❌ Error running decryptor: {e}")
        if bridge:
            bridge.update(0, f"Decryption error: {e}", 0, 0, 0, 0)
        return None
    
    if return_code == 0:
        print(f"\n✅ Decryption complete!")
        print(f"✅ Decrypted files saved in: {game_dir}")
        
        if bridge:
            bridge.update(100, "Decryption complete!", total_files, total_files, 0, 0)
            bridge.updateDecryptionProgress(100, "Decryption complete")
        
        return game_dir  # Return the same directory (decryption happened in place)
    else:
        print(f"❌ Decryption failed with code: {return_code}")
        if bridge:
            bridge.update(0, f"Decryption failed (code: {return_code})", 0, 0, 0, 0)
        return None


def run_extractor(game_dir, bridge=None, token=None):
    """
    Run the wiiu_extract.py script on the decrypted game directory
    """
    if bridge:
        # For extraction phase, we'll handle it differently
        pass
    
    print(f"\n{'='*60}")
    print(f"STARTING AUTOMATIC EXTRACTION")
    print(f"{'='*60}")
    
    # First try to import directly (works better on Android)
    try:
        import wiiu_extract
        
        print(f"✓ Imported wiiu_extract module directly")
        print(f"Extracting files from: {game_dir}")
        
        if hasattr(wiiu_extract, 'main'):
            print(f"Calling wiiu_extract.main() directly...")
            
            import sys
            original_argv = sys.argv
            
            try:
                # Set up argv for the extractor
                sys.argv = ['wiiu_extract.py', game_dir]
                
                # Run the extractor
                result = wiiu_extract.main(game_dir)
                
                if result:
                    print(f"\n✅ Direct extraction complete!")
                    print(f"✅ Extracted files saved in: {game_dir}")
                    
                    if bridge:
                        bridge.update(100, "Extraction complete!", 0, 0, 0, 0)
                        bridge.updateExtractionProgress(100, "Extraction complete")
                    
                    return game_dir
                else:
                    print(f"❌ Direct extraction failed")
                    if bridge:
                        bridge.update(0, "Extraction failed", 0, 0, 0, 0)
                    return None
            finally:
                sys.argv = original_argv
        else:
            print(f"⚠ wiiu_extract doesn't have a main() function, trying subprocess")
            
    except ImportError as e:
        print(f"⚠ Could not import wiiu_extract directly: {e}")
        print(f"Falling back to subprocess method...")
    except Exception as e:
        print(f"⚠ Error with direct import: {e}")
        print(f"Falling back to subprocess method...")
    
    # Fallback to subprocess method
    # Get the path to wiiu_extract.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    extractor_script = os.path.join(script_dir, "wiiu_extract.py")
    
    # Check multiple possible locations
    if not os.path.exists(extractor_script):
        print(f"Looking for extractor at: {extractor_script}")
        
        # Try current working directory
        cwd_script = os.path.join(os.getcwd(), "wiiu_extract.py")
        if os.path.exists(cwd_script):
            extractor_script = cwd_script
            print(f"Found extractor in current directory: {extractor_script}")
        
        # Try looking in parent directories
        elif script_dir:
            parent_dir = os.path.dirname(script_dir)
            parent_script = os.path.join(parent_dir, "wiiu_extract.py")
            if os.path.exists(parent_script):
                extractor_script = parent_script
                print(f"Found extractor in parent directory: {extractor_script}")
    
    if not os.path.exists(extractor_script):
        print(f"❌ Extractor script not found at: {extractor_script}")
        print(f"❌ Also tried:")
        print(f"   - {os.path.join(os.getcwd(), 'wiiu_extract.py')}")
        print(f"   - {os.path.join(os.path.dirname(script_dir), 'wiiu_extract.py')}")
        if bridge:
            bridge.update(0, "Extractor script missing", 0, 0, 0, 0)
        return None
    
    print(f"✓ Found extractor script at: {extractor_script}")
    print(f"Extracting files from: {game_dir}")
    
    # Build command - extract in the same folder
    cmd = [
        sys.executable, 
        extractor_script,
        game_dir
    ]
    
    print(f"Running extractor: {' '.join(cmd)}")
    
    try:
        # Start the extractor process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )
        
        # Monitor output for progress
        extraction_messages = []
        line_count = 0
        total_files = 0
        extracted_files = 0
        
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            
            # Check for cancellation
            if token and hasattr(token, 'is_cancelled') and token.is_cancelled():
                process.terminate()
                print("Extraction cancelled by user")
                if bridge:
                    bridge.update(0, "Extraction cancelled", 0, 0, 0, 0)
                return None
            
            line_count += 1
            
            # Show extractor messages to Android
            if bridge:
                # Clean up the message for Android
                message = line
                
                # Extract meaningful parts
                if "Extracting" in line and "..." in line:
                    # Extract file name
                    file_match = re.search(r'Extracting (.+)\.\.\.', line)
                    if file_match:
                        filename = file_match.group(1)
                        if len(filename) > 20:
                            filename = "..." + filename[-17:]
                        message = f"Extracting: {filename}"
                        extracted_files += 1
                elif "%" in line:
                    # Progress line - show as is
                    message = line
                    
                    # Try to extract percentage
                    match = re.search(r'(\d+\.\d+)%', line)
                    if match:
                        percent = float(match.group(1))
                        # Send extraction progress to Android
                        bridge.updateExtractionProgress(percent, message)
                        
                        # Also send as regular update for compatibility
                        bridge.update(int(percent), message, extracted_files, total_files, 0, 0)
                elif "Found" in line and "files" in line:
                    # File count line
                    message = line
                    match = re.search(r'Found (\d+)', line)
                    if match:
                        total_files = int(match.group(1))
                elif "Skipping" in line or "Not extracting" in line:
                    # Skip these verbose messages
                    continue
                elif "Extracted" in line or "uncompressed" in line:
                    # Success messages
                    message = line
                
                # Truncate long messages
                if len(message) > 40:
                    message = message[:37] + "..."
                
                # Update extraction progress
                if not ("%" in line) and not ("Extracting" in line):
                    bridge.updateExtractionProgress(0, message)
            
            # Also print to console
            print(f"  [Extractor] {line}")
            
            # Store for summary
            if any(keyword in line.lower() for keyword in ['extracted', 'success', 'complete', 'error']):
                extraction_messages.append(line)
        
        # Wait for process to complete
        return_code = process.wait()
        
    except Exception as e:
        print(f"❌ Error running extractor: {e}")
        if bridge:
            bridge.update(0, f"Extraction error: {e}", 0, 0, 0, 0)
        return None
    
    if return_code == 0:
        print(f"\n✅ Extraction complete!")
        print(f"✅ Extracted files saved in: {game_dir}")
        
        # Show summary of extraction
        if extraction_messages:
            print(f"\nExtraction summary:")
            for msg in extraction_messages[-5:]:  # Show last 5 messages
                print(f"  • {msg}")
        
        if bridge:
            bridge.update(100, "Extraction complete!", total_files, total_files, 0, 0)
            bridge.updateExtractionProgress(100, "Extraction complete")
        
        return game_dir  # Return the same directory (extraction happened in place)
    else:
        print(f"❌ Extraction failed with code: {return_code}")
        if bridge:
            bridge.update(0, f"Extraction failed (code: {return_code})", 0, 0, 0, 0)
        return None


def main_with_progress(title_id: str, work_dir: str, provider_root_doc_uri=None, bridge=None, token=None, auto_decrypt=True, delete_encrypted=False, auto_extract=True) -> str:
    """
    Download WiiU game content from CDN with detailed progress tracking
    
    Args:
        title_id: The game title ID (16 characters)
        work_dir: Directory where files will be downloaded temporarily
        provider_root_doc_uri: Optional URI for Android Storage Access Framework (SAF) destination
        bridge: Progress bridge object for Android UI updates (6 arguments: percent, message, current_file, total_files, downloaded_mb, total_mb)
        token: Cancellation token for user cancellation
        auto_decrypt: Whether to automatically decrypt after download
        delete_encrypted: Whether to delete encrypted files after decryption
        auto_extract: Whether to automatically extract after decryption
    
    Returns:
        Path to the downloaded (and possibly decrypted/extracted) game directory
    """
    
    # Initial setup and validation
    if bridge:
        # Send initial progress with file count 0/0
        bridge.update(0, "Initializing download...", 0, 0, 0, 0)
    
    tid = title_id.upper()
    if len(tid) != 16:
        error_msg = 'Title ID must be 16 characters'
        print(error_msg)
        if bridge:
            bridge.update(0, error_msg, 0, 0, 0, 0)
        return ""
    
    # Create game directory
    game_dir = os.path.join(work_dir, tid)
    os.makedirs(game_dir, exist_ok=True)
    
    # Log the destination
    if provider_root_doc_uri:
        print(f"Downloading to SAF URI: {provider_root_doc_uri}")
    print(f"Temporary download directory: {game_dir}")
    
    # Determine base URL
    sysbase = 'http://nus.cdn.wup.shop.nintendo.net/ccs/download/' + tid
    appbase = 'http://ccs.cdn.wup.shop.nintendo.net/ccs/download/' + tid
    
    base = appbase
    if tid[4:8] not in app_categories:
        base = sysbase
    
    # PHASE 1: Download metadata files (0-25%)
    if bridge:
        bridge.update(5, "Downloading metadata...", 0, 0, 0, 0)
    
    # Try to get titlekeys.json first (for title key lookup)
    titlekeys_file = None
    title_data = None
    title_key = None

    # Check multiple locations for titlekeys.json
    possible_paths = [
        'titlekeys.json',  # Current working directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'titlekeys.json'),  # Script directory
        os.path.join(work_dir, 'titlekeys.json'),  # Work directory
        os.path.join(game_dir, 'titlekeys.json'),  # Game directory
    ]

    # Try each location in order
    for path in possible_paths:
        if os.path.exists(path):
            titlekeys_file = path
            break

    # Check if we have titlekeys.json locally
    if titlekeys_file and os.path.exists(titlekeys_file):
        try:
            with open(titlekeys_file, 'r') as f:
                titlekeys_data = json.load(f)
                title_data = next((t for t in titlekeys_data if t['titleID'] == tid), None)
                if title_data:
                    title_key = title_data.get('titleKey')
                    print(f"✓ Found title key in {os.path.basename(titlekeys_file)}")
        except:
            print("⚠ Could not read titlekeys.json")
    else:
        print("⚠ titlekeys.json not found in any standard location")
    
    # Download CETK/title.tik with different strategies based on title type
    tik_path = os.path.join(game_dir, 'title.tik')
    
    # For system titles (not in app_categories), download from CDN
    if tid[4:8] not in app_categories:
        if bridge:
            bridge.update(10, "Downloading system title ticket...", 0, 0, 0, 0)
        
        if not os.path.exists(tik_path):
            try:
                print(f"  Downloading CETK from CDN...")
                with open(tik_path, 'wb') as f:
                    download_with_retry(base + '/cetk', False, f, bridge=bridge, token=token)
                print(f"  ✓ Downloaded CETK from CDN")
            except Exception as e:
                print(f"  ⚠ Could not download CETK from CDN: {e}")
    
    else:
        # For application/demo/DLC titles
        if bridge:
            bridge.update(10, "Getting title ticket...", 0, 0, 0, 0)
        
        if not os.path.exists(tik_path):
            if title_data and title_data.get('ticket') == 1:
                # Download from titlekeys website (disc version)
                try:
                    print(f"  Downloading disc ticket from titlekeys website...")
                    keysite = 'vault.titlekeys.ovh'
                    request = Request(f'https://{keysite}/ticket/{tid}.tik')
                    request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)')
                    
                    # Download with retry
                    for attempt in range(3):
                        try:
                            response = urlopen(request).read()
                            with open(tik_path, 'wb') as f:
                                f.write(response)
                            print(f"  ✓ Downloaded disc ticket")
                            break
                        except Exception as e:
                            if attempt < 2:
                                print(f"  ↻ Retry {attempt + 1}/3...")
                                time.sleep(2)
                            else:
                                raise e
                except Exception as e:
                    print(f"  ⚠ Could not download disc ticket: {e}")
            
            elif title_key:
                # Generate fake CETK from encrypted title key
                print(f"  Generating fake CETK from title key...")
                print(f"  Note: Fake CETK requires custom firmware to use.")
                
                # This is the TIK template from the original script
                TIKTEM = binascii.a2b_hex(
                    '00010004d15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11a' +
                    'd15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed' +
                    '15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11a' +
                    'd15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed' +
                    '15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11a' +
                    'd15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed' +
                    '15abe11ad15ea5ed15abe11ad15ea5ed15abe11a0000000000000000' +
                    '00000000000000000000000000000000000000000000000000000000' +
                    '00000000000000000000000000000000000000000000000000000000' +
                    '000000000000000000000000000000526f6f742d4341303030303030' +
                    '30332d58533030303030303063000000000000000000000000000000' +
                    '00000000000000000000000000000000000000000000000000feedfa' +
                    'cefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedf' +
                    'acefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefee' +
                    'dfacefeedfacefeedfacefeedface010000ccccccccccccccccccc' +
                    'cccccccccccccc00000000000000000000000000aaaaaaaaaaaaaa' +
                    'aa00000000000000000000000000000000000000000000000000000' +
                    '00000000000000000000000000000000000000000000000000000000' +
                    '00000000000100000000000000000000000000000000000000000000' +
                    '00000000000000000000000000000000000000000000000000000000' +
                    '00000000000000000000000000000000000000000000000000000000' +
                    '00000000000000000000000000000000000000000000000000000000' +
                    '0000000000000000010014000000ac000000140001001400000000' +
                    '000000280000000100000084000000840003000000000000ffffffff' +
                    'ffffffffffffffffffffffffffffffffffffffffffffffffffffffff' +
                    '00000000000000000000000000000000000000000000000000000000' +
                    '00000000000000000000000000000000000000000000000000000000' +
                    '00000000000000000000000000000000000000000000000000000000' +
                    '0000000000000000000000000000000000'
                )
                TK = 0x140
                
                try:
                    # First download TMD to get title version
                    tmd_data = download_with_retry(base + '/tmd', bridge=bridge, token=token)
                    title_version = tmd_data[0x21C:0x21E]  # Title version offset in TMD
                    
                    # Create fake tik
                    tikdata = bytearray(TIKTEM)
                    tikdata[TK + 0xA6:TK + 0xA8] = title_version
                    tikdata[TK + 0x9C:TK + 0xA4] = binascii.a2b_hex(tid)
                    tikdata[TK + 0x7F:TK + 0x8F] = binascii.a2b_hex(title_key)
                    
                    with open(tik_path, 'wb') as f:
                        f.write(tikdata)
                    
                    print(f"  ✓ Generated fake CETK")
                except Exception as e:
                    print(f"  ⚠ Could not generate fake CETK: {e}")
            
            else:
                print(f"  ⚠ No title key available, skipping CETK")
                print(f"  ⚠ Decryption may fail without title.tik")
    
    # Download TMD
    if bridge:
        bridge.update(15, "Downloading title metadata...", 0, 0, 0, 0)
    
    tmd_path = os.path.join(game_dir, 'title.tmd')
    try:
        tmd_data = download_with_retry(base + '/tmd', bridge=bridge, token=token)
    except Exception as e:
        print(f"Failed to download TMD: {e}")
        if bridge:
            bridge.update(0, f"Failed to download TMD: {e}", 0, 0, 0, 0)
        return ""
    
    # Parse TMD to get content list
    contents = []
    total_files = 0
    try:
        total_files = struct.unpack('>H', tmd_data[0x1DE:0x1E0])[0]
        
        # Send total file count to Android
        if bridge:
            bridge.update(20, f"Found {total_files} content files", 0, total_files, 0, 0)
        else:
            print(f"Found {total_files} content files")
        
        for c in range(total_files):
            contents.append([
                # content_id
                binascii.hexlify(tmd_data[0xB04 + (0x30 * c):0xB04 + (0x30 * c) + 0x4]).decode('utf-8'),
                # content_type
                struct.unpack('>H', tmd_data[0xB0A + (0x30 * c):0xB0A + (0x30 * c) + 0x2])[0],
                # content_size
                struct.unpack('>Q', tmd_data[0xB0C + (0x30 * c):0xB0C + (0x30 * c) + 0x8])[0],
            ])
        
        # Save TMD
        with open(tmd_path, 'wb') as f:
            f.write(tmd_data)
            
    except Exception as e:
        print(f"Error parsing TMD: {e}")
        if bridge:
            bridge.update(0, f"Error parsing TMD: {e}", 0, total_files, 0, 0)
        return ""
    
    # Calculate total size for progress (in MB)
    total_size = sum(c[2] for c in contents)
    total_size_mb = total_size / (1024 * 1024)
    print(f"\nTotal download size: {total_size_mb:.1f} MB ({total_files} files)")
    
    # Write certificate (if we have titlecert)
    if bridge:
        bridge.update(25, "Writing certificate...", 0, total_files, 0, total_size_mb)
    
    cert_path = os.path.join(game_dir, 'title.cert')
    try:
        if titlecert:  # Only write if titlecert is provided
            cert_data = base64.b64decode(titlecert + '=' * (-len(titlecert) % 4))
            with open(cert_path, 'wb') as f:
                f.write(zlib.decompress(cert_data))
            print(f"  ✓ Wrote title.cert")
        else:
            print(f"  ⚠ No titlecert provided, skipping title.cert")
    except Exception as e:
        print(f"  ⚠ Could not write certificate: {e}")
    
    # PHASE 2: Download content files (25-95%)
    if bridge:
        bridge.update(30, "Starting content download...", 0, total_files, 0, total_size_mb)
    
    print(f"\n{'='*60}")
    print(f"DOWNLOADING {total_files} CONTENT FILES")
    print(f"{'='*60}\n")
    
    downloaded_size = 0
    downloaded_size_mb = 0
    successful_files = 0
    failed_files = []
    
    # Calculate progress weight for each file based on size
    file_weights = [(c[2] / total_size) * 65 if total_size > 0 else 0 for c in contents]
    
    for i, (content_id, content_type, content_size) in enumerate(contents):
        # Check cancellation
        if token and hasattr(token, 'is_cancelled') and token.is_cancelled():
            print("\nDownload cancelled by user")
            if bridge:
                bridge.update(0, "Download cancelled", successful_files, total_files, downloaded_size_mb, total_size_mb)
            return game_dir  # Return partial download
        
        # Calculate overall progress percentage
        progress_percent = 30 + sum(file_weights[:i]) * 100
        
        # Update bridge for file start WITH FILE COUNT and MB
        file_size_mb = content_size / (1024 * 1024)
        file_msg = f"File {i+1}/{total_files}: {content_id}.app ({file_size_mb:.1f} MB)"
        if bridge:
            # Send current file index (i) and total files, with MB values
            bridge.update(int(progress_percent), file_msg, i, total_files, downloaded_size_mb, total_size_mb)
        
        print(f"[{i+1}/{total_files}] {file_msg}")
        
        # Check if file already exists with correct size
        file_path = os.path.join(game_dir, content_id + '.app')
        if os.path.exists(file_path) and os.path.getsize(file_path) == content_size:
            print(f"  ✓ Already downloaded")
            downloaded_size += content_size
            downloaded_size_mb = downloaded_size / (1024 * 1024)
            successful_files += 1
            
            # Update Android with file completion
            if bridge:
                next_progress = 30 + sum(file_weights[:i+1]) * 100
                bridge.update(int(next_progress), f"Completed {content_id}.app", i+1, total_files, downloaded_size_mb, total_size_mb)
            continue
        
        # Download the .app file
        try:
            # Create progress callback for this file
            def make_progress_callback(file_idx, file_id, file_size, file_size_mb, weight, overall_start, bdg, total_files_count, total_size_mb, current_downloaded_mb):
                file_downloaded = 0
                def callback(chunk_read, chunk_total):
                    nonlocal file_downloaded
                    if bdg and chunk_total > 0:
                        # Calculate progress within this file
                        file_progress = (chunk_read / file_size) * weight * 100
                        current_progress = overall_start + file_progress
                        
                        # Calculate downloaded MB for this file
                        chunk_mb = chunk_read / (1024 * 1024)
                        # Update total downloaded (we need to subtract previously reported chunks)
                        total_downloaded_mb = current_downloaded_mb + chunk_mb
                        
                        # Update message with MB progress
                        msg = f"{file_id}.app: {chunk_mb:.1f}/{file_size_mb:.1f} MB"
                        
                        # Update bridge with current file index and MB values
                        # Only update every 5% to avoid too many calls
                        if int(current_progress) % 5 == 0 or chunk_read == chunk_total:
                            bdg.update(int(current_progress), msg, file_idx, total_files_count, total_downloaded_mb, total_size_mb)
                return callback
            
            # Set up callback if bridge is provided
            callback = None
            if bridge:
                overall_start = 30 + sum(file_weights[:i]) * 100
                callback = make_progress_callback(i, content_id, content_size, file_size_mb, file_weights[i], overall_start, bridge, total_files, total_size_mb, downloaded_size_mb)
            
            # Download with retry
            with open(file_path, 'wb') as f:
                download_with_retry(
                    base + '/' + content_id,
                    printprogress=True,
                    outfile=f,
                    message_prefix='  Progress:',
                    message_suffix=f'MB',
                    bridge=bridge,
                    chunk_callback=callback,
                    token=token,
                    max_retries=3,
                    retry_delay=1
                )
            
            downloaded_size += content_size
            downloaded_size_mb = downloaded_size / (1024 * 1024)
            successful_files += 1
            
            # Update after successful download
            if bridge:
                next_progress = 30 + sum(file_weights[:i+1]) * 100
                bridge.update(int(next_progress), f"Completed {content_id}.app", i+1, total_files, downloaded_size_mb, total_size_mb)
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed_files.append(content_id)
            # Remove partial file if it exists
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Still update file count (this file failed)
            if bridge:
                bridge.update(int(progress_percent), f"Failed {content_id}.app", i+1, total_files, downloaded_size_mb, total_size_mb)
            continue
        
        # Download .h3 file if required
        if content_type & 0x2:
            h3_path = os.path.join(game_dir, content_id + '.h3')
            try:
                print(f"  Downloading hash file...")
                with open(h3_path, 'wb') as f:
                    download_with_retry(
                        base + '/' + content_id + '.h3',
                        printprogress=True,
                        outfile=f,
                        message_prefix='  Hash:',
                        bridge=bridge,
                        token=token,
                        max_retries=2
                    )
            except Exception as e:
                print(f"  ⚠ Hash file failed: {e}")
                # Non-critical, continue
    
    # PHASE 3: Finalize download (95-100%)
    if bridge:
        bridge.update(95, "Finalizing download...", total_files, total_files, downloaded_size_mb, total_size_mb)
    
    # Print download summary
    print(f"\n{'='*60}")
    print(f"DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"Successful files: {successful_files}/{total_files}")
    print(f"Failed files: {len(failed_files)}")
    if failed_files:
        print(f"Failed file IDs: {', '.join(failed_files)}")
    print(f"Total downloaded: {downloaded_size_mb:.1f} MB")
    print(f"Download directory: {game_dir}")
    print(f"{'='*60}")
    
    if failed_files:
        print("⚠ Some files failed to download. You may need to retry.")
    
    # Check if we have title.tik
    tik_exists = os.path.exists(tik_path) and os.path.getsize(tik_path) > 0
    
    final_result_dir = game_dir
    
    if successful_files > 0:
        if tik_exists and auto_decrypt:
            print(f"\n✅ Download complete!")
            print(f"✅ Starting automatic decryption...")
            
            # Run decryption IN THE SAME DIRECTORY
            decryption_result = run_decryptor(game_dir, bridge, token, delete_encrypted)
            
            if decryption_result:
                # Decryption successful, now check if we should extract
                final_result_dir = game_dir
                
                if auto_extract:
                    print(f"\n✅ Decryption successful!")
                    print(f"✅ Starting automatic extraction...")
                    
                    # Run extraction IN THE SAME DIRECTORY
                    extraction_result = run_extractor(game_dir, bridge, token)
                    
                    if extraction_result:
                        print(f"\n✅ Download, decryption, and extraction complete!")
                        print(f"✅ Files ready in: {final_result_dir}")
                        print(f"   (Extracted files should be in various subdirectories)")
                        
                        if bridge:
                            bridge.update(100, "Download, decryption, and extraction complete!", total_files, total_files, downloaded_size_mb, total_size_mb)
                    else:
                        # Extraction failed but decryption succeeded
                        print(f"\n⚠ Decryption complete but extraction failed")
                        print(f"⚠ Decrypted files remain at: {game_dir}")
                        print(f"   (Files have .dec extension)")
                        
                        if bridge:
                            bridge.update(95, "Decryption complete (extraction failed)", total_files, total_files, downloaded_size_mb, total_size_mb)
                else:
                    # Decryption succeeded, extraction not requested
                    print(f"\n✅ Download and decryption complete!")
                    print(f"✅ Files ready in: {final_result_dir}")
                    print(f"   (Decrypted files have .dec extension)")
                    
                    if bridge:
                        bridge.update(100, "Download and decryption complete!", total_files, total_files, downloaded_size_mb, total_size_mb)
            else:
                # Decryption failed but download succeeded
                print(f"\n⚠ Download complete but decryption failed")
                print(f"⚠ Encrypted files remain at: {game_dir}")
                
                if bridge:
                    bridge.update(95, "Download complete (decryption failed)", total_files, total_files, downloaded_size_mb, total_size_mb)
                final_result_dir = game_dir
        else:
            if tik_exists:
                print(f"\n✅ Download complete!")
                print(f"✅ Title.tik file is available for decryption")
            else:
                print(f"\n✅ Download complete!")
                print(f"⚠ Note: No title.tik file was obtained")
                print(f"⚠ Decryption will require manual intervention")
            
            if bridge:
                bridge.update(100, f"Download complete! {successful_files}/{total_files} files", total_files, total_files, downloaded_size_mb, total_size_mb)
    else:
        print(f"\n❌ Download failed - no files downloaded")
        if bridge:
            bridge.update(0, "Download failed - no files downloaded", 0, total_files, 0, total_size_mb)
    
    # If provider_root_doc_uri is provided, we could copy files directly to SAF
    # But for now, we'll let Android handle the copying after download
    if provider_root_doc_uri:
        print(f"\nNote: Files downloaded to temporary location.")
        print(f"Android will copy from: {final_result_dir}")
        print(f"To SAF destination: {provider_root_doc_uri}")
    
    return final_result_dir


# Keep the old signature for backward compatibility
def main_with_progress_old(title_id: str, work_dir: str, bridge=None, token=None) -> str:
    """Backward compatible version without provider_root_doc_uri"""
    return main_with_progress(title_id, work_dir, None, bridge, token, auto_decrypt=True)


def main(title_id: str, work_dir: str) -> str:
    """Simple wrapper without bridge for command line use"""
    return main_with_progress(title_id, work_dir, None, None, None, auto_decrypt=True, auto_extract=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Download Wii U games')
    parser.add_argument('title_id', help='Title ID of the game to download')
    parser.add_argument('work_dir', help='Working directory for downloads')
    parser.add_argument('--no-decrypt', action='store_true', help='Skip automatic decryption')
    parser.add_argument('--delete', '-d', action='store_true', help='Delete encrypted files after decryption')
    parser.add_argument('--extract', '-e', action='store_true', help='Extract after decryption', default=True)
    
    args = parser.parse_args()
    
    if len(args.title_id) != 16:
        print("Error: Title ID must be 16 characters")
        sys.exit(1)
    
    print(f"Starting download for title: {args.title_id}")
    print(f"Output directory: {args.work_dir}")
    if not args.no_decrypt:
        print("Automatic decryption: ENABLED")
        print("Decryption will happen in the same folder")
        if args.delete:
            print("Delete encrypted files: ENABLED")
        if args.extract:
            print("Automatic extraction: ENABLED")
    else:
        print("Automatic decryption: DISABLED")
    
    start_time = time.time()
    result = main_with_progress(
        args.title_id, 
        args.work_dir, 
        auto_decrypt=not args.no_decrypt,
        delete_encrypted=args.delete,
        auto_extract=args.extract
    )
    end_time = time.time()
    
    if result and os.path.exists(result):
        elapsed = end_time - start_time
        print(f"\n✅ Process completed in {elapsed:.1f} seconds")
        print(f"✅ Final output directory: {result}")
        
        # Check for extracted files
        extracted_dirs = [d for d in os.listdir(result) if os.path.isdir(os.path.join(result, d))]
        dec_files = [f for f in os.listdir(result) if f.endswith('.dec')]
        
        if extracted_dirs and any(os.listdir(os.path.join(result, d)) for d in extracted_dirs):
            print(f"✅ Found {len(extracted_dirs)} extracted directories")
        elif dec_files:
            print(f"✅ Found {len(dec_files)} decrypted files (.dec extension)")
        else:
            print("⚠ Files are ENCRYPTED (no .dec files or extracted directories found)")
    else:
        print("\n❌ Process failed")
        sys.exit(1)