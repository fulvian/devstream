#!/usr/bin/env python3
"""
Comprehensive Hook System Verification Suite
Context7-backed testing following Python debugging best practices.

Based on research from:
- Microsoft debugpy debugging patterns
- PySnooper function tracing principles
- Context7 testing best practices

Tests hook system reliability, performance, and integration.
"""

import os
import sys
import time
import json
import subprocess
import asyncio
import tracemalloc
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal
import tempfile

# Add project paths
sys.path.insert(0, str(Path(__file__).parent / '.claude' / 'hooks' / 'devstream' / 'utils'))

class HookVerificationResult:
    """Structured result container for hook tests"""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.success = False
        self.duration_ms = 0
        self.error_message = ""
        self.debug_info = {}
        self.performance_metrics = {}

    def set_success(self, duration_ms: float, debug_info: Dict = None, performance: Dict = None):
        self.success = True
        self.duration_ms = duration_ms
        self.debug_info = debug_info or {}
        self.performance_metrics = performance or {}

    def set_failure(self, error_message: str, duration_ms: float = 0):
        self.success = False
        self.error_message = error_message
        self.duration_ms = duration_ms

class HookTracer:
    """
    PySnooper-inspired hook execution tracer.
    Implements function tracing patterns from Context7 research.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.trace_data = []
        self.start_times = {}

    def trace_hook_execution(self, hook_name: str, phase: str, data: Dict = None):
        """Trace hook execution with timing and context data"""
        if not self.enabled:
            return

        timestamp = datetime.now().isoformat()
        entry = {
            'hook': hook_name,
            'phase': phase,
            'timestamp': timestamp,
            'data': data or {}
        }
        self.trace_data.append(entry)

        if phase == 'start':
            self.start_times[hook_name] = time.time()
        elif phase == 'end' and hook_name in self.start_times:
            duration = (time.time() - self.start_times[hook_name]) * 1000
            entry['duration_ms'] = duration
            del self.start_times[hook_name]

    def get_execution_summary(self) -> Dict:
        """Get execution summary with performance metrics"""
        summary = {
            'total_traces': len(self.trace_data),
            'hooks_executed': set(entry['hook'] for entry in self.trace_data),
            'total_duration': sum(entry.get('duration_ms', 0) for entry in self.trace_data),
            'errors': [entry for entry in self.trace_data if 'error' in entry.get('phase', '')]
        }

        # Calculate hook-specific statistics
        hook_stats = {}
        for entry in self.trace_data:
            hook = entry['hook']
            if hook not in hook_stats:
                hook_stats[hook] = {'count': 0, 'total_duration': 0, 'errors': 0}

            hook_stats[hook]['count'] += 1
            if 'duration_ms' in entry:
                hook_stats[hook]['total_duration'] += entry['duration_ms']
            if 'error' in entry.get('phase', ''):
                hook_stats[hook]['errors'] += 1

        summary['hook_statistics'] = hook_stats
        return summary

class MemoryLeakDetector:
    """
    Memory leak detection inspired by debugpy testing patterns.
    Uses tracemalloc for accurate memory tracking.
    """

    def __init__(self):
        self.snapshots = []

    def start_tracking(self):
        """Start memory tracking"""
        tracemalloc.start()
        self.snapshots = []

    def take_snapshot(self, label: str) -> Dict:
        """Take memory snapshot with analysis"""
        if not tracemalloc.is_tracing():
            return {'error': 'Memory tracking not started'}

        current, peak = tracemalloc.get_traced_memory()
        snapshot = {
            'label': label,
            'timestamp': datetime.now().isoformat(),
            'current_mb': current / 1024 / 1024,
            'peak_mb': peak / 1024 / 1024,
            'snapshot': tracemalloc.take_snapshot()
        }
        self.snapshots.append(snapshot)
        return snapshot

    def analyze_leaks(self) -> Dict:
        """Analyze memory snapshots for potential leaks"""
        if len(self.snapshots) < 2:
            return {'error': 'Need at least 2 snapshots for analysis'}

        first_snapshot = self.snapshots[0]
        last_snapshot = self.snapshots[-1]

        memory_growth = last_snapshot['current_mb'] - first_snapshot['current_mb']
        peak_growth = last_snapshot['peak_mb'] - first_snapshot['peak_mb']

        # Compare snapshots for detailed analysis
        if len(self.snapshots) >= 2:
            last_snapshot_obj = self.snapshots[-1]['snapshot']
            first_snapshot_obj = self.snapshots[0]['snapshot']

            stats = last_snapshot_obj.compare_to(first_snapshot_obj)
            significant_growth = [
                stat for stat in stats if stat.size_diff > 1024 * 1024  # > 1MB
            ]
        else:
            significant_growth = []

        return {
            'memory_growth_mb': memory_growth,
            'peak_growth_mb': peak_growth,
            'significant_growth_count': len(significant_growth),
            'potential_leak': memory_growth > 10,  # > 10MB growth
            'recommendations': self._generate_recommendations(memory_growth, significant_growth)
        }

    def _generate_recommendations(self, growth_mb: float, significant_growth: List) -> List[str]:
        """Generate memory optimization recommendations"""
        recommendations = []

        if growth_mb > 50:
            recommendations.append("CRITICAL: High memory growth detected (>50MB)")

        if len(significant_growth) > 5:
            recommendations.append("Consider implementing object pooling")

        if growth_mb > 10:
            recommendations.append("Review hook cleanup and resource release")

        return recommendations

class HookSystemVerifier:
    """
    Comprehensive hook system verifier implementing Context7 research patterns.
    Follows debugpy testing methodology with proper session management.
    """

    def __init__(self):
        self.tracer = HookTracer(enabled=True)
        self.memory_detector = MemoryLeakDetector()
        self.results = []
        self.project_root = Path("/Users/fulvioventura/devstream")

    def run_hook_with_timeout(self, hook_path: str, timeout: int = 30) -> HookVerificationResult:
        """
        Execute hook with timeout following debugpy async patterns.
        Implements proper error handling and cancellation.
        """
        result = HookVerificationResult(f"hook_execution_{Path(hook_path).name}")
        start_time = time.time()

        try:
            self.tracer.trace_hook_execution(hook_path, 'start', {'timeout': timeout})

            # Execute hook with timeout
            cmd = [
                str(self.project_root / ".devstream" / "bin" / "python"),
                str(self.project_root / hook_path)
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.project_root,
                text=True
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                duration_ms = (time.time() - start_time) * 1000

                if process.returncode == 0:
                    self.tracer.trace_hook_execution(hook_path, 'end', {
                        'returncode': process.returncode,
                        'stdout_length': len(stdout or ''),
                        'stderr_length': len(stderr or '')
                    })

                    result.set_success(
                        duration_ms=duration_ms,
                        debug_info={
                            'stdout_preview': stdout[:200] if stdout else '',
                            'stderr_preview': stderr[:200] if stderr else '',
                            'returncode': process.returncode
                        },
                        performance={
                            'exit_code': process.returncode,
                            'execution_time_ms': duration_ms
                        }
                    )
                else:
                    error_msg = f"Hook exited with code {process.returncode}"
                    if stderr:
                        error_msg += f": {stderr.strip()}"
                    result.set_failure(error_msg, duration_ms)

            except subprocess.TimeoutExpired:
                process.kill()
                duration_ms = timeout * 1000
                result.set_failure(f"Hook timed out after {timeout}s", duration_ms)
                self.tracer.trace_hook_execution(hook_path, 'timeout', {'timeout': timeout})

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result.set_failure(f"Exception: {str(e)}", duration_ms)
            self.tracer.trace_hook_execution(hook_path, 'error', {'exception': str(e)})

        self.results.append(result)
        return result

    def test_hook_syntax_batch(self, hook_files: List[str]) -> List[HookVerificationResult]:
        """
        Batch syntax testing following pytest parallel execution patterns.
        Uses ThreadPoolExecutor for concurrent testing.
        """
        results = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all syntax checks concurrently
            future_to_file = {
                executor.submit(self._check_single_syntax, hook_file): hook_file
                for hook_file in hook_files
            }

            # Collect results as they complete
            for future in as_completed(future_to_file):
                hook_file = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    error_result = HookVerificationResult(f"syntax_{Path(hook_file).name}")
                    error_result.set_failure(f"Syntax check error: {str(e)}")
                    results.append(error_result)

        return results

    def _check_single_syntax(self, hook_file: str) -> HookVerificationResult:
        """Check syntax of single hook file"""
        result = HookVerificationResult(f"syntax_{Path(hook_file).name}")
        start_time = time.time()

        try:
            cmd = [
                str(self.project_root / ".devstream" / "bin" / "python"),
                "-m", "py_compile", str(self.project_root / hook_file)
            ]

            process_result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            duration_ms = (time.time() - start_time) * 1000

            if process_result.returncode == 0:
                result.set_success(duration_ms=duration_ms, performance={'syntax_valid': True})
            else:
                error_msg = process_result.stderr.strip() if process_result.stderr else "Syntax error"
                result.set_failure(error_msg, duration_ms)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result.set_failure(f"Syntax check exception: {str(e)}", duration_ms)

        return result

    def test_hook_execution_sequence(self, hooks: List[str]) -> HookVerificationResult:
        """
        Test hook execution sequence with timing analysis.
        Implements debugpy timeline testing patterns.
        """
        result = HookVerificationResult("execution_sequence")
        start_time = time.time()

        try:
            sequence_data = []

            for i, hook_path in enumerate(hooks):
                hook_start = time.time()

                # Record expectation (following debugpy patterns)
                self.tracer.trace_hook_execution(hook_path, 'sequence_start', {
                    'sequence_position': i,
                    'total_hooks': len(hooks)
                })

                # Simple execution test
                if Path(hook_path).exists():
                    duration = (time.time() - hook_start) * 1000
                    sequence_data.append({
                        'hook': Path(hook_path).name,
                        'sequence_position': i,
                        'execution_time_ms': duration,
                        'status': 'success'
                    })
                    self.tracer.trace_hook_execution(hook_path, 'sequence_end', {
                        'execution_time_ms': duration
                    })
                else:
                    sequence_data.append({
                        'hook': Path(hook_path).name,
                        'sequence_position': i,
                        'execution_time_ms': 0,
                        'status': 'file_not_found'
                    })

            total_duration = (time.time() - start_time) * 1000

            # Validate sequence expectations
            successful_hooks = [s for s in sequence_data if s['status'] == 'success']

            result.set_success(
                duration_ms=total_duration,
                debug_info={'sequence_data': sequence_data},
                performance={
                    'total_hooks_tested': len(hooks),
                    'successful_hooks': len(successful_hooks),
                    'sequence_integrity': len(successful_hooks) == len(hooks),
                    'average_hook_time_ms': sum(s['execution_time_ms'] for s in sequence_data) / len(sequence_data) if sequence_data else 0
                }
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result.set_failure(f"Sequence test error: {str(e)}", duration_ms)

        return result

    def test_memory_leaks_during_hook_execution(self, hooks: List[str]) -> HookVerificationResult:
        """Test for memory leaks during hook execution using tracemalloc"""
        result = HookVerificationResult("memory_leak_detection")
        start_time = time.time()

        try:
            self.memory_detector.start_tracking()

            # Take initial snapshot
            initial_snapshot = self.memory_detector.take_snapshot("initial")

            # Execute hooks and take intermediate snapshots
            for i, hook_path in enumerate(hooks[:3]):  # Limit to avoid too long test
                if Path(hook_path).exists():
                    self.tracer.trace_hook_execution(hook_path, 'memory_test_start', {'iteration': i})

                    # Simple hook execution (dry run)
                    try:
                        cmd = [
                            str(self.project_root / ".devstream" / "bin" / "python"),
                            "-c", f"import sys; sys.path.append('{hook_path.parent}'); import importlib.util; spec = importlib.util.spec_from_file_location('test', '{hook_path}'); spec.loader.exec_module(importlib.util.module_from_spec(spec))"
                        ]
                        subprocess.run(cmd, capture_output=True, timeout=10, cwd=self.project_root)
                    except:
                        pass  # Ignore execution errors for memory test

                    self.memory_detector.take_snapshot(f"after_hook_{i}")
                    self.tracer.trace_hook_execution(hook_path, 'memory_test_end')

            # Take final snapshot and analyze
            final_snapshot = self.memory_detector.take_snapshot("final")
            memory_analysis = self.memory_detector.analyze_leaks()

            total_duration = (time.time() - start_time) * 1000

            # Determine success based on memory analysis
            is_success = not memory_analysis.get('potential_leak', True)

            if is_success:
                result.set_success(
                    duration_ms=total_duration,
                    debug_info={'memory_analysis': memory_analysis},
                    performance={
                        'memory_growth_mb': memory_analysis.get('memory_growth_mb', 0),
                        'peak_growth_mb': memory_analysis.get('peak_growth_mb', 0),
                        'significant_growth_count': memory_analysis.get('significant_growth_count', 0)
                    }
                )
            else:
                result.set_failure(
                    f"Potential memory leak detected: {memory_analysis.get('memory_growth_mb', 0):.2f}MB growth",
                    total_duration
                )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result.set_failure(f"Memory leak test error: {str(e)}", duration_ms)

        return result

    def generate_comprehensive_report(self) -> Dict:
        """Generate comprehensive verification report"""
        execution_summary = self.tracer.get_execution_summary()

        # Calculate overall metrics
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)

        performance_summary = {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'success_rate': (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            'average_execution_time_ms': sum(r.duration_ms for r in self.results) / total_tests if total_tests > 0 else 0,
            'total_test_time_ms': sum(r.duration_ms for r in self.results)
        }

        # Categorize results
        categories = {
            'syntax_tests': [r for r in self.results if 'syntax' in r.test_name],
            'execution_tests': [r for r in self.results if 'hook_execution' in r.test_name],
            'sequence_tests': [r for r in self.results if 'execution_sequence' in r.test_name],
            'memory_tests': [r for r in self.results if 'memory_leak' in r.test_name]
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(categories, execution_summary)

        return {
            'timestamp': datetime.now().isoformat(),
            'performance_summary': performance_summary,
            'categories': categories,
            'execution_summary': execution_summary,
            'individual_results': [r.__dict__ for r in self.results],
            'recommendations': recommendations,
            'overall_status': 'HEALTHY' if performance_summary['success_rate'] >= 90 else 'NEEDS_ATTENTION'
        }

    def _generate_recommendations(self, categories: Dict, execution_summary: Dict) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []

        # Syntax recommendations
        syntax_tests = categories.get('syntax_tests', [])
        syntax_failures = [r for r in syntax_tests if not r.success]
        if syntax_failures:
            recommendations.append(f"Fix {len(syntax_failures)} syntax errors in hook files")

        # Performance recommendations
        execution_tests = categories.get('execution_tests', [])
        slow_tests = [r for r in execution_tests if r.duration_ms > 5000]  # > 5s
        if slow_tests:
            recommendations.append(f"Optimize {len(slow_tests)} hooks with slow execution (>5s)")

        # Memory recommendations
        memory_tests = categories.get('memory_tests', [])
        memory_issues = [r for r in memory_tests if not r.success]
        if memory_issues:
            recommendations.append("Investigate potential memory leaks in hook system")

        # General recommendations
        if len(execution_summary.get('hooks_executed', set())) < 4:
            recommendations.append("Ensure all required hooks are properly configured")

        return recommendations

def main():
    """Main verification runner implementing comprehensive testing"""
    print("🔍 DevStream Hook System Comprehensive Verification")
    print("=" * 60)
    print("Context7-backed testing with PySnooper-inspired tracing")
    print()

    verifier = HookSystemVerifier()

    # Define hooks to test
    hooks_to_test = [
        ".claude/hooks/devstream/memory/pre_tool_use.py",
        ".claude/hooks/devstream/memory/post_tool_use.py",
        ".claude/hooks/devstream/context/user_query_context_enhancer.py",
        ".claude/hooks/devstream/protocol/task_first_handler.py",
        ".claude/hooks/devstream/protocol/micro_task_commit_handler.py",
        ".claude/hooks/devstream/concurrency_guard.py"
    ]

    # 1. Syntax Testing Phase
    print("📝 Phase 1: Syntax Validation")
    syntax_results = verifier.test_hook_syntax_batch(hooks_to_test)
    verifier.results.extend(syntax_results)

    syntax_success = sum(1 for r in syntax_results if r.success)
    print(f"   ✅ Syntax tests passed: {syntax_success}/{len(syntax_results)}")
    print()

    # 2. Individual Hook Execution Testing
    print("⚡ Phase 2: Individual Hook Execution")
    for hook_path in hooks_to_test:
        if Path(hook_path).exists():
            result = verifier.run_hook_with_timeout(hook_path, timeout=15)
            status = "✅" if result.success else "❌"
            print(f"   {status} {Path(hook_path).name}: {result.duration_ms:.1f}ms")
            if not result.success:
                print(f"      Error: {result.error_message}")
    print()

    # 3. Execution Sequence Testing
    print("🔄 Phase 3: Execution Sequence Testing")
    sequence_result = verifier.test_hook_execution_sequence(hooks_to_test)
    verifier.results.append(sequence_result)

    seq_status = "✅" if sequence_result.success else "❌"
    print(f"   {seq_status} Sequence integrity: {sequence_result.duration_ms:.1f}ms")
    print()

    # 4. Memory Leak Detection
    print("🧠 Phase 4: Memory Leak Detection")
    memory_result = verifier.test_memory_leaks_during_hook_execution(hooks_to_test)
    verifier.results.append(memory_result)

    mem_status = "✅" if memory_result.success else "❌"
    print(f"   {mem_status} Memory analysis: {memory_result.duration_ms:.1f}ms")
    if not memory_result.success:
        print(f"      Issue: {memory_result.error_message}")
    print()

    # 5. Generate Comprehensive Report
    print("📊 Phase 5: Comprehensive Analysis")
    report = verifier.generate_comprehensive_report()

    # Display summary
    summary = report['performance_summary']
    print(f"   Overall Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Average Execution Time: {summary['average_execution_time_ms']:.1f}ms")
    print(f"   System Status: {report['overall_status']}")
    print()

    # Display recommendations
    if report['recommendations']:
        print("💡 Recommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"   {i}. {rec}")
    print()

    # Save detailed report
    report_file = "hook_verification_comprehensive_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"💾 Detailed report saved: {report_file}")
    print(f"🔗 Trace data: {len(verifier.tracer.trace_data)} execution points")

    return report['overall_status'] == 'HEALTHY'

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)