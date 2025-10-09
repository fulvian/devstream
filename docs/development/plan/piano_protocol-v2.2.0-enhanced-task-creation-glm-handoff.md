# Implementation Plan: DevStream Protocol v2.2.0 - Enhanced Task Creation & GLM Handoff Workflow

**Task ID**: `ce07a156e6a483d829df03d265b26c80`
**Phase**: Protocol Enhancement & Multi-Model Workflow
**Priority**: 9/10
**Model**: Claude Sonnet 4.5 (Reasoning-Enabled, Architectural)
**Estimated Duration**: 8 hours
**Created**: 2025-10-09

---

## 🎯 EXECUTIVE SUMMARY

This plan implements comprehensive DevStream protocol enhancements addressing three critical issues:

1. **Early Task Creation**: Move task creation from Step 5 (APPROVAL) to Step 1 (DISCUSSION) to prevent data loss and enable comprehensive tracking
2. **Implementation Plan Storage**: Dual storage system (database + markdown files) for detailed implementation plans with model-specific templates
3. **Strategic Choice Gate**: Cost-optimized workflow enabling Sonnet 4.5 (planning) → GLM-4.6 (execution) handoff with pre-generated prompts

**Research Foundation**: Context7 + web research on GLM-4.6 capabilities, Sonnet 4.5 strengths, and agentic coding best practices

---

## 📊 ARCHITECTURE OVERVIEW

```
DevStream Protocol v2.2.0 Workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
User Request
    ↓
Step 1: DISCUSSION + TASK CREATION (NEW - Early Creation)
    ↓ [Task DB record created with status='draft']
    ↓ [All subsequent steps linked to task_id]
    ↓
Step 2-3: ANALYSIS + RESEARCH (Context7)
    ↓ [Checkpoints saved to DevStream memory]
    ↓
Step 4: PLANNING + Strategic Choice Gate
    ↓
┌─────────────────────────────────────────────────────┐
│ MODEL SELECTION (User Choice)                       │
├─────────────────────────────────────────────────────┤
│ [1] GLM-4.6     │ [2] Sonnet 4.5                    │
│ Cost-Optimized  │ Quality-First                     │
│ Standard Tasks  │ Complex/Novel                     │
└─────────────────────────────────────────────────────┘
    ↓                              ↓
Generate Plan (model-specific template)
    ↓
┌─────────────────────────────────────────────────────┐
│ DUAL STORAGE                                        │
├─────────────────────────────────────────────────────┤
│ 1. DevStream DB: implementation_plans table         │
│    - task_id (FK to micro_tasks)                    │
│    - model_type, plan_content, metadata             │
│                                                      │
│ 2. File System: docs/development/plan/              │
│    - piano_[task-slug].md                           │
│    - Markdown formatted, human-readable             │
└─────────────────────────────────────────────────────┘
    ↓
[IF GLM-4.6 SELECTED]
    ↓
┌─────────────────────────────────────────────────────┐
│ HANDOFF PROMPT GENERATION                           │
├─────────────────────────────────────────────────────┤
│ Template: Agentic Coding Optimized                  │
│ - Task context from DevStream                       │
│ - Link to plan .md file                             │
│ - CLAUDE.md protocol references                     │
│ - Tool definitions + examples                       │
│ - Constraint emphasis (CAPITALIZATION)              │
│ - Few-shot examples for complex patterns            │
└─────────────────────────────────────────────────────┘
    ↓
Step 5: APPROVAL (User confirms plan)
    ↓ [Task status: draft → active]
    ↓
[USER MANUALLY SWITCHES MODEL IF NEEDED]
    ↓
Step 6-7: IMPLEMENTATION + VERIFICATION
```

---

## 🔬 RESEARCH FINDINGS SUMMARY

