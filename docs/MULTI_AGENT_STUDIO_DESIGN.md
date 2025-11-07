# Multi-Agent Game Studio - Design Specification

**Version:** 1.0
**Date:** 2025-11-07
**Status:** DESIGN PHASE

---

## Overview

This document specifies the architecture for a collaborative AI game studio with 12 specialized agents organized into 6 departments, working together to create Game Boy Color games.

---

## Agent Organization

### Department Structure

Each department has **2 agents** that work collaboratively:
- **Agent A**: Primary executor (proposes solutions)
- **Agent B**: Critic/reviewer (challenges and improves)

Both agents have access to the same tools but play different roles in the workflow.

---

## Departments & Responsibilities

### 🎨 **Art Department**

**Members:**
- **Artist A (Generator)**: Creates sprites, tiles, backgrounds
- **Artist B (Critic)**: Reviews art quality, color theory, Game Boy constraints

**Tools:**
- ComfyUI API (image generation)
- Aseprite MCP (sprite editing)
- PixelDetector (validation)
- Pillow (image manipulation)

**Workflow:**
1. Artist A receives request: "Create knight sprite"
2. Artist A generates with ComfyUI → Shows to Artist B
3. Artist B critiques: "Colors too bright, reduce contrast"
4. Artist A refines in Aseprite → Shows again
5. Artist B approves or requests more changes
6. Final sprite exported to project

**Conversation Example:**
```
[Artist A - Internal Thought]: Need to create a knight sprite, 16x16, Game Boy palette
[Artist A → Artist B]: I'm thinking silver armor with red cape, what do you think?
[Artist B - Internal Thought]: Red might be too vibrant for GB palette
[Artist B → Artist A]: Consider darker red (#8B0000), check palette constraints
[Artist A]: Good catch! Adjusting...
[Artist A]: Done! knight_v2.aseprite ready for review
[Artist B]: Excellent! Colors are perfect now. Approved ✓
```

---

### 📐 **Design Department**

**Members:**
- **Designer A (Systems)**: Game mechanics, level design, progression
- **Designer B (Balance)**: Difficulty tuning, pacing, player experience

**Tools:**
- GBStudio API (project manipulation)
- JSON editor (game data)
- Spreadsheet tools (balance calculations)
- Level validator

**Workflow:**
1. Designer A proposes game mechanic: "Player collects gems for score"
2. Designer B analyzes balance: "Gem value should scale with difficulty"
3. They iterate on design document
4. Designer A implements in GBStudio
5. Designer B validates implementation
6. Design approved for playtesting

**Conversation Example:**
```
[Designer A - Internal Thought]: Boss fight needs to be challenging but fair
[Designer A → Designer B]: Boss HP: 50, Attack: 10, Speed: 2. Thoughts?
[Designer B - Internal Thought]: HP seems high for a Game Boy game
[Designer B → Designer A]: Consider HP: 30. Players have limited healing
[Designer A]: Makes sense. Also reducing attack to 8 for first boss
[Designer B]: Perfect! That creates good difficulty curve ✓
```

---

### 💻 **Code Department**

**Members:**
- **Coder A (Logic)**: Implements features, writes scripts
- **Coder B (Review)**: Code review, refactoring, best practices

**Tools:**
- Python interpreter
- Git (version control)
- Linters (ruff, black, mypy)
- Debugger
- Test runner (pytest)

**Workflow:**
1. Coder A writes feature implementation
2. Coder A runs tests → Some fail
3. Coder B reviews code: "Use async here for performance"
4. Coder A refactors based on feedback
5. Coder B approves: "Looks good, tests pass ✓"
6. Code merged to main branch

**Conversation Example:**
```
[Coder A - Internal Thought]: Need to implement inventory system
[Coder A → Coder B]: Here's my approach: dict to store items
[Coder A → Coder B]: *shares code snippet*
[Coder B - Internal Thought]: Should use dataclass for type safety
[Coder B → Coder A]: Consider using Pydantic models for validation
[Coder A]: Great idea! Refactoring now...
[Coder A]: Done! Also added type hints
[Coder B]: Perfect! All tests pass. Merge approved ✓
```

