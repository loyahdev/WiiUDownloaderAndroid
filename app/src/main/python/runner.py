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

# Import the TK constant and other necessary components from FunKiiU
TK = 0x140  # Ticket offset constant from FunKiiU

# PASTE YOUR titlecert HERE (one line, no whitespace)
titlecert = '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'

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
                print(f'\r{message_prefix} {percent:5.1f}% {totalread:10} / {totalsize:10} bytes', end='')
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


def b64decompress(d):
    """Decompress base64 data - from FunKiiU"""
    return zlib.decompress(base64.b64decode(d))


def patch_ticket_dlc(tikdata):
    """Patch ticket for DLC content - from FunKiiU"""
    tikdata[TK + 0x164:TK + 0x210] = b64decompress('eNpjYGQQYWBgWAPEIgwQNghoADEjELeAMTNE8D8BwEBjAABCdSH/')


def patch_ticket_demo(tikdata):
    """Patch ticket for demo play limit - from FunKiiU"""
    tikdata[TK + 0x124:TK + 0x164] = bytes([0x00] * 64)


def make_ticket(title_id, title_key, title_version, fulloutputpath, patch_demo=False, patch_dlc=False):
    """
    Create a ticket file - adapted from FunKiiU
    """
    # PASTE YOUR TIKTEM HERE (in binascii format as shown in FunKiiU)
    TIKTEM = binascii.a2b_hex('00010004d15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11ad15ea5ed15abe11a000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000526f6f742d434130303030303030332d585330303030303030630000000000000000000000000000000000000000000000000000000000000000000000000000feedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedface010000cccccccccccccccccccccccccccccccc00000000000000000000000000aaaaaaaaaaaaaaaa00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010014000000ac000000140001001400000000000000280000000100000084000000840003000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000')

    tikdata = bytearray(TIKTEM)
    
    # Set title version
    tikdata[TK + 0xA6:TK + 0xA8] = title_version
    
    # Set title ID
    tikdata[TK + 0x9C:TK + 0xA4] = binascii.a2b_hex(title_id)
    
    # Set title key
    tikdata[TK + 0x7F:TK + 0x8F] = binascii.a2b_hex(title_key)
    
    # Check type for patching
    typecheck = title_id[4:8]
    if typecheck == '0002' and patch_demo:
        patch_ticket_demo(tikdata)
    elif typecheck == '000c' and patch_dlc:
        patch_ticket_dlc(tikdata)
    
    # Save ticket
    with open(fulloutputpath, 'wb') as f:
        f.write(tikdata)


def get_ticket_for_title(title_id, title_key, tmd_data, game_dir, patch_demo=False, patch_dlc=False, 
                         onlinetickets=False, bridge=None, token=None):
    """
    Get ticket using FunKiiU logic - either download from CDN or generate
    
    Returns True if ticket was successfully obtained, False otherwise
    """
    tik_path = os.path.join(game_dir, 'title.tik')
    
    # Extract title version from TMD
    title_version = tmd_data[TK + 0x9C:TK + 0x9E] if len(tmd_data) > TK + 0x9E else b'\x00\x00'
    
    # Determine title type
    typecheck = title_id[4:8]
    
    # For updates (000e), get ticket from Nintendo CDN
    if typecheck == '000e':
        if bridge:
            bridge.update(10, "Getting update ticket from Nintendo...", 0, 0, 0, 0)
        
        print(f"  This is an update, getting ticket from Nintendo")
        baseurl = 'http://ccs.cdn.c.shop.nintendowifi.net/ccs/download/' + title_id.lower()
        try:
            with open(tik_path, 'wb') as f:
                download_with_retry(baseurl + '/cetk', False, f, bridge=bridge, token=token)
            print(f"  ✓ Downloaded update ticket from Nintendo")
            return True
        except Exception as e:
            print(f"  ✗ Could not download update ticket: {e}")
            return False
    
    # For applications/demos/DLCs
    if bridge:
        bridge.update(10, "Getting ticket...", 0, 0, 0, 0)
    
    # If onlinetickets mode, we would download from keysite (not implemented here)
    # Otherwise, generate ticket if we have title key
    if title_key:
        try:
            print(f"  Generating ticket with title key...")
            make_ticket(title_id.lower(), title_key, title_version, tik_path, patch_demo, patch_dlc)
            print(f"  ✓ Generated ticket")
            return True
        except Exception as e:
            print(f"  ✗ Could not generate ticket: {e}")
            return False
    else:
        print(f"  ⚠ No title key available for ticket generation")
        print(f"  ⚠ Trying to download from CDN instead...")
        
        # Try to download from CDN as fallback
        baseurl = 'http://ccs.cdn.c.shop.nintendowifi.net/ccs/download/' + title_id.lower()
        try:
            with open(tik_path, 'wb') as f:
                download_with_retry(baseurl + '/cetk', False, f, bridge=bridge, token=token)
            print(f"  ✓ Downloaded ticket from CDN")
            return True
        except Exception as e:
            print(f"  ✗ Could not download ticket: {e}")
            return False


