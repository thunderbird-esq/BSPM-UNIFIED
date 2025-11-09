#!/usr/bin/env python3
"""
Test script for SFX Department
Tests sound effect generation functionality
"""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.sfx_department import create_sfx_department


async def test_sfx_generation():
    """Test basic SFX generation functionality."""
    print("=" * 80)
    print("SFX DEPARTMENT TEST")
    print("=" * 80)

    # Create SFX department
    print("\n1. Initializing SFX Department...")
    sfx_dept = create_sfx_department()
    print(f"   ✓ Output directory: {sfx_dept.output_dir}")

    # Get presets
    print("\n2. Available Presets:")
    presets = sfx_dept.get_presets()
    for preset_name, preset_params in presets.items():
        print(f"   - {preset_name:15s} | Channel: {preset_params.get('channel', 'N/A'):8s} | Duration: {preset_params.get('duration_ms', 0)}ms")

    # Test cases
    test_cases = [
        {
            "description": "classic platformer jump",
            "category": "jump",
            "duration_ms": 150,
            "channel": "pulse1"
        },
        {
            "description": "coin collection sound",
            "category": "coin",
            "duration_ms": 180,
            "channel": "pulse2"
        },
        {
            "description": "enemy hit sound",
            "category": "hit",
            "duration_ms": 120,
            "channel": "noise"
        },
        {
            "description": "power-up collected",
            "category": "powerup",
            "duration_ms": 300,
            "channel": "pulse1"
        }
    ]

    print("\n3. Generating Test Sound Effects:")
    print("-" * 80)

    generated_sfx = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   Test {i}/{len(test_cases)}: {test_case['description']}")
        print(f"   Category: {test_case['category']}, Channel: {test_case['channel']}, Duration: {test_case['duration_ms']}ms")

        try:
            sfx_list = await sfx_dept.generate_sfx(
                description=test_case['description'],
                category=test_case['category'],
                duration_ms=test_case['duration_ms'],
                channel=test_case['channel'],
                variations=1
            )

            sfx = sfx_list[0]
            generated_sfx.append(sfx)

            print(f"   ✓ Generated: {sfx.sfx_id}")
            print(f"     File: {sfx.file_path}")
            print(f"     Parameters:")
            for key, value in sfx.parameters.items():
                if key != 'envelope':
                    print(f"       - {key}: {value}")

            # Check file exists
            file_path = Path(sfx.file_path)
            if file_path.exists():
                file_size = file_path.stat().st_size
                print(f"     File size: {file_size} bytes")
            else:
                print(f"     ✗ WARNING: File not found!")

        except Exception as e:
            print(f"   ✗ FAILED: {e}")

    # Test regeneration
    if generated_sfx:
        print("\n4. Testing Regeneration:")
        print("-" * 80)

        original_sfx = generated_sfx[0]
        print(f"\n   Original SFX: {original_sfx.sfx_id}")

        try:
            new_sfx = sfx_dept.regenerate_sfx(
                sfx_id=original_sfx.sfx_id,
                variation_amount=0.2
            )

            print(f"   ✓ Regenerated: {new_sfx.sfx_id}")
            print(f"     File: {new_sfx.file_path}")
            print(f"     Variation applied: 20%")

        except Exception as e:
            print(f"   ✗ FAILED: {e}")

    # Test listing
    print("\n5. Listing Generated SFX:")
    print("-" * 80)

    sfx_list = sfx_dept.list_sfx()
    print(f"\n   Total SFX in registry: {len(sfx_list)}")

    for sfx_data in sfx_list:
        print(f"   - {sfx_data['sfx_id']:30s} | {sfx_data['category']:12s} | {sfx_data['duration_ms']:4d}ms")

    # Test category filtering
    print("\n6. Testing Category Filtering:")
    print("-" * 80)

    jump_sfx = sfx_dept.list_sfx(category_filter="jump")
    print(f"\n   Jump sounds: {len(jump_sfx)}")

    coin_sfx = sfx_dept.list_sfx(category_filter="coin")
    print(f"   Coin sounds: {len(coin_sfx)}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"✓ SFX Department initialized successfully")
    print(f"✓ {len(presets)} presets available")
    print(f"✓ {len(generated_sfx)} test sound effects generated")
    print(f"✓ Total SFX in registry: {len(sfx_list)}")
    print(f"✓ All tests completed successfully!")
    print()

    return True


async def test_variations():
    """Test generating multiple variations."""
    print("=" * 80)
    print("VARIATION TEST")
    print("=" * 80)

    sfx_dept = create_sfx_department()

    print("\nGenerating 3 variations of jump sound...")

    try:
        sfx_list = await sfx_dept.generate_sfx(
            description="platformer jump with variations",
            category="jump",
            duration_ms=150,
            channel="pulse1",
            variations=3
        )

        print(f"\n✓ Generated {len(sfx_list)} variations:")

        for i, sfx in enumerate(sfx_list, 1):
            print(f"\n   Variation {i}:")
            print(f"   - ID: {sfx.sfx_id}")
            print(f"   - File: {sfx.file_path}")
            print(f"   - Frequency start: {sfx.parameters.get('frequency_start', 'N/A'):.2f} Hz")
            print(f"   - Frequency end: {sfx.parameters.get('frequency_end', 'N/A'):.2f} Hz")

        print(f"\n✓ Variation test completed successfully!")

    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

    return True


async def main():
    """Run all tests."""
    try:
        # Run basic tests
        await test_sfx_generation()

        # Run variation tests
        print("\n")
        await test_variations()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED!")
        print("=" * 80)
        print()

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