---

### 🧪 **QA Department**

**Members:**
- **Tester A (Manual)**: Exploratory testing, UX review
- **Tester B (Auto)**: Automated tests, regression testing

**Tools:**
- Pytest (test framework)
- Coverage.py (code coverage)
- Bug tracker (issues.json)
- Screen recorder
- Game emulator

**Workflow:**
1. Tester A plays the game manually
2. Tester A finds bug: "Player can walk through walls"
3. Tester B writes automated test to reproduce
4. Both document bug with reproduction steps
5. Tester A verifies fix after Code department resolves
6. Tester B confirms regression test passes

**Conversation Example:**
```
[Tester A - Internal Thought]: Testing new level, checking for edge cases
[Tester A → Tester B]: Found issue: collision detection fails at screen edge
[Tester B - Internal Thought]: Need to write test case for this
[Tester B → Tester A]: Can you reproduce consistently?
[Tester A]: Yes - walk to X=255, Y=0, press right
[Tester B]: Perfect! Writing automated test now...
[Tester B]: Test written: test_screen_edge_collision() - FAILING ✓
[Tester A]: Good! Sending bug report to Code department
```

---

### 🎮 **Playtest Department**

**Members:**
- **Player A (Feel)**: Subjective feedback, fun factor, emotions
- **Player B (Metrics)**: Objective data, completion rates, analytics

**Tools:**
- Game runner (emulator)
- Analytics tracker (time, deaths, progress)
- Feedback form
- Video recording
- Heat maps (player movement)

**Workflow:**
1. Player A plays through level
2. Player A reports: "This jump feels unfair"
3. Player B analyzes data: "85% death rate at this point"
4. Both write feedback report for Design department
5. Design makes adjustments
6. Player A confirms: "Much better now!"
7. Player B validates: "Death rate down to 35%"

**Conversation Example:**
```
[Player A - Internal Thought]: Level 3 is frustrating, not fun
[Player A → Player B]: This section feels cheap, dying a lot
[Player B - Internal Thought]: Let me check the death analytics
[Player B → Player A]: Data shows 92% death rate in 30 seconds
[Player A]: Yeah, enemy placement is unfair. Can't react in time
[Player B]: Sending feedback to Design: "Reduce enemy count or add warning"
[Player A]: Also suggest moving health pickup earlier
[Player B]: Good call! Report sent with both suggestions ✓
```

---

### 📦 **Publishing Department**

**Members:**
- **Publisher A (Build)**: Packaging, ROM creation, asset bundling
- **Publisher B (Deploy)**: Distribution, deployment, release management

**Tools:**
- Docker (containerization)
- GBStudio compiler (ROM builder)
- Asset optimizer
- Release automation
- Distribution API (itch.io, etc.)

**Workflow:**
1. Publisher A builds ROM from GBStudio project
2. Publisher A validates: file size, compatibility
3. Publisher B reviews build: "Add version metadata"
4. Publisher A rebuilds with metadata
5. Publisher B tests on multiple emulators
6. Both approve release candidate
7. Publisher B deploys to distribution

**Conversation Example:**
```
[Publisher A - Internal Thought]: Ready to build v1.0 ROM
[Publisher A → Publisher B]: Building ROM... Size: 512KB
[Publisher B - Internal Thought]: Check if we're under 1MB limit
[Publisher B → Publisher A]: Good size. Did you optimize sprites?
[Publisher A]: Yes, compressed with PixelDetector. Testing ROM now...
[Publisher A]: ROM boots successfully on BGB emulator ✓
[Publisher B]: Let me test on Gambatte and mGBA too
[Publisher B]: All emulators pass! Ready for release ✓
```

---

## Conversation System

### Message Types

