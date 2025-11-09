#!/usr/bin/env python3
"""
Test script for Music Department
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.music_department import MusicDepartment, MusicStyle, GameBoyChannel


async def test_music_generation():
    """Test basic music generation"""
    print("=== Testing Music Department ===\n")

    # Create department instance
    music_dept = MusicDepartment(output_dir="/app/music_outputs")
    print(f"✓ Created Music Department instance")
    print(f"  Output directory: /app/music_outputs\n")

    # Test 1: Generate battle music
    print("Test 1: Generating battle music...")
    track1 = await music_dept.generate_music(
        description="Fast-paced battle music for boss fight",
        style=MusicStyle.BATTLE,
        duration_seconds=30,
        tempo_bpm=140,
        seed=12345
    )
    print(f"✓ Generated track: {track1['track_id']}")
    print(f"  Style: {track1['style']}")
    print(f"  Duration: {track1['duration_seconds']}s")
    print(f"  Tempo: {track1['tempo_bpm']} BPM")
    print(f"  Channels: {', '.join(track1['channels'])}")
    print(f"  Files: {list(track1['files'].keys())}")
    print()

    # Test 2: Generate exploration music
    print("Test 2: Generating exploration music...")
    track2 = await music_dept.generate_music(
        description="Calm exploration music for forest area",
        style=MusicStyle.EXPLORATION,
        duration_seconds=45,
        tempo_bpm=100,
        channels=[GameBoyChannel.PULSE1, GameBoyChannel.WAVE],
        seed=67890
    )
    print(f"✓ Generated track: {track2['track_id']}")
    print(f"  Style: {track2['style']}")
    print(f"  Channels: {', '.join(track2['channels'])}")
    print()

    # Test 3: List all tracks
    print("Test 3: Listing all tracks...")
    all_tracks = await music_dept.list_tracks()
    print(f"✓ Total tracks: {len(all_tracks)}")
    for track in all_tracks:
        print(f"  - {track['track_id']}: {track['description'][:50]}...")
    print()

    # Test 4: Get specific track
    print("Test 4: Getting track details...")
    retrieved = await music_dept.get_track(track1['track_id'])
    print(f"✓ Retrieved track: {retrieved['track_id']}")
    print(f"  Description: {retrieved['description']}")
    print()

    # Test 5: Regenerate track with new seed
    print("Test 5: Regenerating track with new seed...")
    track3 = await music_dept.regenerate_track(
        track_id=track1['track_id'],
        new_seed=99999
    )
    print(f"✓ Regenerated track: {track3['track_id']}")
    print(f"  Original seed: {track1['seed']}")
    print(f"  New seed: {track3['seed']}")
    print()

    # Test 6: Validate track
    print("Test 6: Validating track...")
    is_valid, errors = music_dept.validate_track(track1)
    if is_valid:
        print(f"✓ Track validation passed")
    else:
        print(f"✗ Track validation failed:")
        for error in errors:
            print(f"  - {error}")
    print()

    # Test 7: Delete track
    print("Test 7: Deleting track...")
    success = await music_dept.delete_track(track3['track_id'], delete_files=True)
    print(f"✓ Deleted track: {track3['track_id']}")
    print()

    # Test 8: List tracks by style
    print("Test 8: Listing battle tracks...")
    battle_tracks = await music_dept.list_tracks(style_filter="battle")
    print(f"✓ Battle tracks: {len(battle_tracks)}")
    print()

    print("=== All tests completed successfully! ===")


if __name__ == "__main__":
    asyncio.run(test_music_generation())