### GLM-4.6 Profile
**Strengths**:
- ✅ Tool calling accuracy: 90.6% (best-in-class, outperforms Claude Sonnet 4)
- ✅ Token efficiency: 15% fewer tokens than GLM-4.5
- ✅ Cost-effective: ~30% cost of Claude Sonnet for coding tasks
- ✅ Integration: Seamless with Claude Code, Cline, Roo Code

**Limitations**:
- ⚠️ Syntax errors: 13% across languages (vs 5.5% in GLM-4.5)
- ⚠️ Early quit: Complex reasoning tasks may terminate prematurely
- ⚠️ Framework knowledge gaps: Struggles with framework-specific patterns (e.g., Tailwind CSS)
- ⚠️ Thinking mode cost: 18K reasoning tokens, 5+ minutes for medium tasks

**Optimal Use Cases**:
- Standard coding tasks with clear specifications
- Micro-tasks 10-15 minutes duration
- Well-documented patterns and libraries
- Tool-heavy workflows (API calls, database operations)

### Claude Sonnet 4.5 Profile
**Strengths**:
- ✅ SWE-bench Verified: 77.2 (state-of-the-art, vs 68.0 for GLM-4.6)
- ✅ Sustained focus: 30+ hours on complex multi-step tasks
- ✅ Native subagent orchestration: Proactive delegation without explicit instruction
- ✅ Output capacity: 64K tokens (rich code generation + documentation)
- ✅ Agentic search: Exceptional Context7 research autonomy

**Optimal Use Cases**:
- Complex architectural decisions
- Novel pattern exploration
- Long-running multi-component tasks
- Research-heavy implementations
- Security-critical code

### Agentic Coding Best Practices
**Core Patterns** (from research):
1. **Role Definition**: System prompt "You are an expert X"
2. **Step-by-Step Execution**: Explicit sequence, no ambiguity
3. **Format Specification**: JSON/structured output mandatory
4. **Tool Clarity**: Clear definitions + usage examples
5. **Constraint Emphasis**: CAPITALIZATION for critical rules
6. **Few-Shot Examples**: For complex patterns
7. **CLAUDE.md Context**: Automatic pull, avoid repetition

**Memory & Context** (from research):
- LLMs are stateless → Memory system critical
- Tools require as much configuration as prompts
- Planning capabilities → Think ahead (TodoWrite)

---

## 📋 DATABASE SCHEMA

### New Table: `implementation_plans`

```sql
CREATE TABLE IF NOT EXISTS implementation_plans (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE,  -- 1:1 relationship with micro_tasks
    model_type TEXT NOT NULL CHECK(model_type IN ('glm-4.6', 'sonnet-4.5')),
    plan_content TEXT NOT NULL,     -- Full markdown plan
    plan_file_path TEXT,            -- docs/development/plan/piano_*.md
    handoff_prompt TEXT,            -- Pre-generated GLM handoff prompt (if applicable)
    metadata JSON,                  -- {complexity, estimated_duration, context7_libs, etc}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES micro_tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_implementation_plans_task_id ON implementation_plans(task_id);
CREATE INDEX idx_implementation_plans_model_type ON implementation_plans(model_type);
CREATE INDEX idx_implementation_plans_created_at ON implementation_plans(created_at DESC);
```

**Design Rationale**:
- **1:1 relationship**: UNIQUE constraint on `task_id` ensures one plan per task
- **model_type**: Enables template selection and analytics
- **plan_file_path**: Links DB record to markdown file for human readability
- **handoff_prompt**: Pre-generated for GLM workflow (avoids regeneration)
- **metadata JSON**: Flexible schema for future enhancements
- **CASCADE delete**: Data integrity when tasks deleted

---

## 🗂️ FILE STRUCTURE

### New Files Created (7 files)

