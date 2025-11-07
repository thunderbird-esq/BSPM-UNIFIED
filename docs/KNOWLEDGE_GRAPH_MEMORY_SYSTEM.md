# Team Memory & Knowledge Graph System

**Version:** 1.0
**Date:** 2025-11-07
**Status:** DESIGN PHASE

---

## Overview

This document specifies a comprehensive **Knowledge Graph and Memory System** for the 12-agent game studio, enabling all agents to:
- Remember all past conversations and decisions
- Access shared project knowledge
- Query what they've done before
- Track project progress across departments
- Learn from each other's work

Additionally, provides **universal GBStudio access** for all departments via an updated CLI wrapper.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   12 AGENTS (6 Departments)                  │
│  Artist A/B, Designer A/B, Coder A/B, Tester A/B,          │
│  Player A/B, Publisher A/B                                  │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ▼                                ▼
┌────────────────────────┐      ┌──────────────────────────┐
│  MEMORY SYSTEM         │      │  GBSTUDIO ACCESS LAYER   │
│  - Conversation DB     │      │  - Modern CLI Wrapper    │
│  - Knowledge Graph     │      │  - Direct API Access     │
│  - Semantic Search     │      │  - Project Manipulation  │
│  - Context Retrieval   │      │  - Build Automation      │
└────────────┬───────────┘      └──────────┬───────────────┘
             │                             │
             ▼                             ▼
┌──────────────────────────────────────────────────────────┐
│                    KNOWLEDGE GRAPH                        │
│                       (Neo4j)                            │
│                                                          │
│  Nodes:                                                  │
│  - Agents (12)                                          │
│  - Conversations                                        │
│  - Tasks                                                │
│  - Artifacts (sprites, code, designs)                  │
│  - Decisions                                            │
│  - Project Milestones                                   │
│                                                          │
│  Relationships:                                          │
│  - CREATED_BY                                           │
│  - CRITIQUED_BY                                         │
│  - DEPENDS_ON                                           │
│  - REFERENCES                                           │
│  - LEADS_TO                                             │
│  - PART_OF                                              │
└──────────────────────────────────────────────────────────┘
```

---

## Part 1: Knowledge Graph Database

### Schema Design (Neo4j)

#### **Node Types**

**1. Agent Node**
```cypher
CREATE (agent:Agent {
  id: "artist_a",
  name: "Artist A",
  department: "Art",
  role: "executor",
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["sprite_art", "pixel_art", "game_boy_colors"]
})
```

**2. Conversation Node**
```cypher
CREATE (conv:Conversation {
  id: "conv_12345",
  task_id: "boss_fight_001",
  department: "Art",
  started_at: datetime(),
  ended_at: datetime(),
  message_count: 15,
  outcome: "approved",
  summary: "Created boss sprite with 3 animation frames"
})
```

**3. Message Node**
```cypher
CREATE (msg:Message {
  id: "msg_67890",
  type: "peer_message",  // or "internal_thought", "critique", "tool_usage"
  from_agent: "artist_a",
  to_agent: "artist_b",
  content: "What do you think of this sprite?",
  timestamp: datetime(),
  sentiment: "neutral",  // positive, negative, neutral
  has_attachments: true
})
```

**4. Artifact Node** (Things created by agents)
```cypher
CREATE (artifact:Artifact {
  id: "sprite_boss_v2",
  type: "sprite",  // sprite, code, design_doc, test, etc.
  name: "boss_v2.aseprite",
  path: "/temp_outputs/boss_v2.aseprite",
  created_at: datetime(),
  version: 2,
  status: "approved",
  metadata: {
    dimensions: "16x16",
    colors: 4,
    frames: 3
  }
})
```

**5. Task Node**
```cypher
CREATE (task:Task {
  id: "boss_fight_001",
  user_request: "Create a boss fight scene",
  status: "in_progress",
  priority: "high",
  started_at: datetime(),
  estimated_completion: datetime(),
  progress: 60,  // percentage
  blockers: []
})
```

**6. Decision Node** (Important choices made)
```cypher
CREATE (decision:Decision {
  id: "dec_12345",
  description: "Reduced boss HP from 50 to 35 based on playtest feedback",
  rationale: "85% death rate too high, unfun gameplay",
  made_by: ["designer_a", "designer_b"],
  approved_by: "pm_agent",
  timestamp: datetime(),
  impact: "game_balance"
})
```

**7. Milestone Node** (Project progress markers)
```cypher
CREATE (milestone:Milestone {
  id: "level_3_complete",
  name: "Level 3 Boss Fight Complete",
  date: datetime(),
  departments_involved: ["Art", "Design", "Code", "QA", "Playtest"],
  artifacts_delivered: 12,
  status: "complete"
})
```

**8. Knowledge Node** (Learned facts and patterns)
```cypher
CREATE (knowledge:Knowledge {
  id: "know_12345",
  topic: "game_boy_sprite_constraints",
  content: "Game Boy Color supports max 4 colors per sprite, 16x16 or 8x8 sizes",
  source: "multiple_experiences",
  confidence: 0.95,
  last_validated: datetime(),
  usage_count: 47
})
```

#### **Relationship Types**

```cypher
// Agent created artifact
(artist_a:Agent)-[:CREATED {version: 1, timestamp: datetime()}]->(sprite:Artifact)