**1. Internal Thought**
```python
{
  "type": "internal_thought",
  "agent": "Artist A",
  "department": "Art",
  "content": "Need to check Game Boy palette constraints",
  "timestamp": "2025-11-07T10:30:00Z",
  "visible_to": ["Artist A", "PM Agent", "User"]
}
```

**2. Peer Communication**
```python
{
  "type": "peer_message",
  "from": "Artist A",
  "to": "Artist B",
  "department": "Art",
  "content": "What do you think of this color palette?",
  "attachments": ["sprite_v1.png"],
  "timestamp": "2025-11-07T10:31:00Z",
  "visible_to": ["Artist A", "Artist B", "PM Agent", "User"]
}
```

**3. Critique**
```python
{
  "type": "critique",
  "from": "Artist B",
  "to": "Artist A",
  "department": "Art",
  "content": "Colors are good but contrast is too high",
  "severity": "minor",
  "suggestions": ["Reduce brightness by 10%", "Use palette index 2 instead of 3"],
  "timestamp": "2025-11-07T10:32:00Z",
  "visible_to": ["Artist A", "Artist B", "PM Agent", "User"]
}
```

**4. Tool Usage**
```python
{
  "type": "tool_usage",
  "agent": "Artist A",
  "tool": "aseprite_mcp.create_sprite",
  "params": {"width": 16, "height": 16},
  "result": {"success": true, "path": "sprite.aseprite"},
  "timestamp": "2025-11-07T10:33:00Z",
  "visible_to": ["Artist A", "Artist B", "PM Agent", "User"]
}
```

**5. Approval/Rejection**
```python
{
  "type": "approval",
  "from": "Artist B",
  "to": "Artist A",
  "department": "Art",
  "status": "approved",
  "content": "Sprite looks great! Ready for Code integration",
  "timestamp": "2025-11-07T10:35:00Z",
  "visible_to": ["all_departments", "PM Agent", "User"]
}
```

**6. PM Agent Feedback**
```python
{
  "type": "pm_feedback",
  "from": "PM Agent",
  "to_department": "Art",
  "content": "Great work! Consider adding one more animation frame",
  "priority": "low",
  "timestamp": "2025-11-07T10:36:00Z",
  "visible_to": ["Art", "PM Agent", "User"]
}
```

**7. User Feedback**
```python
{
  "type": "user_feedback",
  "from": "User",
  "to_department": "Art",
  "to_agent": "Artist A",  # optional
  "content": "Love the sprite! Can you make the cape darker?",
  "timestamp": "2025-11-07T10:40:00Z",
  "visible_to": ["all"]
}
```

---

## Workflow Orchestration

### PM Agent Coordination

**1. Task Breakdown**
```
User Request: "Create a boss fight scene"
    ↓
PM Agent analyzes and creates plan:
    ├─ Art: Design boss sprite (16x16, animated)
    ├─ Design: Create boss battle mechanics
    ├─ Code: Implement boss AI logic
    ├─ QA: Test boss battle for bugs
    ├─ Playtest: Validate difficulty and fun
    └─ Publishing: Package new version
```

**2. Department Assignment**
```python
# PM Agent sends tasks
{
  "task_id": "boss_fight_001",
  "departments": [
    {
      "name": "Art",
      "agents": ["Artist A", "Artist B"],
      "task": "Create boss sprite with 3 animation frames",
      "dependencies": [],
      "priority": 1
    },
    {
      "name": "Design",
      "agents": ["Designer A", "Designer B"],
      "task": "Define boss attack patterns and HP",
      "dependencies": ["Art"],
      "priority": 2
    },
    # ... etc
  ]
}
```

**3. Progress Monitoring**
```python
# PM Agent tracks completion
{
  "task_id": "boss_fight_001",
  "status": {
    "Art": {"progress": 100, "status": "approved"},
    "Design": {"progress": 80, "status": "in_review"},
    "Code": {"progress": 0, "status": "pending"},
    # ...
  },
  "blockers": [
    "Design waiting for Artist B approval"
  ]
}
```

---

## User Interface Design