```
devstream/
├── mcp-devstream-server/src/
│   ├── tools/
│   │   └── implementation-plans.ts          # NEW - MCP tools for plan CRUD
│   └── database.ts                          # MODIFIED - Add ImplementationPlan interface
├── .claude/hooks/devstream/
│   ├── protocol/
│   │   └── protocol_enforcer.py             # NEW - Step 1 task creation enforcement
│   └── planning/
│       └── implementation_plan_generator.py # NEW - Step 4 plan generation automation
├── templates/
│   ├── implementation-plan-glm46.md         # NEW - GLM-4.6 template (research-backed)
│   ├── implementation-plan-sonnet45.md      # NEW - Sonnet 4.5 template (research-backed)
│   └── handoff-prompt-glm46.md              # NEW - GLM handoff prompt template
├── docs/
│   ├── architecture/
│   │   └── implementation-plans-system.md   # NEW - System documentation
│   └── development/plan/
│       └── piano_protocol-v2.2.0-*.md       # THIS FILE
├── migrations/
│   └── 003_create_implementation_plans.sql  # NEW - Database migration
└── CLAUDE.md                                # MODIFIED - Protocol v2.2.0 documentation
```

---

## 🛠️ IMPLEMENTATION MICRO-TASKS (14 Tasks)

### Task 1: Database Schema Migration (30 min)
**File**: `migrations/003_create_implementation_plans.sql`
**Action**: CREATE TABLE with indexes

**Acceptance Criteria**:
- [ ] Migration script created
- [ ] Table schema matches specification
- [ ] Indexes created for performance
- [ ] Foreign key constraints working
- [ ] Migration tested on local DB

**Test Command**:
```bash
sqlite3 data/devstream.db < migrations/003_create_implementation_plans.sql
sqlite3 data/devstream.db "PRAGMA table_info(implementation_plans);"
```

---

### Task 2: Database Interface Update (15 min)
**File**: `mcp-devstream-server/src/database.ts`
**Action**: Add `ImplementationPlan` TypeScript interface

**Interface Specification**:
```typescript
export interface ImplementationPlan {
  id: string;
  task_id: string;
  model_type: 'glm-4.6' | 'sonnet-4.5';
  plan_content: string;
  plan_file_path: string | null;
  handoff_prompt: string | null;
  metadata: string; // JSON string
  created_at: string;
  updated_at: string;
}
```

**Acceptance Criteria**:
- [ ] Interface matches DB schema
- [ ] Type safety enforced
- [ ] Exported from database.ts
- [ ] No TypeScript errors

---

### Task 3: MCP Implementation Plans Tool (1.5 hours)
**File**: `mcp-devstream-server/src/tools/implementation-plans.ts`
**Action**: Create CRUD operations for implementation plans

**Methods Required**:
1. `createImplementationPlan(args)` - Create plan + file
2. `getImplementationPlan(task_id)` - Retrieve by task_id
3. `updateImplementationPlan(args)` - Update existing plan
4. `listImplementationPlans(filters)` - List with optional filters

**Input Schemas** (Zod validation):
```typescript
const CreatePlanInputSchema = z.object({
  task_id: z.string().min(1),
  model_type: z.enum(['glm-4.6', 'sonnet-4.5']),
  plan_content: z.string().min(1),
  plan_file_path: z.string().optional(),
  handoff_prompt: z.string().optional(),
  metadata: z.object({
    complexity: z.number().optional(),
    estimated_duration: z.number().optional(),
    context7_libraries: z.array(z.string()).optional()
  }).optional()
});
```

**Acceptance Criteria**:
- [ ] All CRUD operations implemented
- [ ] Zod validation on inputs
- [ ] Error handling comprehensive
- [ ] Returns formatted MCP responses
- [ ] Tests written (unit tests)

**Test File**: `tests/unit/test_implementation_plans_tool.py`

---

### Task 4: Register MCP Tool (10 min)
**File**: `mcp-devstream-server/src/index.ts`
**Action**: Register implementation-plans tool in MCP server