// Agent critiqued artifact
(artist_b:Agent)-[:CRITIQUED {
  severity: "minor",
  approved: false,
  suggestions: ["increase contrast", "adjust colors"]
}]->(sprite:Artifact)

// Agent participated in conversation
(artist_a:Agent)-[:PARTICIPATED_IN {message_count: 8}]->(conv:Conversation)

// Message is part of conversation
(msg:Message)-[:PART_OF]->(conv:Conversation)

// Artifact created during conversation
(conv:Conversation)-[:PRODUCED]->(sprite:Artifact)

// Task has conversation
(task:Task)-[:HAS_CONVERSATION]->(conv:Conversation)

// Task depends on another task
(code_task:Task)-[:DEPENDS_ON]->(art_task:Task)

// Artifact references another artifact
(code:Artifact)-[:REFERENCES]->(sprite:Artifact)

// Decision affects artifact
(decision:Decision)-[:AFFECTS]->(boss_design:Artifact)

// Milestone includes task
(milestone:Milestone)-[:INCLUDES]->(task:Task)

// Agent learned knowledge
(agent:Agent)-[:LEARNED {
  source: "experience",
  confidence: 0.9
}]->(knowledge:Knowledge)

// Knowledge supports decision
(knowledge:Knowledge)-[:SUPPORTS]->(decision:Decision)
```

---

## Part 2: Memory & Retrieval System

### Agent Memory Interface

```python
# backend/multi_agent/memory.py

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from neo4j import GraphDatabase
import numpy as np
from sentence_transformers import SentenceTransformer

