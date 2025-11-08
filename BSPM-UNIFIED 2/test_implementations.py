#!/usr/bin/env python3
"""
Test script for WORKSTREAM 2 implementations
Tests the core functionality implementations without requiring running services
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test that all new modules can be imported"""
    print("Testing imports...")

    try:
        from backend.websocket import ConnectionManager, manager
        print("✓ WebSocket module imported successfully")
    except Exception as e:
        print(f"✗ WebSocket import failed: {e}")
        return False

    try:
        from backend.session_manager import SessionManager
        print("✓ SessionManager module imported successfully")
    except Exception as e:
        print(f"✗ SessionManager import failed: {e}")
        return False

    try:
        from backend.metrics import metrics
        print("✓ Metrics module imported successfully")
    except Exception as e:
        print(f"✗ Metrics import failed: {e}")
        return False

    return True


def test_session_manager():
    """Test session manager functionality"""
    print("\nTesting SessionManager...")

    try:
        from backend.session_manager import SessionManager
        import tempfile
        import shutil

        # Create temporary directory for testing
        test_dir = tempfile.mkdtemp()

        try:
            # Initialize session manager
            sm = SessionManager(storage_path=test_dir, expiration_hours=24)
            print("✓ SessionManager initialized")

            # Create session
            session_data = sm.create_session("test_session_1", {"test": "data"})
            assert session_data['session_id'] == "test_session_1"
            print("✓ Session created")

            # Get session
            retrieved = sm.get_session("test_session_1")
            assert retrieved is not None
            assert retrieved['data']['test'] == "data"
            print("✓ Session retrieved")

            # Update session
            sm.update_session("test_session_1", {"new_key": "new_value"})
            updated = sm.get_session("test_session_1")
            assert updated['data']['new_key'] == "new_value"
            print("✓ Session updated")

            # Get stats
            stats = sm.get_stats()
            assert stats['total_sessions'] == 1
            print(f"✓ Session stats: {stats}")

            # Delete session
            sm.delete_session("test_session_1")
            assert sm.get_session("test_session_1") is None
            print("✓ Session deleted")

            return True

        finally:
            # Cleanup
            shutil.rmtree(test_dir)

    except Exception as e:
        print(f"✗ SessionManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_websocket_manager():
    """Test WebSocket manager functionality"""
    print("\nTesting WebSocket ConnectionManager...")

    try:
        from backend.websocket import ConnectionManager

        # Initialize connection manager
        manager = ConnectionManager()
        print("✓ ConnectionManager initialized")

        # Get connection count
        stats = manager.get_connection_count()
        assert stats['total_connections'] == 0
        assert stats['active_sessions'] == 0
        print(f"✓ Connection stats: {stats}")

        return True

    except Exception as e:
        print(f"✗ ConnectionManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_main_imports():
    """Test that main.py can import all required modules"""
    print("\nTesting main.py imports...")

    try:
        # Test ComfyUI imports
        from backend.comfyui.executor import execute_spritesheet_generation
        from backend.comfyui.workflow_builder import create_spritesheet_workflow
        print("✓ ComfyUI modules imported")

        # Test knowledge base
        from backend.memory.knowledge_base import KnowledgeBase
        print("✓ KnowledgeBase imported")

        # Test session manager
        from backend.session_manager import SessionManager
        print("✓ SessionManager imported")

        # Test websocket
        from backend.websocket import manager as ws_manager
        print("✓ WebSocket manager imported")

        return True

    except Exception as e:
        print(f"✗ Main imports test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics():
    """Test metrics functionality"""
    print("\nTesting Metrics...")

    try:
        from backend.metrics import metrics

        # Test PM agent metrics
        metrics.record_pm_agent_request(requires_approval=True, duration_seconds=1.5)
        print("✓ PM agent metrics recorded")

        # Test art generation metrics
        metrics.record_art_generation(success=True, duration_seconds=120.0)
        print("✓ Art generation metrics recorded")

        # Test knowledge base metrics
        metrics.record_knowledge_base_search()
        print("✓ Knowledge base metrics recorded")

        # Export metrics
        output = metrics.export_metrics()
        assert len(output) > 0
        print("✓ Metrics exported successfully")

        return True

    except Exception as e:
        print(f"✗ Metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("WORKSTREAM 2 - Core Functionality Implementation Tests")
    print("=" * 60)

    tests = [
        ("Module Imports", test_imports),
        ("SessionManager", test_session_manager),
        ("WebSocket Manager", test_websocket_manager),
        ("Main.py Imports", test_main_imports),
        ("Metrics", test_metrics)
    ]

    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