**Code Change**:
```typescript
import { ImplementationPlanTools } from './tools/implementation-plans.js';

// In server initialization
const implementationPlanTools = new ImplementationPlanTools(database);

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  // ... existing tools ...
  case 'devstream_create_implementation_plan':
    return await implementationPlanTools.createPlan(request.params.arguments);
  case 'devstream_get_implementation_plan':
    return await implementationPlanTools.getPlan(request.params.arguments);
  // ... etc
});
```

**Acceptance Criteria**:
- [ ] Tool registered correctly
- [ ] MCP server starts without errors
- [ ] Tool callable via MCP protocol
- [ ] Test with manual MCP call

---

### Task 5: GLM-4.6 Template (45 min)
**File**: `templates/implementation-plan-glm46.md`
**Action**: Create research-backed template for GLM-4.6 execution

**Template Sections** (see full template in research section above):
1. Execution Profile (strengths, constraints)
2. Micro-Task Breakdown (detailed specs)
3. Tool Usage Examples (Context7, DevStream memory)
4. Context7 Findings (pre-researched)
5. Critical Constraints (capitalized)
6. Quality Gates (mandatory checks)
7. Commit Message Template

**Acceptance Criteria**:
- [ ] All sections present
- [ ] Research findings integrated
- [ ] GLM-specific optimizations applied
- [ ] Template variables documented
- [ ] Example usage documented

---

### Task 6: Sonnet 4.5 Template (45 min)
**File**: `templates/implementation-plan-sonnet45.md`
**Action**: Create research-backed template for Sonnet 4.5 reasoning

**Key Differences from GLM Template**:
- Component-level (not micro-task level)
- Architectural guidance (not prescriptive)
- ADR (Architectural Decision Records) section
- Subagent delegation guidance
- Autonomy emphasis (research, refactor)

**Acceptance Criteria**:
- [ ] All sections present
- [ ] Sonnet-specific strengths leveraged
- [ ] ADR template included
- [ ] Subagent delegation patterns documented
- [ ] Template variables documented

---

### Task 7: GLM Handoff Prompt Template (45 min)
**File**: `templates/handoff-prompt-glm46.md`
**Action**: Create agentic coding optimized handoff prompt

**Sections** (see full template above):
1. Task Context (FROM/TO, status)
2. Work Completed (Steps 1-5 summary)
3. Implementation Plan Reference
4. Mission (Steps 6-7)
5. DevStream Protocol Compliance
6. Context7 Research Findings
7. Technical Specifications
8. Critical Constraints
9. Quality Gates
10. Execution Checklist

**Acceptance Criteria**:
- [ ] Complete handoff context
- [ ] Protocol compliance emphasized
- [ ] Tool usage examples included
- [ ] Checklist actionable
- [ ] Template variables documented

---

### Task 8: Protocol Enforcer Hook (1 hour)
**File**: `.claude/hooks/devstream/protocol/protocol_enforcer.py`
**Action**: Enforce task creation at Step 1 (DISCUSSION)

**Logic**:
```python
async def enforce_task_creation(user_prompt: str) -> Dict[str, Any]:
    """
    Analyze user request complexity.
    If meets criteria (>15 min, code required, etc), enforce task creation.
    """
    complexity = await analyze_complexity(user_prompt)

    if complexity >= 0.7:  # Threshold for task requirement
        # Check if task already exists
        if not await has_active_task():
            # Force task creation with user confirmation
            return await prompt_task_creation(user_prompt)

    return {"proceed": True}
```

**Acceptance Criteria**:
- [ ] Complexity analysis implemented
- [ ] User confirmation prompt working
- [ ] Task creation via MCP tool
- [ ] Hook registered in settings.json
- [ ] Tests written (unit + integration)

**Test File**: `tests/unit/test_protocol_enforcer.py`

---

### Task 9: Implementation Plan Generator Hook (1.5 hours)
**File**: `.claude/hooks/devstream/planning/implementation_plan_generator.py`
**Action**: Automate Step 4 plan generation with Strategic Choice Gate