def main_with_progress(title_id: str, work_dir: str, provider_root_doc_uri=None, bridge=None, token=None, 
                       auto_decrypt=True, delete_encrypted=False, auto_extract=True, 
                       patch_demo=True, patch_dlc=True) -> str:
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
        patch_demo: Whether to patch demo play limit (from FunKiiU)
        patch_dlc: Whether to patch DLC content (from FunKiiU)
    
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
        os.path.join(work_dir, '..', 'titlekeys.json'),  # Parent of work directory
        os.path.join(os.getcwd(), 'titlekeys.json'),  # Current working directory (alternative)
    ]

    # Try each location in order
    for path in possible_paths:
        if os.path.exists(path):
            titlekeys_file = path
            print(f"Found titlekeys.json at: {path}")
            break

    # Check if we have titlekeys.json locally
    if titlekeys_file and os.path.exists(titlekeys_file):
        try:
            with open(titlekeys_file, 'r') as f:
                titlekeys_data = json.load(f)
                print(f"Loaded {len(titlekeys_data)} titles from {os.path.basename(titlekeys_file)}")
                
                # Convert both to lowercase for case-insensitive matching
                tid_lower = tid.lower()
                print(f"Looking for title ID: {tid_lower}")
                
                title_data = next((t for t in titlekeys_data if t['titleID'].lower() == tid_lower), None)
                if title_data:
                    title_key = title_data.get('titleKey')
                    print(f"✓ Found title key in {os.path.basename(titlekeys_file)}")
                    print(f"  Title: {title_data.get('name', 'Unknown')}")
                    print(f"  Region: {title_data.get('region', 'Unknown')}")
                    ticket_flag = title_data.get('ticket')
                    print(f"  Ticket flag: {ticket_flag} (type: {type(ticket_flag)})")
                    
                    # Debug: print the actual title key
                    if title_key:
                        print(f"  Title key: {title_key}")
                    else:
                        print(f"  ⚠ No title key found for this title")
                else:
                    print(f"⚠ Title ID {tid_lower} not found in {os.path.basename(titlekeys_file)}")
        except Exception as e:
            print(f"⚠ Could not read titlekeys.json: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠ titlekeys.json not found in any standard location")
    
    # Download TMD first
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
    
    # Get ticket using FunKiiU logic
    if not get_ticket_for_title(tid, title_key, tmd_data, game_dir, patch_demo, patch_dlc, False, bridge, token):
        print(f"⚠ Could not get ticket for title {tid}")
        print(f"⚠ Decryption will require manual ticket placement")
    
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
            # PASTE YOUR MAGIC HERE (in binascii format as shown in FunKiiU)
            MAGIC = binascii.a2b_hex('00010003704138EFBBBDA16A987DD901326D1C9459484C88A2861B91A312587AE70EF6237EC50E1032DC39DDE89A96A8E859D76A98A6E7E36A0CFE352CA893058234FF833FCB3B03811E9F0DC0D9A52F8045B4B2F9411B67A51C44B5EF8CE77BD6D56BA75734A1856DE6D4BED6D3A242C7C8791B3422375E5C779ABF072F7695EFA0F75BCB83789FC30E3FE4CC8392207840638949C7F688565F649B74D63D8D58FFADDA571E9554426B1318FC468983D4C8A5628B06B6FC5D507C13E7A18AC1511EB6D62EA5448F83501447A9AFB3ECC2903C9DD52F922AC9ACDBEF58C6021848D96E208732D3D1D9D9EA440D91621C7A99DB8843C59C1F2E2C7D9B577D512C166D6F7E1AAD4A774A37447E78FE2021E14A95D112A068ADA019F463C7A55685AABB6888B9246483D18B9C806F474918331782344A4B8531334B26303263D9D2EB4F4BB99602B352F6AE4046C69A5E7E8E4A18EF9BC0A2DED61310417012FD824CC116CFB7C4C1F7EC7177A17446CBDE96F3EDD88FCD052F0B888A45FDAF2B631354F40D16E5FA9C2C4EDA98E798D15E6046DC5363F3096B2C607A9D8DD55B1502A6AC7D3CC8D8C575998E7D796910C804C495235057E91ECD2637C9C1845151AC6B9A0490AE3EC6F47740A0DB0BA36D075956CEE7354EA3E9A4F2720B26550C7D394324BC0CB7E9317D8A8661F42191FF10B08256CE3FD25B745E5194906B4D61CB4C2E000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000526F6F7400000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001434130303030303030330000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000007BE8EF6CB279C9E2EEE121C6EAF44FF639F88F078B4B77ED9F9560B0358281B50E55AB721115A177703C7A30FE3AE9EF1C60BC1D974676B23A68CC04B198525BC968F11DE2DB50E4D9E7F071E562DAE2092233E9D363F61DD7C19FF3A4A91E8F6553D471DD7B84B9F1B8CE7335F0F5540563A1EAB83963E09BE901011F99546361287020E9CC0DAB487F140D6626A1836D27111F2068DE4772149151CF69C61BA60EF9D949A0F71F5499F2D39AD28C7005348293C431FFBD33F6BCA60DC7195EA2BCC56D200BAF6D06D09C41DB8DE9C720154CA4832B69C08C69CD3B073A0063602F462D338061A5EA6C915CD5623579C3EB64CE44EF586D14BAAA8834019B3EEBEED3790001000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000100042EA66C66CFF335797D0497B77A197F9FE51AB5A41375DC73FD9E0B10669B1B9A5B7E8AB28F01B67B6254C14AA1331418F25BA549004C378DD72F0CE63B1F7091AAFE3809B7AC6C2876A61D60516C43A63729162D280BE21BE8E2FE057D8EB6E204242245731AB6FEE30E5335373EEBA970D531BBA2CB222D9684387D5F2A1BF75200CE0656E390CE19135B59E14F0FA5C1281A7386CCD1C8EC3FAD70FBCE74DEEE1FD05F46330B51F9B79E1DDBF4E33F14889D05282924C5F5DC2766EF0627D7EEDC736E67C2E5B93834668072216D1C78B823A072D34FF3ECF9BD11A29AF16C33BD09AFB2D74D534E027C19240D595A68EBB305ACC44AB38AB820C6D426560C000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000526F6F742D43413030303030303033000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000143503030303030303062000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000137A080BA689C590FD0B2F0D4F56B632FB934ED0739517B33A79DE040EE92DC31D37C7F73BF04BD3E44E20AB5A6FEAF5984CC1F6062E9A9FE56C3285DC6F25DDD5D0BF9FE2EFE835DF2634ED937FAB0214D104809CF74B860E6B0483F4CD2DAB2A9602BC56F0D6BD946AED6E0BE4F08F26686BD09EF7DB325F82B18F6AF2ED525BFD828B653FEE6ECE400D5A48FFE22D538BB5335B4153342D4335ACF590D0D30AE2043C7F5AD214FC9C0FE6FA40A5C86506CA6369BCEE44A32D9E695CF00B4FD79ADB568D149C2028A14C9D71B850CA365B37F70B657791FC5D728C4E18FD22557C4062D74771533C70179D3DAE8F92B117E45CB332F3B3C2A22E705CFEC66F6DA3772B000100010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010004919EBE464AD0F552CD1B72E7884910CF55A9F02E50789641D896683DC005BD0AEA87079D8AC284C675065F74C8BF37C88044409502A022980BB8AD48383F6D28A79DE39626CCB2B22A0F19E41032F094B39FF0133146DEC8F6C1A9D55CD28D9E1C47B3D11F4F5426C2C780135A2775D3CA679BC7E834F0E0FB58E68860A71330FC95791793C8FBA935A7A6908F229DEE2A0CA6B9B23B12D495A6FE19D0D72648216878605A66538DBF376899905D3445FC5C727A0E13E0E2C8971C9CFA6C60678875732A4E75523D2F562F12AABD1573BF06C94054AEFA81A71417AF9A4A066D0FFC5AD64BAB28B1FF60661F4437D49E1E0D9412EB4BCACF4CFD6A3408847982000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000526F6F742D43413030303030303033000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000158533030303030303063000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000137A0894AD505BB6C67E2E5BDD6A3BEC43D910C772E9CC290DA58588B77DCC11680BB3E29F4EABBB26E98C2601985C041BB14378E689181AAD770568E928A2B98167EE3E10D072BEEF1FA22FA2AA3E13F11E1836A92A4281EF70AAF4E462998221C6FBB9BDD017E6AC590494E9CEA9859CEB2D2A4C1766F2C33912C58F14A803E36FCCDCCCDC13FD7AE77C7A78D997E6ACC35557E0D3E9EB64B43C92F4C50D67A602DEB391B06661CD32880BD64912AF1CBCB7162A06F02565D3B0ECE4FCECDDAE8A4934DB8EE67F3017986221155D131C6C3F09AB1945C206AC70C942B36F49A1183BCD78B6E4B47C6C5CAC0F8D62F897C6953DD12F28B70C5B7DF751819A98346526250001000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000')

            # Write certificate using MAGIC from FunKiiU
            with open(cert_path, 'wb') as f:
                f.write(MAGIC)
            print(f"  ✓ Wrote title.cert (using FunKiiU MAGIC)")
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
                    message_suffix='bytes',
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
                        message_suffix='bytes',
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
    tik_path = os.path.join(game_dir, 'title.tik')
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