#!/usr/bin/env .devstream/bin/python
"""
Test script for DevStream crash prevention features.

Validates:
- PollingObserver usage on macOS
- Crash prevention monitoring
- Risk assessment accuracy
- Diagnostic tool functionality

Author: DevStream QA Team
License: MIT
"""

import sys
import os
import platform
from pathlib import Path

# Add .claude/hooks/devstream to path for imports
hooks_path = Path(__file__).parent / '.claude' / 'hooks' / 'devstream'
if hooks_path.exists():
    sys.path.insert(0, str(hooks_path))
    print(f"✅ Added hooks path: {hooks_path}")
else:
    print(f"⚠️ Hooks path not found: {hooks_path}")

def test_real_time_capture_macos_fix():
    """Test that real_time_capture uses PollingObserver on macOS."""
    try:
        # Import from current directory structure
        from memory.real_time_capture import RealTimeDataCapture

        capture = RealTimeDataCapture()

        if platform.system() == 'Darwin':  # macOS
            assert capture.observer_type == 'polling', f"Expected polling observer on macOS, got {capture.observer_type}"
            print("✅ macOS: Using PollingObserver (kernel panic safe)")
        else:
            assert capture.observer_type == 'native', f"Expected native observer on {platform.system()}, got {capture.observer_type}"
            print(f"✅ {platform.system()}: Using native Observer")

        return True

    except ImportError as e:
        print(f"⚠️ Could not import real_time_capture: {e}")
        return False
    except Exception as e:
        print(f"❌ Real-time capture test failed: {e}")
        return False


def test_crash_prevention_monitor():
    """Test crash prevention monitoring functionality."""
    try:
        # Import directly from file
        sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'monitoring'))
        from crash_prevention import get_crash_monitor, assess_current_risk

        monitor = get_crash_monitor()
        assert monitor is not None, "Crash monitor should be available"

        # Test risk assessment
        risk_metrics = assess_current_risk()
        assert risk_metrics is not None, "Risk assessment should return metrics"
        assert hasattr(risk_metrics, 'risk_level'), "Risk metrics should have risk level"
        assert hasattr(risk_metrics, 'fd_usage_percent'), "Risk metrics should have FD usage"

        print(f"✅ Crash prevention working: Current risk = {risk_metrics.risk_level.value}")
        print(f"   File descriptor usage: {risk_metrics.fd_usage_percent:.1f}%")
        print(f"   Memory usage: {risk_metrics.memory_pressure:.1f}%")

        return True

    except ImportError as e:
        print(f"⚠️ Could not import crash_prevention: {e}")
        return False
    except Exception as e:
        print(f"❌ Crash prevention test failed: {e}")
        return False


def test_crash_diagnostic_tool():
    """Test crash diagnostic tool functionality."""
    try:
        # Import directly from file
        sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'monitoring'))
        from crash_diagnostic import CrashDiagnosticTool, analyze_macos_panic_report

        # Test with sample panic report (simulated)
        sample_panic = """
panic(cpu 1 caller 0xfffffe0029c528e8): Kernel data abort. at pc 0xfffffe0029344bb8
Probabilistic GZAlloc Report:
  Zone    : data.kalloc.24576
  Address : 0xfffffe36094b8000
  Kind    : use-after-free (medium confidence)
Panicked task 0xfffffe1876052410: 551 pages, 16 threads: pid 317: fseventsd
        """

        analysis = analyze_macos_panic_report(sample_panic)
        if analysis:
            print(f"   Analysis result: process='{analysis.process_involved}', correlation={analysis.devstream_correlation:.2f}")

            # More flexible assertions
            assert "fseventsd" in analysis.process_involved, f"Should detect fseventsd process, got '{analysis.process_involved}'"
            assert analysis.filesystem_involvement, "Should detect filesystem involvement"
            assert analysis.memory_corruption, "Should detect memory corruption"
            assert analysis.devstream_correlation > 0.5, f"Should detect DevStream correlation, got {analysis.devstream_correlation}"

            print(f"✅ Crash diagnostic working: Correlation = {analysis.devstream_correlation:.2f}")
            print(f"   Process: {analysis.process_involved}")
            print(f"   Memory corruption: {analysis.memory_corruption}")
            print(f"   Recommendations: {len(analysis.recommendations)}")

            return True
        else:
            print("⚠️ Panic analysis returned None")
            return False

    except ImportError as e:
        print(f"⚠️ Could not import crash_diagnostic: {e}")
        return False
    except Exception as e:
        print(f"❌ Crash diagnostic test failed: {e}")
        return False


def test_environment_configuration():
    """Test environment configuration for crash prevention."""
    print("\n🔧 Environment Configuration Check:")

    # Check ulimit
    try:
        import resource
        fd_limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        print(f"   File descriptor limit: {fd_limit}")

        if fd_limit < 1024:
            print("⚠️ Low file descriptor limit - consider: ulimit -n 2048")
        else:
            print("✅ File descriptor limit adequate")
    except:
        print("⚠️ Could not check file descriptor limit")

    # Check platform
    print(f"   Platform: {platform.system()}")
    print(f"   Python version: {platform.python_version()}")

    # Check if we're in DevStream directory
    current_dir = Path.cwd()
    devstream_indicators = ['.claude', 'CLAUDE.md', 'src']
    is_devstream = any((current_dir / indicator).exists() for indicator in devstream_indicators)

    if is_devstream:
        print("✅ Running in DevStream directory")
    else:
        print("⚠️ Not in DevStream directory")

    return True


def main():
    """Run all crash prevention tests."""
    print("🧪 DevStream Crash Prevention Tests")
    print("=" * 50)

    tests = [
        ("Real-time Capture macOS Fix", test_real_time_capture_macos_fix),
        ("Crash Prevention Monitor", test_crash_prevention_monitor),
        ("Crash Diagnostic Tool", test_crash_diagnostic_tool),
        ("Environment Configuration", test_environment_configuration),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 Testing: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All crash prevention tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed - review crash prevention implementation")
        return 1


if __name__ == "__main__":
    sys.exit(main())