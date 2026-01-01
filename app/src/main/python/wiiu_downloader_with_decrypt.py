# wiiu_downloader_with_decrypt.py

#!/usr/bin/env python3

"""
Enhanced Wii U Downloader with Automatic Decryption
Combines downloading and decryption in one workflow
"""

import os
import sys
import time

# Import the download functionality
# (Assuming the download script is in the same directory or PYTHONPATH)
try:
    from runner import main_with_progress, main_with_progress_old
except ImportError:
    # If the download script is not importable, we'll need to integrate it
    print("Warning: Could not import download script")
    # You would need to copy the download functions here or ensure they're accessible

# Import the decryptor
from wiiu_decryptor import decrypt_game_directory, WiiUDecryptor


def download_and_decrypt(title_id, work_dir, common_key_path=None, 
                         provider_root_doc_uri=None, bridge=None, token=None,
                         delete_encrypted=False, skip_decryption=False):
    """
    Download a Wii U game and automatically decrypt it
    
    Args:
        title_id: The game title ID (16 characters)
        work_dir: Directory where files will be downloaded
        common_key_path: Path to the Wii U common key file
        provider_root_doc_uri: Optional URI for Android Storage Access Framework
        bridge: Progress bridge object for Android UI updates
        token: Cancellation token for user cancellation
        delete_encrypted: Whether to delete encrypted files after decryption
        skip_decryption: Skip decryption step (just download)
    
    Returns:
        Tuple of (download_directory, decrypt_directory) or None on failure
    """
    # PHASE 1: Download the game
    if bridge:
        bridge.update(0, "Starting download...", 0, 0)
    
    print(f"\n{'='*60}")
    print(f"DOWNLOADING TITLE: {title_id}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Call the download function
        if provider_root_doc_uri:
            download_dir = main_with_progress(
                title_id, work_dir, provider_root_doc_uri, bridge, token
            )
        else:
            download_dir = main_with_progress_old(
                title_id, work_dir, bridge, token
            )
    except Exception as e:
        print(f"❌ Download failed: {e}")
        if bridge:
            bridge.update(0, f"Download failed: {e}", 0, 0)
        return None
    
    if not download_dir or not os.path.exists(download_dir):
        print("❌ Download directory not created")
        return None
    
    download_time = time.time() - start_time
    print(f"✅ Download completed in {download_time:.1f} seconds")
    print(f"✅ Files saved to: {download_dir}")
    
    # Check if decryption should be skipped
    if skip_decryption:
        if bridge:
            bridge.update(100, "Download complete (skipped decryption)", 0, 0)
        return download_dir, None
    
    # PHASE 2: Decrypt the game
    if bridge:
        bridge.update(95, "Starting decryption...", 0, 0)
    
    print(f"\n{'='*60}")
    print(f"DECRYPTING GAME")
    print(f"{'='*60}")
    
    decrypt_start = time.time()
    
    try:
        # Create a progress callback for the decryptor
        def decrypt_progress_callback(percent, message):
            if bridge:
                # Map decryption progress from 95% to 100%
                overall_percent = 95 + (percent * 0.05)
                bridge.update(int(overall_percent), f"Decrypting: {message}", 0, 0)
            else:
                print(f"\rDecryption: {message}... {percent:.1f}%", end='', flush=True)
        
        # Initialize decryptor with progress callback
        decryptor = WiiUDecryptor(common_key_path, decrypt_progress_callback)
        
        # Create output directory for decrypted files
        decrypt_dir = os.path.join(work_dir, f"{title_id}_decrypted")
        
        # Decrypt the game
        result_dir = decryptor.decrypt_game(
            download_dir,
            decrypt_dir,
            delete_encrypted
        )
        
        decrypt_time = time.time() - decrypt_start
        
        print(f"\n✅ Decryption completed in {decrypt_time:.1f} seconds")
        print(f"✅ Decrypted files saved to: {result_dir}")
        
        total_time = time.time() - start_time
        print(f"\n✅ Total process completed in {total_time:.1f} seconds")
        
        if bridge:
            bridge.update(100, "Download and decryption complete!", 0, 0)
        
        return download_dir, result_dir
        
    except Exception as e:
        print(f"❌ Decryption failed: {e}")
        if bridge:
            bridge.update(0, f"Decryption failed: {e}", 0, 0)
        
        # Return the download directory even if decryption failed
        return download_dir, None


# Simple wrapper for command-line use
def main():
    """Command-line interface for download and decrypt"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download and decrypt Wii U games')
    parser.add_argument('title_id', help='Title ID of the game to download')
    parser.add_argument('work_dir', help='Working directory for downloads')
    parser.add_argument('--key', '-k', help='Path to Wii U common key file', default=None)
    parser.add_argument('--no-decrypt', action='store_true', help='Skip decryption step')
    parser.add_argument('--delete', '-d', action='store_true', help='Delete encrypted files after decryption')
    
    args = parser.parse_args()
    
    if len(args.title_id) != 16:
        print("Error: Title ID must be 16 characters")
        sys.exit(1)
    
    print(f"Starting download and decrypt for title: {args.title_id}")
    print(f"Working directory: {args.work_dir}")
    
    result = download_and_decrypt(
        args.title_id,
        args.work_dir,
        args.key,
        skip_decryption=args.no_decrypt,
        delete_encrypted=args.delete
    )
    
    if result:
        download_dir, decrypt_dir = result
        if decrypt_dir:
            print(f"\n✅ Success! Game is ready at: {decrypt_dir}")
        else:
            print(f"\n✅ Download complete! Files at: {download_dir}")
            if args.no_decrypt:
                print("   (Decryption was skipped)")
    else:
        print("\n❌ Process failed")
        sys.exit(1)


if __name__ == "__main__":
    main()