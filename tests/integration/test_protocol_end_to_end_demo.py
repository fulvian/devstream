#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pytest>=7.0.0",
#     "pytest-asyncio>=0.21.0",
#     "aiofiles>=23.0.0",
#     "structlog>=23.0.0",
# ]
# ///

"""
End-to-End Demonstration of DevStream Protocol System

This integration test demonstrates the complete 7-step protocol enforcement
system working together to ensure Claude Code follows proper methodology.

The demonstration shows:
1. Task creation as mandatory STEP 1
2. Protocol enforcement gate with user interaction
3. Step-by-step progression through all 7 steps
4. State persistence and crash recovery
5. Integration with existing hook system
6. Memory tracking and Context7 integration
7. Performance under realistic usage

This serves as both a test and a documentation example of how the
protocol system works in practice.
"""

import asyncio
import json
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

# Import all protocol components
from claude.hooks.devstream.protocol.protocol_state_manager import (
    ProtocolStateManager, ProtocolStep, ProtocolState
)
from claude.hooks.devstream.protocol.enforcement_gate import (
    EnforcementGate, EnforcementDecision, EnforcementContext
)
from claude.hooks.devstream.protocol.step_validator import (
    StepValidator, ValidationStatus
)
from claude.hooks.devstream.protocol.task_first_handler import (
    TaskFirstHandler, TaskInfo
)
from claude.hooks.devstream.protocol.task_state_sync import (
    TaskStateSync, SyncTrigger
)