class AgentMemory:
    """
    Memory system for individual agents
    Provides access to:
    - Past conversations
    - Previous work
    - Learned knowledge
    - Related artifacts
    """

    def __init__(self, agent_id: str, neo4j_uri: str):
        self.agent_id = agent_id
        self.driver = GraphDatabase.driver(neo4j_uri)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    async def remember_conversation(
        self,
        topic: str,
        time_range: Optional[timedelta] = None
    ) -> List[Dict]:
        """
        Retrieve past conversations on similar topics

        Example:
            memory.remember_conversation("boss sprite creation")
            Returns all past conversations about creating boss sprites
        """
        # 1. Embed the topic query
        query_embedding = self.embedding_model.encode(topic)

        # 2. Search conversations via semantic similarity
        with self.driver.session() as session:
            result = session.run("""
                MATCH (agent:Agent {id: $agent_id})
                      -[:PARTICIPATED_IN]->(conv:Conversation)
                      -[:PART_OF]->(msg:Message)
                WHERE ($time_range IS NULL OR
                       conv.started_at > datetime() - duration($time_range))
                RETURN conv, collect(msg) as messages
                ORDER BY conv.started_at DESC
                LIMIT 10
            """, agent_id=self.agent_id, time_range=time_range)

            conversations = []
            for record in result:
                conv = record['conv']
                messages = record['messages']

                # Rank by semantic similarity
                conv_text = " ".join([m['content'] for m in messages])
                conv_embedding = self.embedding_model.encode(conv_text)
                similarity = np.dot(query_embedding, conv_embedding)

                conversations.append({
                    'conversation': conv,
                    'messages': messages,
                    'similarity': similarity
                })

            # Sort by similarity
            conversations.sort(key=lambda x: x['similarity'], reverse=True)
            return conversations[:5]

    async def recall_work(
        self,
        artifact_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Recall past work/artifacts created by this agent

        Example:
            memory.recall_work(artifact_type="sprite", status="approved")
            Returns all approved sprites this agent created
        """
        with self.driver.session() as session:
            query = """
                MATCH (agent:Agent {id: $agent_id})
                      -[r:CREATED]->(artifact:Artifact)
            """

            if artifact_type:
                query += " WHERE artifact.type = $artifact_type"
            if status:
                query += " AND artifact.status = $status"

            query += """
                RETURN artifact, r
                ORDER BY r.timestamp DESC
                LIMIT 20
            """

            result = session.run(
                query,
                agent_id=self.agent_id,
                artifact_type=artifact_type,
                status=status
            )

            return [record['artifact'] for record in result]

    async def query_knowledge(self, topic: str) -> List[Dict]:
        """
        Query learned knowledge on a topic

        Example:
            memory.query_knowledge("game boy color palette")
            Returns: "Game Boy Color supports 4 colors per sprite..."
        """
        query_embedding = self.embedding_model.encode(topic)

        with self.driver.session() as session:
            result = session.run("""
                MATCH (knowledge:Knowledge)
                WHERE knowledge.confidence > 0.7
                RETURN knowledge
                ORDER BY knowledge.usage_count DESC, knowledge.confidence DESC
                LIMIT 10
            """)

            knowledge_items = []
            for record in result:
                k = record['knowledge']
                k_embedding = self.embedding_model.encode(k['content'])
                similarity = np.dot(query_embedding, k_embedding)

                knowledge_items.append({
                    'knowledge': k,
                    'similarity': similarity
                })

            knowledge_items.sort(key=lambda x: x['similarity'], reverse=True)
            return knowledge_items[:3]

    async def get_related_artifacts(
        self,
        artifact_id: str,
        relationship: Optional[str] = None
    ) -> List[Dict]:
        """
        Get artifacts related to a given artifact

        Example:
            memory.get_related_artifacts("sprite_boss_v2", "REFERENCES")
            Returns all artifacts that reference this sprite
        """
        with self.driver.session() as session:
            if relationship:
                query = f"""
                    MATCH (source:Artifact {{id: $artifact_id}})
                          -[r:{relationship}]-(related:Artifact)
                    RETURN related, type(r) as rel_type
                """
            else:
                query = """
                    MATCH (source:Artifact {id: $artifact_id})
                          -[r]-(related:Artifact)
                    RETURN related, type(r) as rel_type
                """

            result = session.run(query, artifact_id=artifact_id)
            return [
                {
                    'artifact': record['related'],
                    'relationship': record['rel_type']
                }
                for record in result
            ]

    async def find_similar_past_tasks(self, current_task: str) -> List[Dict]:
        """
        Find similar tasks completed in the past

        Example:
            memory.find_similar_past_tasks("Create enemy sprite")
            Returns past enemy sprite tasks with outcomes
        """
        query_embedding = self.embedding_model.encode(current_task)

        with self.driver.session() as session:
            result = session.run("""
                MATCH (task:Task)
                WHERE task.status = 'complete'
                RETURN task
                ORDER BY task.started_at DESC
                LIMIT 50
            """)

            similar_tasks = []
            for record in result:
                task = record['task']
                task_embedding = self.embedding_model.encode(task['user_request'])
                similarity = np.dot(query_embedding, task_embedding)

                if similarity > 0.7:  # Threshold for relevance
                    similar_tasks.append({
                        'task': task,
                        'similarity': similarity
                    })

            similar_tasks.sort(key=lambda x: x['similarity'], reverse=True)
            return similar_tasks[:5]

    async def get_project_state(self) -> Dict:
        """
        Get current state of the entire project

        Returns overview of:
        - Completed milestones
        - In-progress tasks
        - Department statuses
        - Recent decisions
        """
        with self.driver.session() as session:
            # Get completed milestones
            milestones = session.run("""
                MATCH (m:Milestone)
                WHERE m.status = 'complete'
                RETURN m
                ORDER BY m.date DESC
                LIMIT 5
            """).data()

            # Get active tasks
            active_tasks = session.run("""
                MATCH (t:Task)
                WHERE t.status IN ['in_progress', 'pending']
                RETURN t, t.progress as progress
                ORDER BY t.priority DESC, t.started_at DESC
            """).data()

            # Get recent decisions
            decisions = session.run("""
                MATCH (d:Decision)
                RETURN d
                ORDER BY d.timestamp DESC
                LIMIT 10
            """).data()

            # Department activity
            dept_activity = session.run("""
                MATCH (agent:Agent)-[:PARTICIPATED_IN]->(conv:Conversation)
                WHERE conv.started_at > datetime() - duration('P7D')
                RETURN agent.department as department,
                       count(conv) as conversation_count,
                       sum(conv.message_count) as total_messages
                ORDER BY conversation_count DESC
            """).data()

            return {
                'completed_milestones': milestones,
                'active_tasks': active_tasks,
                'recent_decisions': decisions,
                'department_activity': dept_activity,
                'last_updated': datetime.now().isoformat()
            }

    async def log_message(self, message: Dict) -> str:
        """
        Log a message to the knowledge graph
        Creates nodes and relationships automatically
        """
        with self.driver.session() as session:
            # Create message node
            result = session.run("""
                CREATE (m:Message {
                    id: $id,
                    type: $type,
                    from_agent: $from_agent,
                    to_agent: $to_agent,
                    content: $content,
                    timestamp: datetime($timestamp),
                    sentiment: $sentiment
                })

                WITH m
                MATCH (agent:Agent {id: $from_agent})
                CREATE (agent)-[:SENT]->(m)

                WITH m
                MATCH (conv:Conversation {id: $conversation_id})
                CREATE (m)-[:PART_OF]->(conv)

                RETURN m.id as message_id
            """, **message)

            return result.single()['message_id']

    async def create_knowledge(
        self,
        topic: str,
        content: str,
        source: str = "experience"
    ) -> str:
        """
        Create a new knowledge node from learned experience
        """
        with self.driver.session() as session:
            result = session.run("""
                CREATE (k:Knowledge {
                    id: randomUUID(),
                    topic: $topic,
                    content: $content,
                    source: $source,
                    confidence: 0.8,
                    last_validated: datetime(),
                    usage_count: 0
                })

                WITH k
                MATCH (agent:Agent {id: $agent_id})
                CREATE (agent)-[:LEARNED {
                    timestamp: datetime(),
                    confidence: 0.8
                }]->(k)

                RETURN k.id as knowledge_id
            """, topic=topic, content=content, source=source, agent_id=self.agent_id)

            return result.single()['knowledge_id']
```

---

## Part 3: Cross-Department Knowledge Sharing

### Shared Memory Pool

```python
# backend/multi_agent/shared_memory.py

class SharedMemory:
    """
    Cross-department knowledge sharing
    All agents can query collective memory
    """

    def __init__(self, neo4j_uri: str):
        self.driver = GraphDatabase.driver(neo4j_uri)

    async def get_best_practices(self, department: str) -> List[Dict]:
        """
        Get best practices from a department

        Example:
            shared_memory.get_best_practices("Art")
            Returns: Top patterns used by Art department
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (agent:Agent {department: $department})
                      -[:CREATED]->(artifact:Artifact {status: 'approved'})
                WITH artifact, count(*) as approval_count
                WHERE approval_count > 3
                RETURN artifact.type as artifact_type,
                       collect(artifact.metadata) as successful_patterns,
                       approval_count
                ORDER BY approval_count DESC
                LIMIT 10
            """, department=department)

            return result.data()

    async def cross_reference_decisions(
        self,
        topic: str,
        departments: List[str]
    ) -> List[Dict]:
        """
        Find related decisions across multiple departments

        Example:
            shared_memory.cross_reference_decisions(
                "boss difficulty",
                ["Design", "Playtest"]
            )
            Returns decisions about boss difficulty from both departments
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (agent:Agent)-[:MADE_DECISION]->(d:Decision)
                WHERE agent.department IN $departments
                      AND toLower(d.description) CONTAINS toLower($topic)
                RETURN d, agent.department as department
                ORDER BY d.timestamp DESC
            """, topic=topic, departments=departments)

            return result.data()

    async def find_bottlenecks(self) -> List[Dict]:
        """
        Identify project bottlenecks by analyzing task dependencies
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (t1:Task)-[:DEPENDS_ON]->(t2:Task)
                WHERE t2.status <> 'complete'
                      AND t1.status = 'pending'
                WITH t2, count(t1) as blocked_tasks
                WHERE blocked_tasks > 2
                RETURN t2 as bottleneck_task,
                       blocked_tasks,
                       t2.assigned_to as responsible_agent
                ORDER BY blocked_tasks DESC
            """)

            return result.data()
```

---

## Part 4: GBStudio Access Layer

### Modern GBStudio CLI Wrapper

```python
# backend/gbstudio/cli_wrapper.py

import subprocess
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

class GBStudioCLI:
    """
    Modern wrapper around GB Studio CLI
    Supports both legacy gb-studio-cli and direct GB Studio v3+ access
    """

    def __init__(
        self,
        gbstudio_path: str = "/usr/local/bin/gb-studio",
        project_path: str = "./game_project"
    ):
        self.gbstudio_path = gbstudio_path
        self.project_path = Path(project_path)
        self.gb_studio_cli = "gbstudio"  # Legacy CLI if available

    async def build_rom(
        self,
        output_path: Optional[str] = None,
        color_only: bool = True
    ) -> Dict[str, Any]:
        """
        Build Game Boy ROM from GB Studio project

        Args:
            output_path: Where to save the ROM
            color_only: Build for Game Boy Color only (vs original GB)

        Returns:
            {
                "success": True,
                "rom_path": "/path/to/game.gbc",
                "size_bytes": 524288,
                "build_time": 12.5
            }
        """
        if output_path is None:
            output_path = self.project_path / "build" / "game.gbc"

        # Try modern GB Studio first
        if self._has_modern_gbstudio():
            return await self._build_with_modern(output_path, color_only)

        # Fallback to legacy CLI
        elif self._has_legacy_cli():
            return await self._build_with_legacy(output_path)

        else:
            raise RuntimeError("No GB Studio build tool found")

    async def build_web(
        self,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build web version of game
        """
        if output_dir is None:
            output_dir = self.project_path / "build" / "web"

        cmd = [self.gb_studio_cli, "build", str(self.project_path), str(output_dir), "--type", "web"]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return {
                "success": True,
                "output_dir": str(output_dir),
                "index_html": str(output_dir / "index.html")
            }
        else:
            return {
                "success": False,
                "error": result.stderr
            }

    async def get_project_info(self) -> Dict[str, Any]:
        """
        Read GB Studio project file and extract metadata
        """
        project_file = self.project_path / f"{self.project_path.name}.gbsproj"

        if not project_file.exists():
            project_file = self.project_path / "project.gbsproj"

        if not project_file.exists():
            raise FileNotFoundError(f"No GB Studio project found in {self.project_path}")

        with open(project_file, 'r') as f:
            project_data = json.load(f)

        return {
            "name": project_data.get('name', 'Untitled'),
            "author": project_data.get('author', 'Unknown'),
            "scenes": len(project_data.get('scenes', [])),
            "sprites": len(project_data.get('spriteSheets', [])),
            "backgrounds": len(project_data.get('backgrounds', [])),
            "music": len(project_data.get('music', [])),
            "variables": len(project_data.get('variables', [])),
            "gb_studio_version": project_data.get('_version', 'unknown')
        }

    async def add_sprite(
        self,
        sprite_path: str,
        sprite_name: str
    ) -> Dict[str, Any]:
        """
        Add a sprite to the GB Studio project

        Args:
            sprite_path: Path to sprite PNG file
            sprite_name: Name for the sprite in project
        """
        project_file = self._get_project_file()

        with open(project_file, 'r') as f:
            project_data = json.load(f)

        # Add sprite to spriteSheets
        sprite_id = f"sprite_{len(project_data.get('spriteSheets', []))}"

        sprite_data = {
            "id": sprite_id,
            "name": sprite_name,
            "filename": os.path.basename(sprite_path),
            "numFrames": 1,
            "width": 16,
            "height": 16
        }

        if 'spriteSheets' not in project_data:
            project_data['spriteSheets'] = []

        project_data['spriteSheets'].append(sprite_data)

        # Copy sprite file to project assets
        assets_dir = self.project_path / "assets" / "sprites"
        assets_dir.mkdir(parents=True, exist_ok=True)

        import shutil
        shutil.copy(sprite_path, assets_dir / os.path.basename(sprite_path))

        # Save updated project
        with open(project_file, 'w') as f:
            json.dump(project_data, f, indent=2)

        return {
            "success": True,
            "sprite_id": sprite_id,
            "sprite_name": sprite_name
        }

    async def add_scene(
        self,
        scene_name: str,
        background_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a new scene to the project
        """
        project_file = self._get_project_file()

        with open(project_file, 'r') as f:
            project_data = json.load(f)

        scene_id = f"scene_{len(project_data.get('scenes', []))}"

        scene_data = {
            "id": scene_id,
            "name": scene_name,
            "backgroundId": background_id or "",
            "actors": [],
            "triggers": [],
            "x": 0,
            "y": 0,
            "width": 20,
            "height": 18
        }

        if 'scenes' not in project_data:
            project_data['scenes'] = []

        project_data['scenes'].append(scene_data)

        with open(project_file, 'w') as f:
            json.dump(project_data, f, indent=2)

        return {
            "success": True,
            "scene_id": scene_id,
            "scene_name": scene_name
        }

    async def list_scenes(self) -> List[Dict]:
        """
        List all scenes in the project
        """
        project_file = self._get_project_file()

        with open(project_file, 'r') as f:
            project_data = json.load(f)

        return [
            {
                "id": scene['id'],
                "name": scene.get('name', 'Untitled'),
                "background": scene.get('backgroundId', ''),
                "actors": len(scene.get('actors', [])),
                "triggers": len(scene.get('triggers', []))
            }
            for scene in project_data.get('scenes', [])
        ]

    async def list_sprites(self) -> List[Dict]:
        """
        List all sprites in the project
        """
        project_file = self._get_project_file()

        with open(project_file, 'r') as f:
            project_data = json.load(f)

        return [
            {
                "id": sprite['id'],
                "name": sprite.get('name', 'Untitled'),
                "filename": sprite.get('filename', ''),
                "frames": sprite.get('numFrames', 1),
                "size": f"{sprite.get('width', 16)}x{sprite.get('height', 16)}"
            }
            for sprite in project_data.get('spriteSheets', [])
        ]

    async def validate_project(self) -> Dict[str, Any]:
        """
        Validate GB Studio project for errors
        """
        try:
            info = await self.get_project_info()

            issues = []

            if info['scenes'] == 0:
                issues.append("No scenes in project")

            if info['sprites'] == 0:
                issues.append("No sprites in project")

            # Check for missing files
            sprites_dir = self.project_path / "assets" / "sprites"
            if not sprites_dir.exists():
                issues.append("Sprites directory missing")

            backgrounds_dir = self.project_path / "assets" / "backgrounds"
            if not backgrounds_dir.exists():
                issues.append("Backgrounds directory missing")

            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "project_info": info
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }

    def _get_project_file(self) -> Path:
        """Find the project file"""
        candidates = [
            self.project_path / f"{self.project_path.name}.gbsproj",
            self.project_path / "project.gbsproj",
            self.project_path / "project.json"
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise FileNotFoundError(f"No GB Studio project file found in {self.project_path}")

    def _has_modern_gbstudio(self) -> bool:
        """Check if modern GB Studio is available"""
        return os.path.exists(self.gbstudio_path)

    def _has_legacy_cli(self) -> bool:
        """Check if legacy gb-studio-cli is available"""
        result = subprocess.run(['which', self.gb_studio_cli], capture_output=True)
        return result.returncode == 0

    async def _build_with_modern(self, output_path: str, color_only: bool) -> Dict:
        """Build with modern GB Studio"""
        # Implementation depends on GB Studio v3+ API
        # This would call the actual GB Studio build process
        pass

    async def _build_with_legacy(self, output_path: str) -> Dict:
        """Build with legacy gb-studio-cli"""
        cmd = [self.gb_studio_cli, "build", str(self.project_path), str(output_path), "--type", "rom"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return {
                "success": True,
                "rom_path": output_path,
                "size_bytes": os.path.getsize(output_path)
            }
        else:
            return {
                "success": False,
                "error": result.stderr
            }
```

---

## Part 5: Updated Tool Access Matrix

All departments now have GBStudio access:

| Tool | Art | Design | Code | QA | Playtest | Publishing |
|------|-----|--------|------|----|-----------|-----------|
| ComfyUI API | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Aseprite MCP | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **GBStudio CLI** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Agent Memory** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Knowledge Graph** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Python Exec | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Git | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| Pytest | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Game Emulator | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Docker | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Analytics | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |

**GBStudio Capabilities by Department:**

**Art:**
- Add sprites to project
- List sprites
- View sprite metadata

**Design:**
- Create/edit scenes
- Add actors and triggers
- Define game variables
- Set up scene connections

**Code:**
- Add custom scripts
- Modify game logic
- Read/write project data programmatically

**QA:**
- Build test ROMs
- Validate project structure
- Check for errors

**Playtest:**
- Build web versions for playtesting
- Generate test builds

**Publishing:**
- Build final ROMs
- Create distribution packages
- Validate builds

---

## Part 6: Example Agent Workflows with Memory

### Example 1: Artist A Uses Memory

```python
# Artist A receives task: "Create enemy sprite"

# Step 1: Check past work
past_enemies = await artist_a.memory.recall_work(
    artifact_type="sprite",
    status="approved"
)

# Step 2: Find similar tasks
similar_tasks = await artist_a.memory.find_similar_past_tasks(
    "Create enemy sprite"
)

# Step 3: Query knowledge
knowledge = await artist_a.memory.query_knowledge(
    "enemy sprite best practices"
)

# Artist A now knows:
# - Past enemies they created: slime (approved), bat (approved)
# - Similar task: "Created ghost enemy" - took 15 minutes, 2 iterations
# - Knowledge: "Enemy sprites should contrast with background"

# Artist A thinks:
await artist_a.think(
    "I've created slime and bat before. Ghost enemy was similar and "
    "worked well. I should make sure this new enemy contrasts with backgrounds."
)

# Artist A generates sprite with learned insights
sprite = await artist_a.use_tool("comfyui", prompt="skeleton enemy, contrasting colors")

# Artist A logs this work for future reference
await artist_a.memory.log_artifact(sprite)
```

### Example 2: Designer B Queries Cross-Department Knowledge

```python
# Designer B is balancing boss difficulty

# Step 1: Check what Design department did before
past_bosses = await shared_memory.get_best_practices("Design")
# Returns: "Boss HP typically 30-40 for mid-game"

# Step 2: See what Playtest said about difficulty
playtest_feedback = await shared_memory.cross_reference_decisions(
    topic="boss difficulty",
    departments=["Playtest", "Design"]
)
# Returns: "Players found bosses with HP>40 too frustrating"

# Step 3: Check recent QA testing results
qa_data = await designer_b.memory.remember_conversation(
    "boss testing results"
)
# Returns: "Level 3 boss: 75% death rate, too hard"

# Designer B makes informed decision
await designer_b.think(
    "Based on past bosses (30-40 HP), playtest feedback (HP>40 is frustrating), "
    "and QA data (75% death rate), I should set this boss to HP=35"
)
```

### Example 3: PM Agent Checks Project State

```python
# PM Agent wants to understand overall progress

project_state = await shared_memory.get_project_state()

# PM sees:
# - Milestones: Level 1 complete, Level 2 complete, Level 3 in progress (60%)
# - Active tasks: Boss sprite (Art), Boss AI (Code), Boss testing (QA)
# - Recent decisions: "Reduced boss HP to 35", "Added health pickup before boss"
# - Department activity: Art (45 messages), Design (32 messages), Code (28 messages)

# PM identifies bottleneck
bottlenecks = await shared_memory.find_bottlenecks()
# Returns: "Boss sprite" is blocking "Boss AI" and "Boss testing"

# PM provides feedback
await pm_agent.provide_feedback(
    department="Art",
    message="Boss sprite is critical path. Please prioritize completion."
)
```

---

## Part 7: Implementation Plan

### Phase 1: Database Setup (Week 1)
- [ ] Install Neo4j
- [ ] Create node and relationship schema
- [ ] Set up indexes for performance
- [ ] Create sample data for testing

### Phase 2: Memory System (Week 2)
- [ ] Implement AgentMemory class
- [ ] Implement SharedMemory class
- [ ] Add semantic search with embeddings
- [ ] Test memory retrieval

### Phase 3: GBStudio Integration (Week 2)
- [ ] Create GBStudioCLI wrapper
- [ ] Test with gb-studio-cli
- [ ] Add direct project manipulation
- [ ] Test sprite/scene addition

### Phase 4: Agent Integration (Week 3)
- [ ] Connect agents to memory system
- [ ] Add memory queries to agent workflows
- [ ] Test cross-department knowledge sharing
- [ ] Validate knowledge graph population

### Phase 5: UI & Visualization (Week 4)
- [ ] Create knowledge graph visualization
- [ ] Add memory search interface
- [ ] Show project state dashboard
- [ ] Add conversation history browser

---

## Part 8: Docker Service Addition

```yaml
# Add to docker-compose.intel-mac.yml

  neo4j:
    image: neo4j:5.13-community
    container_name: gbstudio_neo4j
    ports:
      - "7474:7474"  # Neo4j Browser
      - "7687:7687"  # Bolt protocol
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    environment:
      - NEO4J_AUTH=neo4j/password123
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_memory_heap_max__size=2G
    networks:
      - gbstudio_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:7474"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  neo4j_data:
    driver: local
    name: gbstudio_neo4j_data
  neo4j_logs:
    driver: local
    name: gbstudio_neo4j_logs
```

---

## Benefits Summary

### For Individual Agents:
- **Remember everything** they've done before
- **Learn from past successes** and failures
- **Query knowledge** when stuck
- **Avoid repeating mistakes**

### For Departments:
- **Share best practices** within department
- **Reference past work** easily
- **Track progress** on department goals
- **Coordinate better** with other departments

### For Project:
- **Full transparency** of all decisions
- **Historical record** of why choices were made
- **Identify bottlenecks** automatically
- **Track milestones** and progress
- **Universal GBStudio access** for all agents

### For You (User):
- **Understand agent reasoning** completely
- **Query any past conversation** or decision
- **See project evolution** over time
- **Identify patterns** in agent behavior
- **Audit all decisions** made by agents

---

## Next Steps

1. Review this design
2. Approve approach
3. Begin implementation (4-week timeline)
4. Start with Phase 1 (database setup)

---

**Status:** Ready for review and approval
**Estimated Implementation:** 4 weeks
**Dependencies:** Neo4j, sentence-transformers, gb-studio-cli