### Real-Time Conversation View

```
┌─────────────────────────────────────────────────────────────┐
│  MULTI-AGENT GAME STUDIO - Task: "Create boss fight"       │
├─────────────────────────────────────────────────────────────┤
│  Departments: [Art] [Design] [Code] [QA] [Playtest] [Pub]  │
│  Show: [All] [Internal Thoughts] [Critiques] [Approvals]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🎨 ART DEPARTMENT (Artist A ↔ Artist B)                    │
│  ┌─────────────────────────────────────────────────────────┤
│  │ 10:30 [Artist A 💭] Need to create boss sprite, 16x16   │
│  │ 10:31 [Artist A → Artist B] Starting boss design, ideas?│
│  │ 10:32 [Artist B 💭] Should check existing enemy sprites │
│  │ 10:32 [Artist B → Artist A] Make it distinct from normal│
│  │       enemies. Suggest: horns, larger weapon           │
│  │ 10:33 [Artist A 🔧] Using tool: comfyui.generate()      │
│  │       Prompt: "boss enemy, horns, sword, 16x16 pixel"  │
│  │ 10:35 [Artist A → Artist B] 📎 boss_v1.png - thoughts?  │
│  │ 10:36 [Artist B 🔍 CRITIQUE] Colors look good but...    │
│  │       - Needs more contrast on weapon                   │
│  │       - Horns blend with background                     │
│  │       Severity: Minor                                   │
│  │ 10:37 [Artist A] Adjusting in Aseprite...               │
│  │ 10:39 [Artist A 🔧] Using tool: aseprite.apply_palette()│
│  │ 10:40 [Artist A → Artist B] 📎 boss_v2.png - better?    │
│  │ 10:41 [Artist B ✓ APPROVED] Perfect! Ready for Design   │
│  └─────────────────────────────────────────────────────────┘
│                                                             │
│  📐 DESIGN DEPARTMENT (Designer A ↔ Designer B)             │
│  ┌─────────────────────────────────────────────────────────┤
│  │ 10:42 [Designer A 💭] Received boss sprite from Art     │
│  │ 10:42 [Designer A → Designer B] Boss HP? Attack damage? │
│  │ 10:43 [Designer B 💭] Level 5 boss, should be tough     │
│  │ 10:43 [Designer B → Designer A] Suggest: HP=50, ATK=12  │
│  │ 10:44 [Designer A] Too hard? Player only has HP=20      │
│  │ 10:45 [Designer B 💭] Good point, recalculating...      │
│  │ 10:45 [Designer B → Designer A] You're right! HP=35,    │
│  │       ATK=8, but faster movement to compensate          │
│  │ 10:46 [Designer A ✓] Perfect balance! Documenting...    │
│  └─────────────────────────────────────────────────────────┘
│                                                             │
│  💬 PM AGENT FEEDBACK                                       │
│  ┌─────────────────────────────────────────────────────────┤
│  │ 10:50 [PM → Art] Excellent sprite! Consider adding      │
│  │       hit flash animation for damage feedback           │
│  │ 10:51 [PM → Design] Boss stats look balanced. Queue for │
│  │       Code department implementation                    │
│  └─────────────────────────────────────────────────────────┘
│                                                             │
│  📝 YOUR NOTES                                              │
│  ┌─────────────────────────────────────────────────────────┤
│  │ [Type feedback to any department or agent...]           │
│  │ To: [Art ▼] Message: ____________________________       │
│  │ [SEND]                                                  │
│  └─────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### Agent Class Structure

```python
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

class AgentRole(Enum):
    EXECUTOR = "executor"    # Agent A - proposes solutions
    CRITIC = "critic"        # Agent B - reviews and improves

@dataclass
class Message:
    type: str  # internal_thought, peer_message, critique, etc.
    from_agent: str
    to_agent: str = None
    department: str
    content: str
    attachments: List[str] = None
    timestamp: str
    visible_to: List[str]
    metadata: Dict[str, Any] = None

