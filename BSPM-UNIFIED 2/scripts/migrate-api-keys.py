#!/usr/bin/env python3
"""
API Key Migration Script
Migrates plaintext API keys to bcrypt hashes.

Usage:
    python scripts/migrate-api-keys.py

This script:
1. Reads plaintext keys from secrets/api_keys.txt
2. Hashes each key using bcrypt
3. Saves hashes to secrets/api_key_hashes.txt
4. Backs up original file to secrets/api_keys.txt.bak
"""

import sys
import os
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import bcrypt


def hash_key(plaintext_key: str) -> str:
    """Hash an API key using bcrypt."""
    key_bytes = plaintext_key.encode('utf-8')
    hash_bytes = bcrypt.hashpw(key_bytes, bcrypt.gensalt())
    return hash_bytes.decode('utf-8')


def migrate_keys(plaintext_file: Path, hash_file: Path):
    """
    Migrate plaintext keys to hashes.

    Args:
        plaintext_file: Path to plaintext keys file
        hash_file: Path to output hash file
    """
    if not plaintext_file.exists():
        print(f"❌ Error: {plaintext_file} does not exist")
        print("   No keys to migrate.")
        return

    # Read plaintext keys
    with open(plaintext_file, 'r') as f:
        plaintext_keys = [line.strip() for line in f if line.strip()]

    if not plaintext_keys:
        print("❌ No keys found in file")
        return

    print(f"📋 Found {len(plaintext_keys)} plaintext keys")

    # Hash each key
    hashes = []
    for i, key in enumerate(plaintext_keys, 1):
        print(f"   🔐 Hashing key {i}/{len(plaintext_keys)}...", end='')
        key_hash = hash_key(key)
        hashes.append(key_hash)
        print(" ✅")

    # Write hashes to file
    with open(hash_file, 'w') as f:
        for key_hash in hashes:
            f.write(key_hash + '\n')

    print(f"✅ Wrote {len(hashes)} hashes to {hash_file}")

    # Backup original file
    backup_file = plaintext_file.parent / f"{plaintext_file.name}.bak"
    plaintext_file.rename(backup_file)
    print(f"📦 Backed up original keys to {backup_file}")

    print("\n⚠️  IMPORTANT SECURITY NOTICE:")
    print("   The original plaintext keys are still in the backup file.")
    print(f"   Delete it securely when migration is confirmed: rm {backup_file}")
    print("\n✅ Migration complete!")


def verify_migration(hash_file: Path, plaintext_keys: list):
    """
    Verify that hashes match plaintext keys.

    Args:
        hash_file: Path to hash file
        plaintext_keys: List of plaintext keys
    """
    with open(hash_file, 'r') as f:
        hashes = [line.strip() for line in f if line.strip()]

    print(f"\n🔍 Verifying {len(hashes)} hashes against plaintext keys...")

    all_valid = True
    for i, (plaintext, hash_str) in enumerate(zip(plaintext_keys, hashes), 1):
        try:
            is_valid = bcrypt.checkpw(plaintext.encode('utf-8'), hash_str.encode('utf-8'))
            if is_valid:
                print(f"   ✅ Key {i} verified")
            else:
                print(f"   ❌ Key {i} verification FAILED")
                all_valid = False
        except Exception as e:
            print(f"   ❌ Key {i} error: {e}")
            all_valid = False

    if all_valid:
        print("\n✅ All keys verified successfully!")
    else:
        print("\n❌ Some keys failed verification. Check logs.")

    return all_valid


def main():
    """Main migration function."""
    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    plaintext_file = project_root / "secrets" / "api_keys.txt"
    hash_file = project_root / "secrets" / "api_key_hashes.txt"

    print("=" * 60)
    print("API Key Migration: Plaintext → Bcrypt Hashes")
    print("=" * 60)
    print(f"Source: {plaintext_file}")
    print(f"Target: {hash_file}")
    print()

    # Check if already migrated
    if hash_file.exists():
        response = input("⚠️  Hash file already exists. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return

    # Read plaintext keys for verification
    if plaintext_file.exists():
        with open(plaintext_file, 'r') as f:
            plaintext_keys = [line.strip() for line in f if line.strip()]
    else:
        plaintext_keys = []

    # Perform migration
    migrate_keys(plaintext_file, hash_file)

    # Verify
    if plaintext_keys:
        verify_migration(hash_file, plaintext_keys)


if __name__ == "__main__":
    main()