**Workflow**:
1. Detect Step 4 (PLANNING) completion
2. Prompt user: "Choose model: [1] GLM-4.6  [2] Sonnet 4.5"
3. Load appropriate template
4. Generate plan with variable substitution
5. Save to DB (via MCP tool)
6. Save to filesystem (docs/development/plan/)
7. If GLM selected: Generate handoff prompt
8. Return confirmation to user

**Acceptance Criteria**:
- [ ] Strategic Choice Gate implemented
- [ ] Template selection logic correct
- [ ] Variable substitution working
- [ ] Dual storage (DB + file) implemented
- [ ] Handoff prompt generation working
- [ ] Tests written

**Test File**: `tests/integration/test_plan_generator.py`

---

### Task 10: Enhanced UserPromptSubmit Hook (30 min)
**File**: `.claude/hooks/devstream/context/user_query_context_enhancer.py`
**Action**: Integrate protocol_enforcer call

**Code Change**:
```python
from ..protocol.protocol_enforcer import enforce_task_creation

async def enhance_context(user_prompt: str) -> Dict[str, Any]:
    # Existing context enhancement logic
    # ...

    # NEW: Protocol enforcement
    enforcement_result = await enforce_task_creation(user_prompt)
    if not enforcement_result["proceed"]:
        # User rejected task creation or needs confirmation
        return {"blocked": True, "reason": enforcement_result["reason"]}

    # Continue with normal enhancement
    return enhanced_context
```

**Acceptance Criteria**:
- [ ] Protocol enforcer integrated
- [ ] No breaking changes to existing logic
- [ ] Error handling comprehensive
- [ ] Tests updated

---

### Task 11: Update CLAUDE.md Protocol v2.2.0 (30 min)
**File**: `CLAUDE.md`
**Action**: Document new protocol flow with Strategic Choice Gate

**Sections to Update**:
1. Version (2.1.0 → 2.2.0)
2. Step 1 DISCUSSION: Add "Task Creation MANDATORY" note
3. Step 4 PLANNING: Add Strategic Choice Gate documentation
4. Implementation Plans section (new)
5. Appendix: Add implementation_plans table schema

**Example Addition**:
```markdown
#### Step 4: PLANNING (MANDATORY - TodoWrite + Strategic Choice Gate)
- ✅ Create TodoWrite list for non-trivial tasks
- ✅ **NEW**: Choose implementation model via Strategic Choice Gate
  - [1] GLM-4.6: Cost-optimized (30% Sonnet cost), standard tasks
  - [2] Sonnet 4.5: Quality-first, complex/novel patterns
- ✅ Generate model-specific implementation plan
- ✅ Save plan to DevStream DB + docs/development/plan/
- ✅ (If GLM) Generate handoff prompt for session switch
```

**Acceptance Criteria**:
- [ ] All protocol steps updated
- [ ] Strategic Choice Gate documented
- [ ] Implementation plans section added
- [ ] Version bumped to 2.2.0
- [ ] No formatting errors

---

### Task 12: Architecture Documentation (30 min)
**File**: `docs/architecture/implementation-plans-system.md`
**Action**: Comprehensive system documentation

**Sections**:
1. Overview & Motivation
2. Architecture Diagram (ASCII art)
3. Database Schema
4. MCP Tool API Reference
5. Template Specifications
6. Hook Integration Points
7. Workflow Examples (Sonnet → GLM handoff)
8. Troubleshooting Guide

**Acceptance Criteria**:
- [ ] Complete documentation
- [ ] Diagrams clear
- [ ] API reference accurate
- [ ] Examples tested
- [ ] Troubleshooting comprehensive

---

### Task 13: E2E Test Workflow (1 hour)
**File**: `tests/integration/test_glm_handoff_workflow.py`
**Action**: End-to-end test simulating Sonnet → GLM workflow

**Test Scenarios**:
1. Task creation at Step 1
2. Strategic Choice Gate selection (GLM)
3. Plan generation (GLM template)
4. Dual storage validation (DB + file)
5. Handoff prompt generation
6. Plan retrieval by task_id