class DepartmentAgent:
    def __init__(
        self,
        name: str,
        department: str,
        role: AgentRole,
        tools: List[str],
        llm_model: str = "claude-sonnet-4"
    ):
        self.name = name
        self.department = department
        self.role = role
        self.tools = tools
        self.llm = llm_model
        self.conversation_history = []
        self.partner = None  # Linked to other agent in department

    async def think(self, context: str) -> str:
        """Internal reasoning (visible to user/PM)"""
        thought = await self.llm.generate(
            f"As {self.name} ({self.role}), analyze: {context}"
        )
        self.log_message(Message(
            type="internal_thought",
            from_agent=self.name,
            department=self.department,
            content=thought,
            timestamp=now(),
            visible_to=[self.name, "PM Agent", "User"]
        ))
        return thought

    async def communicate(self, to_agent: str, message: str):
        """Send message to partner agent"""
        self.log_message(Message(
            type="peer_message",
            from_agent=self.name,
            to_agent=to_agent,
            department=self.department,
            content=message,
            timestamp=now(),
            visible_to=[self.name, to_agent, "PM Agent", "User"]
        ))

    async def critique(self, artifact: Any) -> Dict:
        """Provide critique on work (only for CRITIC role)"""
        if self.role != AgentRole.CRITIC:
            raise ValueError("Only critic agents can provide critiques")

        critique = await self.llm.generate(
            f"Review this artifact and provide constructive feedback:\n{artifact}"
        )

        return {
            "approved": critique.get("approved", False),
            "feedback": critique.get("feedback", ""),
            "suggestions": critique.get("suggestions", []),
            "severity": critique.get("severity", "none")
        }
```

### Department Workflow Engine

```python
class Department:
    def __init__(
        self,
        name: str,
        agent_a: DepartmentAgent,
        agent_b: DepartmentAgent
    ):
        self.name = name
        self.agent_a = agent_a  # Executor
        self.agent_b = agent_b  # Critic
        agent_a.partner = agent_b
        agent_b.partner = agent_a

    async def execute_task(self, task: Dict) -> Dict:
        """
        Collaborative workflow between two agents
        """
        # Step 1: Agent A thinks and proposes solution
        await self.agent_a.think(task['description'])
        proposal = await self.agent_a.work(task)

        # Step 2: Agent A shows to Agent B
        await self.agent_a.communicate(
            self.agent_b.name,
            f"Here's my proposal: {proposal}"
        )

        # Step 3: Agent B thinks and critiques
        await self.agent_b.think(f"Reviewing: {proposal}")
        critique = await self.agent_b.critique(proposal)

        # Step 4: Iteration loop
        iteration = 0
        max_iterations = 3

        while not critique['approved'] and iteration < max_iterations:
            await self.agent_b.communicate(
                self.agent_a.name,
                f"CRITIQUE: {critique['feedback']}"
            )

            # Agent A revises
            await self.agent_a.think(f"Addressing: {critique['feedback']}")
            proposal = await self.agent_a.revise(proposal, critique)

            # Agent B reviews again
            await self.agent_b.think(f"Reviewing revision {iteration + 1}")
            critique = await self.agent_b.critique(proposal)

            iteration += 1

        # Step 5: Final approval or escalation
        if critique['approved']:
            await self.agent_b.communicate(
                self.agent_a.name,
                "✓ APPROVED - Great work!"
            )
            return {"status": "approved", "result": proposal}
        else:
            # Escalate to PM Agent
            return {
                "status": "needs_pm_review",
                "result": proposal,
                "unresolved_issues": critique['feedback']
            }
