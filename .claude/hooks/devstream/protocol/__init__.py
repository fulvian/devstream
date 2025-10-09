"""
DevStream Protocol Components.

This package provides the core protocol enforcement components for DevStream:

- ProtocolStateManager: Atomic state persistence and session management
- EnforcementGate: Blocking enforcement gate with user interaction
- StepValidator: Step completion validation with memory search
- TaskFirstHandler: Mandatory STEP 1 enforcement for task creation
- TaskStateSync: Automatic state synchronization with hook integration
"""

__version__ = "1.0.0"
__author__ = "DevStream Team"