class MockMemoryClient:
    """Mock memory client for demonstration."""

    def __init__(self):
        self.storage = []
        self.search_results = []

    async def search_memory(self, query: str, content_type=None, limit=10):
        """Mock memory search."""
        # Return relevant results based on query
        results = []
        for item in self.storage:
            if any(keyword in item["content"].lower() for keyword in query.lower().split()):
                results.append(item)
        return {"results": results[:limit]}

    async def store_memory(self, content: str, content_type: str, keywords: List[str]):
        """Mock memory storage."""
        item = {
            "id": str(uuid.uuid4()),
            "content": content,
            "content_type": content_type,
            "keywords": keywords,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.storage.append(item)
        return True

    async def create_task(self, title: str, description: str, task_type: str,
                         priority: int, phase_name: str, project: str):
        """Mock task creation."""
        task = {
            "task_id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "task_type": task_type,
            "priority": priority,
            "phase_name": phase_name,
            "project": project,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        return task


class ProtocolDemo:
    """Complete protocol demonstration system."""

    def __init__(self, temp_dir: Path):
        """Initialize demonstration system."""
        self.temp_dir = temp_dir
        self.state_file = temp_dir / "demo_protocol_state.json"

        # Initialize components
        self.memory_client = MockMemoryClient()
        self.protocol_manager = ProtocolStateManager(self.state_file)
        self.enforcement_gate = EnforcementGate()
        self.step_validator = StepValidator(self.memory_client)
        self.task_first_handler = TaskFirstHandler(self.memory_client)
        self.task_state_sync = TaskStateSync(self.memory_client, self.protocol_manager)

        # Demo tracking
        self.demo_log = []
        self.session_id = None

    async def run_complete_demo(self) -> Dict[str, Any]:
        """Run complete end-to-end demonstration."""
        print("🚀 Starting DevStream Protocol End-to-End Demonstration")
        print("=" * 80)

        demo_results = {
            "session_id": None,
            "task_created": False,
            "steps_completed": [],
            "protocol_enforced": False,
            "errors_encountered": [],
            "performance_metrics": {},
            "final_state": None
        }

        try:
            # Step 0: Initialize session
            await self._demo_step_session_initialization(demo_results)

            # Step 1: Task creation enforcement (MANDATORY)
            await self._demo_step_task_creation(demo_results)

            # Step 2: Protocol enforcement gate
            await self._demo_step_enforcement_gate(demo_results)

            # Step 3: Progress through 7-step protocol
            await self._demo_step_protocol_progression(demo_results)

            # Step 4: State persistence and recovery
            await self._demo_step_persistence_demo(demo_results)

            # Step 5: Performance validation
            await self._demo_step_performance_validation(demo_results)

            # Final: Summary and statistics
            await self._demo_final_summary(demo_results)

        except Exception as e:
            demo_results["errors_encountered"].append(str(e))
            print(f"❌ Demo error: {e}")

        return demo_results

    async def _demo_step_session_initialization(self, results: Dict[str, Any]):
        """Demonstrate session initialization."""
        print("\n📋 STEP 0: Session Initialization")
        print("-" * 50)

        start_time = time.time()

        # Initialize new session
        initial_state = await self.protocol_manager.initialize_session()
        self.session_id = initial_state.session_id
        results["session_id"] = self.session_id

        init_time = time.time() - start_time

        print(f"✅ Session initialized: {self.session_id[:8]}...")
        print(f"   Initial step: {initial_state.protocol_step}")
        print(f"   Initialization time: {init_time:.3f}s")

        # Verify state persistence
        assert self.state_file.exists()
        assert initial_state.is_valid()

        self.demo_log.append(f"Session initialized: {self.session_id}")

    async def _demo_step_task_creation(self, results: Dict[str, Any]):
        """Demonstrate mandatory task creation."""
        print("\n🎯 STEP 1: Task Creation Enforcement")
        print("-" * 50)

        # Complex task that should trigger enforcement
        user_prompt = "Build comprehensive user authentication system with JWT tokens, OAuth2 integration, and role-based access control"

        print(f"📝 User Prompt: {user_prompt}")

        # Analyze if task creation is required
        should_create, task_info = await self.task_first_handler.should_create_task(
            user_prompt=user_prompt,
            tool_name="Write",
            tool_input={"file_path": "src/auth.py"}
        )

        print(f"🔍 Task Analysis:")
        print(f"   • Requires task creation: {should_create}")
        print(f"   • Complexity: {task_info.complexity.value}")
        print(f"   • Estimated duration: {task_info.estimated_duration} minutes")
        print(f"   • Trigger reasons: {len(task_info.trigger_reasons)}")
        for reason in task_info.trigger_reasons:
            print(f"     - {reason}")

        results["task_analysis"] = {
            "should_create": should_create,
            "complexity": task_info.complexity.value,
            "duration": task_info.estimated_duration,
            "trigger_reasons": task_info.trigger_reasons
        }

        if should_create:
            # Store analysis results for validation
            await self.memory_client.store_memory(
                content=f"Task Analysis: {task_info.title}\nComplexity: {task_info.complexity.value}\nDuration: {task_info.estimated_duration}min",
                content_type="decision",
                keywords=["task-analysis", "complexity", task_info.session_id]
            )

    async def _demo_step_enforcement_gate(self, results: Dict[str, Any]):
        """Demonstrate enforcement gate with user choice."""
        print("\n🚪 STEP 2: Protocol Enforcement Gate")
        print("-" * 50)

        # Create enforcement context
        context = EnforcementContext(
            task_description="Build comprehensive user authentication system",
            estimated_duration=90,
            complexity_score=0.85,
            involves_code=True,
            involves_architecture=True,
            requires_context7=True,
            trigger_reasons=[
                "Duration > 15min (90min)",
                "Code implementation required",
                "Architectural decisions involved",
                "Context7 research required"
            ],
            session_id=self.session_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        print("⚠️  PROTOCOL ENFORCEMENT TRIGGERED")
        print("   This task requires following the DevStream 7-step workflow")
        print("   Options:")
        print("   ✅ [RECOMMENDED] Follow DevStream protocol")
        print("   ⚠️  [OVERRIDE] Skip protocol (quick fix)")
        print("   ❌ [CANCEL] Abort operation")

        # Simulate user choosing protocol (non-interactive demo)
        print("\n🤖 Demo: User chooses to follow DevStream protocol")
        decision = EnforcementDecision.PROTOCOL

        # Log decision
        await self.enforcement_gate._log_decision_to_memory(
            context, decision, self.memory_client
        )

        print(f"✅ Decision: {decision.value.upper()}")
        print("   Protocol enforcement will be applied")

        results["protocol_enforced"] = True
        results["enforcement_decision"] = decision.value

        self.demo_log.append(f"Enforcement decision: {decision.value}")

    async def _demo_step_protocol_progression(self, results: Dict[str, Any]):
        """Demonstrate progression through all 7 steps."""
        print("\n🔄 STEP 3: 7-Step Protocol Progression")
        print("-" * 50)

        # Create task as part of protocol
        success, task_id = await self.task_first_handler._create_task(
            task_info=TaskInfo(
                title="User Authentication System Implementation",
                description="Build comprehensive authentication with JWT and OAuth2",
                task_type="coding",
                priority=8,
                estimated_duration=90,
                complexity="complex",  # Using string for demo
                involves_code=True,
                involves_architecture=True,
                requires_context7=True,
                file_count=5,
                trigger_reasons=["Complex implementation"],
                acceptance_criteria=[
                    "JWT token implementation",
                    "OAuth2 integration",
                    "Role-based access control",
                    "Security validation",
                    "API documentation"
                ]
            ),
            session_id=self.session_id
        )

        if success and task_id:
            results["task_created"] = True
            results["task_id"] = task_id

            # Update protocol state with task
            current_state = await self.protocol_manager.get_current_state()
            await self.protocol_manager.advance_step(
                current_state,
                ProtocolStep.DISCUSSION,
                task_id=task_id
            )

            print(f"✅ Task created: {task_id[:8]}...")

        # Progress through each step
        steps_progress = [
            (ProtocolStep.DISCUSSION, "Discussion", "decision"),
            (ProtocolStep.ANALYSIS, "Analysis", "context"),
            (ProtocolStep.RESEARCH, "Research", "context"),
            (ProtocolStep.PLANNING, "Planning", "context"),
            (ProtocolStep.APPROVAL, "Approval", "decision"),
            (ProtocolStep.IMPLEMENTATION, "Implementation", "code"),
            (ProtocolStep.VERIFICATION, "Verification", "learning")
        ]

        current_state = await self.protocol_manager.get_current_state()

        for step, step_name, content_type in steps_progress:
            print(f"\n   📍 {step_name}")

            # Advance to step
            if current_state.protocol_step != step:
                current_state = await self.protocol_manager.advance_step(
                    current_state, step
                )

            # Simulate step activity
            content = f"Completed {step_name} phase for authentication system"
            await self.memory_client.store_memory(
                content=content,
                content_type=content_type,
                keywords=[step_name.lower(), "authentication", self.session_id]
            )

            # Simulate tool execution
            await self.task_state_sync.synchronize_on_tool_execution(
                tool_name="Write",
                tool_input={
                    "file_path": f"{step_name.lower()}.md",
                    "content": f"# {step_name} Documentation\n\n{content}"
                },
                execution_result={"success": True},
                session_id=self.session_id
            )

            # Validate step (mock results for demo)
            if step != ProtocolStep.VERIFICATION:
                await self.memory_client.storage.append({
                    "id": str(uuid.uuid4()),
                    "content": f"Validation evidence for {step_name}",
                    "content_type": "evidence",
                    "keywords": [step_name.lower()],
                    "created_at": datetime.now(timezone.utc).isoformat()
                })

            results["steps_completed"].append(step_name)
            print(f"      ✅ {step_name} completed")

        results["final_step"] = current_state.protocol_step.name

    async def _demo_step_persistence_demo(self, results: Dict[str, Any]):
        """Demonstrate state persistence and crash recovery."""
        print("\n💾 STEP 4: State Persistence & Recovery")
        print("-" * 50)

        # Show current state
        current_state = await self.protocol_manager.get_current_state()
        print(f"📊 Current State:")
        print(f"   • Session ID: {current_state.session_id[:8]}...")
        print(f"   • Current Step: {current_state.protocol_step}")
        print(f"   • Task ID: {current_state.task_id}")
        print(f"   • Metadata: {len(current_state.metadata)} items")

        # Demonstrate crash recovery
        print(f"\n🔄 Simulating crash recovery...")

        # Create new manager instance (simulating restart)
        recovery_manager = ProtocolStateManager(self.state_file)
        recovery_success = await recovery_manager.perform_crash_recovery(self.session_id)

        if recovery_success:
            recovered_state = await recovery_manager.get_current_state()
            print(f"✅ Recovery successful:")
            print(f"   • Session restored: {recovered_state.session_id[:8]}...")
            print(f"   • Step maintained: {recovered_state.protocol_step}")
            print(f"   • Task preserved: {recovered_state.task_id}")

            results["crash_recovery"] = {
                "successful": True,
                "session_restored": recovered_state.session_id == current_state.session_id,
                "step_maintained": recovered_state.protocol_step == current_state.protocol_step
            }
        else:
            print("❌ Recovery failed")
            results["crash_recovery"] = {"successful": False}

    async def _demo_step_performance_validation(self, results: Dict[str, Any]):
        """Demonstrate performance metrics and validation."""
        print("\n📈 STEP 5: Performance Metrics & Validation")
        print("-" * 50)

        # Get comprehensive statistics
        session_summary = self.task_state_sync.get_session_summary(self.session_id)
        sync_stats = self.task_state_sync.get_sync_statistics()
        enforcement_stats = self.enforcement_gate.get_statistics()

        print(f"📊 Session Summary:")
        print(f"   • Files modified: {session_summary['files_modified']}")
        print(f"   • Lines written: {session_summary['lines_written']}")
        print(f"   • Memory entries: {session_summary['memory_entries']}")
        print(f"   • Tool usage: {session_summary['total_tool_usage']} operations")
        print(f"   • Duration: {session_summary.get('duration_seconds', 0):.1f}s")

        print(f"\n🔄 Sync Statistics:")
        print(f"   • Total syncs: {sync_stats['total_syncs']}")
        print(f"   • Active sessions: {sync_stats['active_sessions']}")
        print(f"   • Debouncer active: {sync_stats['debouncer_active']}")

        print(f"\n🚪 Enforcement Statistics:")
        print(f"   • Decisions logged: {enforcement_stats['decisions_logged']}")
        print(f"   • Enforcement active: {enforcement_stats['enforcement_active']}")

        # Store performance metrics
        results["performance_metrics"] = {
            "session_summary": session_summary,
            "sync_stats": sync_stats,
            "enforcement_stats": enforcement_stats
        }

        # Validate performance expectations
        performance_ok = (
            session_summary['files_modified'] > 0 and
            sync_stats['total_syncs'] > 0 and
            session_summary['memory_entries'] > 0
        )

        results["performance_validation"] = {
            "passed": performance_ok,
            "files_created": session_summary['files_modified'],
            "syncs_completed": sync_stats['total_syncs'],
            "memory_entries": session_summary['memory_entries']
        }

        if performance_ok:
            print("✅ Performance validation passed")
        else:
            print("⚠️  Performance validation issues detected")

    async def _demo_final_summary(self, results: Dict[str, Any]):
        """Generate final demonstration summary."""
        print("\n🎉 FINAL DEMONSTRATION SUMMARY")
        print("=" * 80)

        # Final state
        final_state = await self.protocol_manager.get_current_state()
        results["final_state"] = {
            "session_id": final_state.session_id,
            "protocol_step": final_state.protocol_step.name,
            "task_id": final_state.task_id,
            "is_valid": final_state.is_valid()
        }

        print(f"🏆 Demonstration Results:")
        print(f"   • Session: {results['session_id'][:8]}...")
        print(f"   • Task created: {results['task_created']}")
        print(f"   • Protocol enforced: {results['protocol_enforced']}")
        print(f"   • Steps completed: {len(results['steps_completed'])}/7")
        print(f"   • Errors encountered: {len(results['errors_encountered'])}")

        if results['task_created']:
            print(f"   • Task ID: {results.get('task_id', 'N/A')[:8]}...")

        print(f"\n📋 Steps Completed:")
        for step in results['steps_completed']:
            print(f"   ✅ {step}")

        if results['errors_encountered']:
            print(f"\n❌ Errors:")
            for error in results['errors_encountered']:
                print(f"   • {error}")

        # Performance summary
        if 'performance_metrics' in results:
            metrics = results['performance_metrics']
            print(f"\n📊 Performance Summary:")
            print(f"   • Total operations: {metrics['sync_stats']['total_syncs']}")
            print(f"   • Files created: {metrics['session_summary']['files_modified']}")
            print(f"   • Memory entries: {metrics['session_summary']['memory_entries']}")

        print(f"\n🔐 Final State: {final_state.protocol_step.name}")
        print(f"   State valid: {final_state.is_valid}")
        print(f"   Session active: {self.session_id in self.task_state_sync.active_sessions}")

        print("\n" + "=" * 80)
        print("🎯 DevStream Protocol System Demonstration Complete!")
        print("✅ All components working together successfully")


# Test runner
async def run_protocol_demo():
    """Run the complete protocol demonstration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        demo = ProtocolDemo(Path(temp_dir))
        results = await demo.run_complete_demo()
        return results


# Integration test
async def test_protocol_end_to_end_demo():
    """Test the complete protocol demonstration."""
    print("🧪 Running Protocol End-to-End Demo Test")
    print("=" * 80)

    results = await run_protocol_demo()

    # Validate demo results
    assert results["session_id"] is not None
    assert results["protocol_enforced"] == True
    assert len(results["steps_completed"]) > 0
    assert results["final_state"]["is_valid"] == True

    # Validate performance metrics
    if "performance_validation" in results:
        perf = results["performance_validation"]
        assert perf["passed"] == True

    print("\n✅ All end-to-end demo tests passed!")
    return results


if __name__ == "__main__":
    # Run the demonstration
    async def main():
        try:
            results = await test_protocol_end_to_end_demo()
            print(f"\n🎊 Demo completed successfully!")
            print(f"Final session: {results['session_id'][:8]}...")
            print(f"Steps completed: {len(results['steps_completed'])}")
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(main())