```

### PM Agent Orchestrator

```python
class PMAgent:
    def __init__(self, departments: List[Department]):
        self.departments = {d.name: d for d in departments}
        self.task_queue = []
        self.active_tasks = {}

    async def process_user_request(self, request: str) -> str:
        """
        Main entry point for user requests
        """
        # Step 1: Analyze request and break into department tasks
        task_plan = await self.create_task_plan(request)

        # Step 2: Assign tasks to departments
        for dept_task in task_plan['tasks']:
            department = self.departments[dept_task['department']]
            task_id = self.assign_task(department, dept_task)

        # Step 3: Monitor and coordinate
        await self.coordinate_execution(task_plan)

        # Step 4: Collect results
        results = await self.gather_results(task_plan)

        return results

    async def create_task_plan(self, request: str) -> Dict:
        """
        Use LLM to break request into department tasks
        """
        prompt = f"""
        User request: {request}

        Break this into tasks for these departments:
        - Art: Visual assets (sprites, backgrounds, etc.)
        - Design: Game mechanics, balance, level design
        - Code: Implementation logic
        - QA: Testing and quality assurance
        - Playtest: User experience validation
        - Publishing: Build and distribution

        Return JSON with task assignments and dependencies.
        """

        plan = await self.llm.generate(prompt)
        return plan

    async def provide_feedback(
        self,
        department: str,
        agent: str,
        feedback: str
    ):
        """
        PM provides improvement notes to agents
        """
        dept = self.departments[department]
        await dept.receive_pm_feedback(agent, feedback)
```

---

## Database Schema

### Conversations Table

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    message_type VARCHAR(50),
    from_agent VARCHAR(50),
    to_agent VARCHAR(50),
    department VARCHAR(50),
    content TEXT,
    attachments JSONB,
    metadata JSONB,
    timestamp TIMESTAMP,
    visible_to TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_task_conversations ON conversations(task_id, timestamp);
CREATE INDEX idx_department_conversations ON conversations(department, timestamp);
```

### Tasks Table

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    user_request TEXT,
    status VARCHAR(50),
    assigned_departments TEXT[],
    progress JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result JSONB
);
```

---

## Tool Access Matrix

| Tool | Art | Design | Code | QA | Playtest | Publishing |
|------|-----|--------|------|----|-----------|-----------|
| ComfyUI API | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Aseprite MCP | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| GBStudio API | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Python Exec | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Git | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| Pytest | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Game Emulator | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Docker | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Analytics | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Bug Tracker | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Release Tools | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Implementation Timeline

### Week 1: Foundation
- [x] Design specification (this document)
- [ ] Agent base classes
- [ ] Message/conversation system
- [ ] Database schema
- [ ] PM Agent orchestrator

### Week 2: Departments
- [ ] Art department agents + ComfyUI/Aseprite integration
- [ ] Design department agents + GBStudio API
- [ ] Code department agents + Python tools

### Week 3: More Departments
- [ ] QA department agents + Testing tools
- [ ] Playtest department agents + Analytics
- [ ] Publishing department agents + Build tools

### Week 4: UI & Integration
- [ ] Real-time conversation viewer
- [ ] User feedback interface
- [ ] PM dashboard
- [ ] End-to-end testing

### Week 5: Polish & Launch
- [ ] Performance optimization
- [ ] Documentation
- [ ] Example workflows
- [ ] Production deployment

---

## Success Metrics

**Collaboration Quality:**
- Average iterations before approval: <3
- Critique relevance score: >80%
- User satisfaction with agent work: >4/5

**System Performance:**
- Response time (internal thought): <2s
- Response time (critique): <5s
- Response time (task completion): <5min
- Concurrent departments: 6 (all)

**Visibility:**
- All conversations logged: 100%
- Internal thoughts visible: 100%
- Real-time UI updates: <500ms latency

---

## Next Steps

1. **Review & Approve** this design specification
2. **Set up development environment** for multi-agent system
3. **Build foundation** (agent classes, messaging, database)
4. **Implement departments** one at a time with testing
5. **Create UI** for conversation viewing
6. **Deploy & iterate** based on real usage

---

**Status:** Ready for implementation
**Estimated Effort:** 5 weeks (1 developer)
**Dependencies:** Existing BSPM-UNIFIED infrastructure
**Risks:** LLM token costs (mitigated by caching), agent coordination complexity