**Acceptance Criteria**:
- [ ] All scenarios covered
- [ ] Tests pass 100%
- [ ] Fixtures for test data
- [ ] Cleanup after tests
- [ ] Documentation for running tests

---

### Task 14: Complete Workflow Validation (30 min)
**Action**: Manual validation of end-to-end workflow

**Validation Steps**:
1. Create test task via protocol enforcer
2. Complete Steps 1-3
3. Trigger Step 4 with Strategic Choice Gate
4. Select GLM-4.6
5. Verify plan generation (both DB and file)
6. Verify handoff prompt generation
7. Retrieve plan via MCP tool
8. Simulate GLM session with handoff prompt
9. Verify task completion tracking

**Acceptance Criteria**:
- [ ] All steps work end-to-end
- [ ] No errors in hooks
- [ ] Data persisted correctly
- [ ] Handoff prompt usable
- [ ] Documentation matches implementation

---

## ✅ QUALITY GATES

### Testing Requirements
- **Unit Tests**: 95%+ coverage for new code
  - `test_implementation_plans_tool.py`
  - `test_protocol_enforcer.py`
- **Integration Tests**: E2E workflow coverage
  - `test_plan_generator.py`
  - `test_glm_handoff_workflow.py`
- **Manual Testing**: Complete workflow validation

### Type Safety
```bash
cd mcp-devstream-server
npm run typecheck  # Zero TypeScript errors
```

### Database Integrity
```bash
sqlite3 data/devstream.db "PRAGMA foreign_key_check;"
sqlite3 data/devstream.db "PRAGMA integrity_check;"
```

### Performance Validation
- Plan generation: <2 seconds
- MCP tool calls: <500ms
- Hook execution: <1 second

---

## 📊 SUCCESS METRICS

**Implementation**:
- [ ] 14/14 micro-tasks completed
- [ ] All tests passing (unit + integration)
- [ ] Type safety: Zero errors
- [ ] Database migration successful
- [ ] MCP tools registered and callable

**Functionality**:
- [ ] Task creation at Step 1 working
- [ ] Strategic Choice Gate functional
- [ ] Plans saved to DB + filesystem
- [ ] Handoff prompts generated correctly
- [ ] Protocol v2.2.0 documented

**Quality**:
- [ ] Test coverage ≥ 95%
- [ ] No TypeScript errors
- [ ] No Python type errors (mypy)
- [ ] No database integrity issues
- [ ] Performance targets met

---

## 🚀 DEPLOYMENT STRATEGY

### Phase 1: Database & Core (Tasks 1-4)
- Database schema migration
- TypeScript interfaces
- MCP tools implementation
- Tool registration

### Phase 2: Templates (Tasks 5-7)
- GLM-4.6 template
- Sonnet 4.5 template
- Handoff prompt template

### Phase 3: Hooks & Integration (Tasks 8-10)
- Protocol enforcer hook
- Plan generator hook
- UserPromptSubmit enhancement

### Phase 4: Documentation & Testing (Tasks 11-14)
- CLAUDE.md update
- Architecture documentation
- E2E tests
- Complete workflow validation

---

## 🎯 NEXT STEPS

1. **APPROVED** ✅ - Plan reviewed and accepted
2. **BEGIN** Task 1: Database schema migration
3. **PROCEED** sequentially through micro-tasks
4. **VALIDATE** after each phase
5. **COMPLETE** with full workflow validation

---

**Prepared by**: Claude Sonnet 4.5
**Research**: Context7 + Web (GLM-4.6, Sonnet 4.5, agentic best practices)
**Implementation Timeline**: 8 hours (14 micro-tasks)
**Priority**: Critical (9/10)
**Status**: APPROVED - Ready for Implementation

---

*This plan incorporates research findings from official documentation, performance benchmarks, and agentic coding best practices to create model-optimized templates and cost-efficient workflows.*
