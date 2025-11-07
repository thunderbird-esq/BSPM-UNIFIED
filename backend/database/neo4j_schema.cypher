// ============================================================================
// Neo4j Knowledge Graph Schema for BSPM-UNIFIED Multi-Agent Game Studio
// ============================================================================
// Purpose: Define complete data model for 12-agent collaborative game development
// Node Types: 8 (Agent, Conversation, Message, Artifact, Task, Decision, Milestone, Knowledge)
// Relationship Types: 10+ (Various interactions and dependencies)
// ============================================================================

// ============================================================================
// CLEAR DATABASE (USE WITH CAUTION - DEVELOPMENT ONLY)
// ============================================================================
// Uncomment the following line to clear all data before schema initialization
// MATCH (n) DETACH DELETE n;

// ============================================================================
// NODE TYPE 1: Agent
// ============================================================================
// Represents each of the 12 agents in the system
// Departments: Art, Design, Code, QA, Playtest, PM
// Roles: executor, critic, manager
// ============================================================================

// Art Department - Artist A (Executor)
CREATE (artist_a:Agent {
  id: "artist_a",
  name: "Artist A",
  department: "Art",
  role: "executor",
  tools: ["comfyui", "aseprite_mcp"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["sprite_art", "pixel_art", "game_boy_colors", "animation"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "🎨",
  specializations: ["character_sprites", "environmental_tiles", "UI_elements"]
});

// Art Department - Artist B (Critic)
CREATE (artist_b:Agent {
  id: "artist_b",
  name: "Artist B",
  department: "Art",
  role: "critic",
  tools: ["comfyui", "aseprite_mcp"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["art_critique", "composition", "color_theory", "game_boy_aesthetic"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "🖼️",
  specializations: ["visual_feedback", "style_consistency", "technical_review"]
});

// Design Department - Designer A (Executor)
CREATE (designer_a:Agent {
  id: "designer_a",
  name: "Designer A",
  department: "Design",
  role: "executor",
  tools: ["gbstudio_api"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["level_design", "game_mechanics", "enemy_ai", "boss_fights"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "🎮",
  specializations: ["combat_design", "difficulty_curves", "puzzle_design"]
});

// Design Department - Designer B (Critic)
CREATE (designer_b:Agent {
  id: "designer_b",
  name: "Designer B",
  department: "Design",
  role: "critic",
  tools: ["gbstudio_api"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["game_balance", "player_psychology", "difficulty_tuning", "pacing"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "⚖️",
  specializations: ["balance_analysis", "fun_factor", "accessibility"]
});

// Code Department - Coder A (Executor)
CREATE (coder_a:Agent {
  id: "coder_a",
  name: "Coder A",
  department: "Code",
  role: "executor",
  tools: ["gbstudio_api", "python", "javascript"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["gbstudio_scripting", "game_logic", "custom_events", "optimization"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "💻",
  specializations: ["entity_scripting", "state_machines", "performance"]
});

// Code Department - Coder B (Critic)
CREATE (coder_b:Agent {
  id: "coder_b",
  name: "Coder B",
  department: "Code",
  role: "critic",
  tools: ["gbstudio_api", "python", "javascript"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["code_review", "architecture", "best_practices", "debugging"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "🔍",
  specializations: ["code_quality", "edge_cases", "maintainability"]
});

// QA Department - QA A (Executor)
CREATE (qa_a:Agent {
  id: "qa_a",
  name: "QA A",
  department: "QA",
  role: "executor",
  tools: ["gbstudio_api", "testing_framework"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["functional_testing", "regression_testing", "bug_reporting", "test_automation"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "🐛",
  specializations: ["bug_discovery", "edge_case_testing", "integration_testing"]
});

// QA Department - QA B (Critic)
CREATE (qa_b:Agent {
  id: "qa_b",
  name: "QA B",
  department: "QA",
  role: "critic",
  tools: ["gbstudio_api", "testing_framework"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["test_coverage", "qa_strategy", "risk_assessment", "quality_metrics"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "📊",
  specializations: ["test_planning", "severity_assessment", "regression_prioritization"]
});

// Playtest Department - Playtester A (Executor)
CREATE (playtester_a:Agent {
  id: "playtester_a",
  name: "Playtester A",
  department: "Playtest",
  role: "executor",
  tools: ["gbstudio_emulator"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["gameplay_feedback", "user_experience", "difficulty_assessment", "fun_evaluation"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "🎯",
  specializations: ["player_experience", "flow_analysis", "engagement_metrics"]
});

// Playtest Department - Playtester B (Critic)
CREATE (playtester_b:Agent {
  id: "playtester_b",
  name: "Playtester B",
  department: "Playtest",
  role: "critic",
  tools: ["gbstudio_emulator"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["ux_critique", "accessibility", "learning_curve", "player_onboarding"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "🎲",
  specializations: ["first_impression", "tutorial_effectiveness", "player_frustration"]
});

// PM Department - PM Agent (Manager)
CREATE (pm:Agent {
  id: "pm_agent",
  name: "Project Manager",
  department: "PM",
  role: "manager",
  tools: ["gbstudio_api", "orchestration"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["project_management", "task_coordination", "resource_allocation", "timeline_management"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "📋",
  specializations: ["sprint_planning", "dependency_management", "risk_mitigation"]
});

// Universal GBStudio Agent (Shared Resource)
CREATE (gbstudio:Agent {
  id: "gbstudio_agent",
  name: "GBStudio Agent",
  department: "Universal",
  role: "executor",
  tools: ["gbstudio_mcp"],
  created_at: datetime(),
  total_tasks: 0,
  total_critiques: 0,
  expertise_areas: ["gbstudio_operations", "project_management", "asset_management", "build_compilation"],
  performance_score: 0.0,
  status: "active",
  avatar_emoji: "🎬",
  specializations: ["scene_management", "actor_operations", "trigger_logic", "variable_management"]
});

// ============================================================================
// NODE TYPE 2: Conversation
// ============================================================================
// Represents peer-to-peer or group conversations between agents
// ============================================================================

CREATE (conv_1:Conversation {
  id: "conv_art_001",
  task_id: "task_boss_sprite",
  department: "Art",
  started_at: datetime(),
  ended_at: datetime() + duration('PT15M'),
  message_count: 12,
  outcome: "approved",
  iterations: 2,
  summary: "Created boss sprite with 3 animation frames after initial critique",
  duration_seconds: 900,
  participants: ["artist_a", "artist_b"],
  conversation_type: "peer_critique",
  resolution_status: "resolved"
});

CREATE (conv_2:Conversation {
  id: "conv_design_001",
  task_id: "task_boss_fight",
  department: "Design",
  started_at: datetime(),
  ended_at: datetime() + duration('PT25M'),
  message_count: 18,
  outcome: "approved_with_changes",
  iterations: 3,
  summary: "Designed boss fight mechanics, reduced HP based on balance feedback",
  duration_seconds: 1500,
  participants: ["designer_a", "designer_b"],
  conversation_type: "peer_critique",
  resolution_status: "resolved"
});

CREATE (conv_3:Conversation {
  id: "conv_cross_dept_001",
  task_id: "task_boss_implementation",
  department: "Cross-Departmental",
  started_at: datetime(),
  ended_at: datetime() + duration('PT40M'),
  message_count: 24,
  outcome: "approved",
  iterations: 1,
  summary: "Integrated boss sprite, mechanics, and code successfully",
  duration_seconds: 2400,
  participants: ["artist_a", "designer_a", "coder_a", "pm_agent"],
  conversation_type: "integration",
  resolution_status: "resolved"
});

// ============================================================================
// NODE TYPE 3: Message
// ============================================================================
// Individual messages within conversations
// ============================================================================

CREATE (msg_1:Message {
  id: "msg_001",
  type: "peer_message",
  from_agent: "artist_a",
  to_agent: "artist_b",
  content: "I've completed the initial boss sprite. Here's version 1 with 3 animation frames.",
  timestamp: datetime(),
  sentiment: "neutral",
  has_attachments: true,
  attachment_ids: ["sprite_boss_v1"],
  conversation_id: "conv_art_001",
  message_index: 1,
  is_system_message: false,
  mentions: ["artist_b"],
  priority: "normal"
});

CREATE (msg_2:Message {
  id: "msg_002",
  type: "critique_message",
  from_agent: "artist_b",
  to_agent: "artist_a",
  content: "Good start! The animation is smooth, but the contrast is too low for Game Boy. Suggest increasing the color difference between layers.",
  timestamp: datetime() + duration('PT5M'),
  sentiment: "constructive",
  has_attachments: false,
  attachment_ids: [],
  conversation_id: "conv_art_001",
  message_index: 2,
  is_system_message: false,
  mentions: ["artist_a"],
  priority: "normal",
  critique_severity: "minor",
  critique_approved: false
});

CREATE (msg_3:Message {
  id: "msg_003",
  type: "peer_message",
  from_agent: "artist_a",
  to_agent: "artist_b",
  content: "Updated! I've increased the contrast using the standard GB palette more effectively. Version 2 attached.",
  timestamp: datetime() + duration('PT10M'),
  sentiment: "positive",
  has_attachments: true,
  attachment_ids: ["sprite_boss_v2"],
  conversation_id: "conv_art_001",
  message_index: 3,
  is_system_message: false,
  mentions: ["artist_b"],
  priority: "normal"
});

CREATE (msg_4:Message {
  id: "msg_004",
  type: "approval_message",
  from_agent: "artist_b",
  to_agent: "artist_a",
  content: "Excellent! This version has much better visibility. Approved for integration.",
  timestamp: datetime() + duration('PT15M'),
  sentiment: "positive",
  has_attachments: false,
  attachment_ids: [],
  conversation_id: "conv_art_001",
  message_index: 4,
  is_system_message: false,
  mentions: ["artist_a"],
  priority: "normal",
  critique_severity: null,
  critique_approved: true
});

CREATE (msg_5:Message {
  id: "msg_005",
  type: "pm_coordination",
  from_agent: "pm_agent",
  to_agent: "all",
  content: "Boss sprite approved. Moving to design phase for mechanics implementation.",
  timestamp: datetime() + duration('PT20M'),
  sentiment: "neutral",
  has_attachments: false,
  attachment_ids: [],
  conversation_id: "conv_cross_dept_001",
  message_index: 1,
  is_system_message: true,
  mentions: ["designer_a", "designer_b"],
  priority: "high"
});

// ============================================================================
// NODE TYPE 4: Artifact
// ============================================================================
// Created assets: sprites, code, designs, builds, etc.
// ============================================================================

CREATE (artifact_1:Artifact {
  id: "sprite_boss_v1",
  type: "sprite",
  name: "boss_v1.aseprite",
  path: "/temp_outputs/boss_v1.aseprite",
  created_at: datetime(),
  version: 1,
  status: "rejected",
  file_size_bytes: 1856,
  metadata: {
    dimensions: "16x16",
    colors: 4,
    frames: 3,
    frame_duration_ms: 200,
    palette: ["#0F380F", "#306230", "#8BAC0F", "#9BBC0F"],
    layer_count: 3,
    tags: ["boss", "enemy", "animated"]
  },
  checksum: "sha256_abc123",
  created_by: "artist_a",
  mime_type: "application/x-aseprite"
});

CREATE (artifact_2:Artifact {
  id: "sprite_boss_v2",
  type: "sprite",
  name: "boss_v2.aseprite",
  path: "/temp_outputs/boss_v2.aseprite",
  created_at: datetime() + duration('PT10M'),
  version: 2,
  status: "approved",
  file_size_bytes: 2048,
  metadata: {
    dimensions: "16x16",
    colors: 4,
    frames: 3,
    frame_duration_ms: 200,
    palette: ["#0F380F", "#306230", "#8BAC0F", "#9BBC0F"],
    layer_count: 3,
    tags: ["boss", "enemy", "animated", "high_contrast"]
  },
  checksum: "sha256_def456",
  created_by: "artist_a",
  mime_type: "application/x-aseprite",
  export_formats: ["png", "gif"]
});

CREATE (artifact_3:Artifact {
  id: "design_boss_mechanics_v1",
  type: "design_document",
  name: "boss_mechanics.json",
  path: "/temp_outputs/boss_mechanics.json",
  created_at: datetime() + duration('PT20M'),
  version: 1,
  status: "approved_with_changes",
  file_size_bytes: 3200,
  metadata: {
    boss_name: "Stone Guardian",
    hp: 50,
    damage: 10,
    attack_patterns: ["charge", "stomp", "projectile"],
    phases: 2,
    weaknesses: ["jump_attack"],
    rewards: ["boss_key", "100_gold"]
  },
  checksum: "sha256_ghi789",
  created_by: "designer_a",
  mime_type: "application/json"
});

CREATE (artifact_4:Artifact {
  id: "design_boss_mechanics_v2",
  type: "design_document",
  name: "boss_mechanics_v2.json",
  path: "/temp_outputs/boss_mechanics_v2.json",
  created_at: datetime() + duration('PT45M'),
  version: 2,
  status: "approved",
  file_size_bytes: 3400,
  metadata: {
    boss_name: "Stone Guardian",
    hp: 35,
    damage: 10,
    attack_patterns: ["charge", "stomp", "projectile"],
    phases: 2,
    weaknesses: ["jump_attack"],
    rewards: ["boss_key", "100_gold"],
    balance_notes: "Reduced HP from 50 to 35 based on difficulty feedback"
  },
  checksum: "sha256_jkl012",
  created_by: "designer_a",
  mime_type: "application/json"
});

CREATE (artifact_5:Artifact {
  id: "code_boss_ai_v1",
  type: "code",
  name: "boss_ai.gbsscript",
  path: "/project_files/scenes/level_3/boss_ai.gbsscript",
  created_at: datetime() + duration('PT60M'),
  version: 1,
  status: "approved",
  file_size_bytes: 5600,
  metadata: {
    language: "gbstudio_script",
    line_count: 142,
    complexity: "high",
    dependencies: ["sprite_boss_v2", "design_boss_mechanics_v2"],
    functions: ["boss_init", "boss_update", "boss_attack", "boss_take_damage", "boss_death"]
  },
  checksum: "sha256_mno345",
  created_by: "coder_a",
  mime_type: "text/plain"
});

// ============================================================================
// NODE TYPE 5: Task
// ============================================================================
// User requests and internal sub-tasks
// ============================================================================

CREATE (task_1:Task {
  id: "task_boss_sprite",
  user_request: "Create a boss sprite for level 3",
  status: "completed",
  priority: "high",
  started_at: datetime(),
  completed_at: datetime() + duration('PT15M'),
  estimated_completion: datetime() + duration('PT30M'),
  progress: 100,
  assigned_departments: ["Art"],
  assigned_agents: ["artist_a", "artist_b"],
  blockers: [],
  parent_task_id: "task_boss_implementation",
  subtask_count: 0,
  deliverables: ["sprite_boss_v2"]
});

CREATE (task_2:Task {
  id: "task_boss_fight",
  user_request: "Design boss fight mechanics for level 3",
  status: "completed",
  priority: "high",
  started_at: datetime() + duration('PT20M'),
  completed_at: datetime() + duration('PT45M'),
  estimated_completion: datetime() + duration('PT60M'),
  progress: 100,
  assigned_departments: ["Design"],
  assigned_agents: ["designer_a", "designer_b"],
  blockers: [],
  parent_task_id: "task_boss_implementation",
  subtask_count: 0,
  deliverables: ["design_boss_mechanics_v2"]
});

CREATE (task_3:Task {
  id: "task_boss_code",
  user_request: "Implement boss AI and behavior",
  status: "completed",
  priority: "high",
  started_at: datetime() + duration('PT50M'),
  completed_at: datetime() + duration('PT80M'),
  estimated_completion: datetime() + duration('PT90M'),
  progress: 100,
  assigned_departments: ["Code"],
  assigned_agents: ["coder_a", "coder_b"],
  blockers: [],
  parent_task_id: "task_boss_implementation",
  subtask_count: 0,
  deliverables: ["code_boss_ai_v1"]
});

CREATE (task_4:Task {
  id: "task_boss_implementation",
  user_request: "Create a complete boss fight for level 3",
  status: "in_progress",
  priority: "high",
  started_at: datetime(),
  completed_at: null,
  estimated_completion: datetime() + duration('PT120M'),
  progress: 75,
  assigned_departments: ["Art", "Design", "Code", "QA", "Playtest"],
  assigned_agents: ["pm_agent"],
  blockers: [],
  parent_task_id: null,
  subtask_count: 5,
  deliverables: []
});

CREATE (task_5:Task {
  id: "task_boss_qa",
  user_request: "Test boss fight for bugs and balance",
  status: "pending",
  priority: "high",
  started_at: null,
  completed_at: null,
  estimated_completion: datetime() + duration('PT150M'),
  progress: 0,
  assigned_departments: ["QA", "Playtest"],
  assigned_agents: ["qa_a", "playtester_a"],
  blockers: ["task_boss_code"],
  parent_task_id: "task_boss_implementation",
  subtask_count: 0,
  deliverables: []
});

// ============================================================================
// NODE TYPE 6: Decision
// ============================================================================
// Important decisions made during development
// ============================================================================

CREATE (decision_1:Decision {
  id: "dec_001",
  description: "Reduced boss HP from 50 to 35",
  rationale: "Initial playtests showed 85% death rate, indicating unfun difficulty spike",
  made_by: ["designer_a", "designer_b"],
  approved_by: "pm_agent",
  timestamp: datetime() + duration('PT40M'),
  impact: "game_balance",
  confidence: 0.9,
  data_sources: ["playtest_results", "designer_intuition"],
  affected_systems: ["boss_mechanics", "level_3_balance"],
  decision_type: "balance_adjustment",
  reversible: true
});

CREATE (decision_2:Decision {
  id: "dec_002",
  description: "Use high-contrast Game Boy palette for boss sprite",
  rationale: "Low contrast version was difficult to see on original Game Boy hardware",
  made_by: ["artist_a", "artist_b"],
  approved_by: "pm_agent",
  timestamp: datetime() + duration('PT10M'),
  impact: "visual_quality",
  confidence: 0.95,
  data_sources: ["gb_technical_specs", "artist_experience"],
  affected_systems: ["sprite_rendering", "visual_polish"],
  decision_type: "technical_requirement",
  reversible: false
});

CREATE (decision_3:Decision {
  id: "dec_003",
  description: "Implement 2-phase boss fight pattern",
  rationale: "Adds variety and maintains player engagement throughout the encounter",
  made_by: ["designer_a"],
  approved_by: "pm_agent",
  timestamp: datetime() + duration('PT25M'),
  impact: "gameplay_depth",
  confidence: 0.85,
  data_sources: ["game_design_patterns", "competitor_analysis"],
  affected_systems: ["boss_ai", "player_progression"],
  decision_type: "design_pattern",
  reversible: true
});

// ============================================================================
// NODE TYPE 7: Milestone
// ============================================================================
// Major project achievements
// ============================================================================

CREATE (milestone_1:Milestone {
  id: "milestone_boss_complete",
  name: "Level 3 Boss Fight Complete",
  date: datetime() + duration('PT120M'),
  departments_involved: ["Art", "Design", "Code", "QA", "Playtest"],
  artifacts_delivered: 5,
  status: "in_progress",
  completion_percentage: 75,
  celebration_message: "Level 3 boss fight is taking shape!",
  tasks_completed: ["task_boss_sprite", "task_boss_fight", "task_boss_code"],
  tasks_remaining: ["task_boss_qa"],
  estimated_completion: datetime() + duration('PT150M')
});

CREATE (milestone_2:Milestone {
  id: "milestone_level_3_complete",
  name: "Level 3 Fully Playable",
  date: datetime() + duration('PT300M'),
  departments_involved: ["Art", "Design", "Code", "QA", "Playtest"],
  artifacts_delivered: 0,
  status: "pending",
  completion_percentage: 30,
  celebration_message: null,
  tasks_completed: [],
  tasks_remaining: ["task_boss_implementation", "task_level_3_polish"],
  estimated_completion: datetime() + duration('PT480M')
});

// ============================================================================
// NODE TYPE 8: Knowledge
// ============================================================================
// Learned patterns and tribal knowledge
// ============================================================================

CREATE (knowledge_1:Knowledge {
  id: "know_001",
  topic: "game_boy_sprite_constraints",
  content: "Game Boy Color supports max 4 colors per sprite. Use palettes with high contrast for visibility on original GB hardware.",
  source: "multiple_experiences",
  confidence: 0.95,
  last_validated: datetime(),
  usage_count: 47,
  related_topics: ["pixel_art", "sprite_optimization", "game_boy_hardware"],
  knowledge_type: "technical_constraint",
  department: "Art",
  validated_by: ["artist_a", "artist_b"]
});

CREATE (knowledge_2:Knowledge {
  id: "know_002",
  topic: "boss_fight_difficulty_tuning",
  content: "Target 60-70% success rate on first attempt for satisfying difficulty. Above 80% death rate feels unfair.",
  source: "playtest_data",
  confidence: 0.85,
  last_validated: datetime(),
  usage_count: 23,
  related_topics: ["game_balance", "player_psychology", "difficulty_curves"],
  knowledge_type: "design_pattern",
  department: "Design",
  validated_by: ["designer_a", "designer_b", "playtester_a"]
});

CREATE (knowledge_3:Knowledge {
  id: "know_003",
  topic: "gbstudio_actor_state_management",
  content: "Use custom events for complex enemy AI. Store state in actor variables. Max 4 persistent variables per actor.",
  source: "technical_documentation",
  confidence: 0.90,
  last_validated: datetime(),
  usage_count: 34,
  related_topics: ["gbstudio_scripting", "enemy_ai", "state_machines"],
  knowledge_type: "technical_pattern",
  department: "Code",
  validated_by: ["coder_a", "coder_b"]
});

CREATE (knowledge_4:Knowledge {
  id: "know_004",
  topic: "animation_timing_game_boy",
  content: "Game Boy runs at 60 FPS. Sprite animations should use frame durations that are multiples of 16.67ms (1 frame). 3-5 frames typical for idle animations.",
  source: "hardware_specs",
  confidence: 0.98,
  last_validated: datetime(),
  usage_count: 56,
  related_topics: ["animation", "game_boy_hardware", "performance"],
  knowledge_type: "technical_constraint",
  department: "Art",
  validated_by: ["artist_a"]
});

// ============================================================================
// RELATIONSHIPS - Agent -> Artifact
// ============================================================================

MATCH (agent:Agent {id: "artist_a"}), (artifact:Artifact {id: "sprite_boss_v1"})
CREATE (agent)-[:CREATED {
  version: 1,
  timestamp: datetime(),
  time_spent_seconds: 600,
  tool_used: "aseprite_mcp"
}]->(artifact);

MATCH (agent:Agent {id: "artist_a"}), (artifact:Artifact {id: "sprite_boss_v2"})
CREATE (agent)-[:CREATED {
  version: 2,
  timestamp: datetime() + duration('PT10M'),
  time_spent_seconds: 300,
  tool_used: "aseprite_mcp"
}]->(artifact);

MATCH (agent:Agent {id: "designer_a"}), (artifact:Artifact {id: "design_boss_mechanics_v1"})
CREATE (agent)-[:CREATED {
  version: 1,
  timestamp: datetime() + duration('PT20M'),
  time_spent_seconds: 900,
  tool_used: "manual"
}]->(artifact);

MATCH (agent:Agent {id: "designer_a"}), (artifact:Artifact {id: "design_boss_mechanics_v2"})
CREATE (agent)-[:CREATED {
  version: 2,
  timestamp: datetime() + duration('PT45M'),
  time_spent_seconds: 600,
  tool_used: "manual"
}]->(artifact);

MATCH (agent:Agent {id: "coder_a"}), (artifact:Artifact {id: "code_boss_ai_v1"})
CREATE (agent)-[:CREATED {
  version: 1,
  timestamp: datetime() + duration('PT60M'),
  time_spent_seconds: 1200,
  tool_used: "gbstudio_api"
}]->(artifact);

// ============================================================================
// RELATIONSHIPS - Agent -> Artifact (CRITIQUED)
// ============================================================================

MATCH (agent:Agent {id: "artist_b"}), (artifact:Artifact {id: "sprite_boss_v1"})
CREATE (agent)-[:CRITIQUED {
  version: 1,
  severity: "minor",
  approved: false,
  suggestions: ["increase contrast", "use standard GB palette more effectively"],
  timestamp: datetime() + duration('PT5M'),
  critique_type: "technical_quality"
}]->(artifact);

MATCH (agent:Agent {id: "artist_b"}), (artifact:Artifact {id: "sprite_boss_v2"})
CREATE (agent)-[:CRITIQUED {
  version: 2,
  severity: null,
  approved: true,
  suggestions: [],
  timestamp: datetime() + duration('PT15M'),
  critique_type: "approval"
}]->(artifact);

MATCH (agent:Agent {id: "designer_b"}), (artifact:Artifact {id: "design_boss_mechanics_v1"})
CREATE (agent)-[:CRITIQUED {
  version: 1,
  severity: "major",
  approved: false,
  suggestions: ["reduce HP significantly", "adjust damage curve", "add more telegraph to attacks"],
  timestamp: datetime() + duration('PT35M'),
  critique_type: "balance"
}]->(artifact);

// ============================================================================
// RELATIONSHIPS - Agent -> Conversation (PARTICIPATED_IN)
// ============================================================================

MATCH (agent:Agent {id: "artist_a"}), (conv:Conversation {id: "conv_art_001"})
CREATE (agent)-[:PARTICIPATED_IN {
  message_count: 6,
  role: "executor",
  started_at: datetime(),
  ended_at: datetime() + duration('PT15M')
}]->(conv);

MATCH (agent:Agent {id: "artist_b"}), (conv:Conversation {id: "conv_art_001"})
CREATE (agent)-[:PARTICIPATED_IN {
  message_count: 6,
  role: "critic",
  started_at: datetime(),
  ended_at: datetime() + duration('PT15M')
}]->(conv);

MATCH (agent:Agent {id: "designer_a"}), (conv:Conversation {id: "conv_design_001"})
CREATE (agent)-[:PARTICIPATED_IN {
  message_count: 9,
  role: "executor",
  started_at: datetime() + duration('PT20M'),
  ended_at: datetime() + duration('PT45M')
}]->(conv);

MATCH (agent:Agent {id: "designer_b"}), (conv:Conversation {id: "conv_design_001"})
CREATE (agent)-[:PARTICIPATED_IN {
  message_count: 9,
  role: "critic",
  started_at: datetime() + duration('PT20M'),
  ended_at: datetime() + duration('PT45M')
}]->(conv);

MATCH (agent:Agent {id: "pm_agent"}), (conv:Conversation {id: "conv_cross_dept_001"})
CREATE (agent)-[:PARTICIPATED_IN {
  message_count: 6,
  role: "manager",
  started_at: datetime() + duration('PT50M'),
  ended_at: datetime() + duration('PT90M')
}]->(conv);

// ============================================================================
// RELATIONSHIPS - Message -> Conversation (PART_OF)
// ============================================================================

MATCH (msg:Message {id: "msg_001"}), (conv:Conversation {id: "conv_art_001"})
CREATE (msg)-[:PART_OF]->(conv);

MATCH (msg:Message {id: "msg_002"}), (conv:Conversation {id: "conv_art_001"})
CREATE (msg)-[:PART_OF]->(conv);

MATCH (msg:Message {id: "msg_003"}), (conv:Conversation {id: "conv_art_001"})
CREATE (msg)-[:PART_OF]->(conv);

MATCH (msg:Message {id: "msg_004"}), (conv:Conversation {id: "conv_art_001"})
CREATE (msg)-[:PART_OF]->(conv);

MATCH (msg:Message {id: "msg_005"}), (conv:Conversation {id: "conv_cross_dept_001"})
CREATE (msg)-[:PART_OF]->(conv);

// ============================================================================
// RELATIONSHIPS - Conversation -> Artifact (PRODUCED)
// ============================================================================

MATCH (conv:Conversation {id: "conv_art_001"}), (artifact:Artifact {id: "sprite_boss_v2"})
CREATE (conv)-[:PRODUCED {
  final_version: true,
  iterations: 2,
  timestamp: datetime() + duration('PT15M')
}]->(artifact);

MATCH (conv:Conversation {id: "conv_design_001"}), (artifact:Artifact {id: "design_boss_mechanics_v2"})
CREATE (conv)-[:PRODUCED {
  final_version: true,
  iterations: 2,
  timestamp: datetime() + duration('PT45M')
}]->(artifact);

// ============================================================================
// RELATIONSHIPS - Task -> Conversation (HAS_CONVERSATION)
// ============================================================================

MATCH (task:Task {id: "task_boss_sprite"}), (conv:Conversation {id: "conv_art_001"})
CREATE (task)-[:HAS_CONVERSATION]->(conv);

MATCH (task:Task {id: "task_boss_fight"}), (conv:Conversation {id: "conv_design_001"})
CREATE (task)-[:HAS_CONVERSATION]->(conv);

MATCH (task:Task {id: "task_boss_implementation"}), (conv:Conversation {id: "conv_cross_dept_001"})
CREATE (task)-[:HAS_CONVERSATION]->(conv);

// ============================================================================
// RELATIONSHIPS - Task -> Task (DEPENDS_ON)
// ============================================================================

MATCH (t1:Task {id: "task_boss_code"}), (t2:Task {id: "task_boss_sprite"})
CREATE (t1)-[:DEPENDS_ON {
  dependency_type: "blocking",
  reason: "Code needs sprite asset to reference"
}]->(t2);

MATCH (t1:Task {id: "task_boss_code"}), (t2:Task {id: "task_boss_fight"})
CREATE (t1)-[:DEPENDS_ON {
  dependency_type: "blocking",
  reason: "Code implements design specifications"
}]->(t2);

MATCH (t1:Task {id: "task_boss_qa"}), (t2:Task {id: "task_boss_code"})
CREATE (t1)-[:DEPENDS_ON {
  dependency_type: "blocking",
  reason: "Cannot test until implementation complete"
}]->(t2);

// ============================================================================
// RELATIONSHIPS - Task -> Task (PARENT_OF / SUBTASK_OF)
// ============================================================================

MATCH (parent:Task {id: "task_boss_implementation"}), (child:Task {id: "task_boss_sprite"})
CREATE (parent)-[:HAS_SUBTASK]->(child);

MATCH (parent:Task {id: "task_boss_implementation"}), (child:Task {id: "task_boss_fight"})
CREATE (parent)-[:HAS_SUBTASK]->(child);

MATCH (parent:Task {id: "task_boss_implementation"}), (child:Task {id: "task_boss_code"})
CREATE (parent)-[:HAS_SUBTASK]->(child);

MATCH (parent:Task {id: "task_boss_implementation"}), (child:Task {id: "task_boss_qa"})
CREATE (parent)-[:HAS_SUBTASK]->(child);

// ============================================================================
// RELATIONSHIPS - Artifact -> Artifact (REFERENCES / VERSION_OF)
// ============================================================================

MATCH (newer:Artifact {id: "sprite_boss_v2"}), (older:Artifact {id: "sprite_boss_v1"})
CREATE (newer)-[:VERSION_OF {
  version_number: 2,
  changes: ["increased_contrast", "improved_palette_usage"],
  improvement_type: "iteration"
}]->(older);

MATCH (newer:Artifact {id: "design_boss_mechanics_v2"}), (older:Artifact {id: "design_boss_mechanics_v1"})
CREATE (newer)-[:VERSION_OF {
  version_number: 2,
  changes: ["reduced_hp", "balance_adjustment"],
  improvement_type: "balance"
}]->(older);

MATCH (code:Artifact {id: "code_boss_ai_v1"}), (sprite:Artifact {id: "sprite_boss_v2"})
CREATE (code)-[:REFERENCES {
  reference_type: "uses_asset",
  usage_context: "sprite_rendering"
}]->(sprite);

MATCH (code:Artifact {id: "code_boss_ai_v1"}), (design:Artifact {id: "design_boss_mechanics_v2"})
CREATE (code)-[:IMPLEMENTS {
  implementation_completeness: 1.0,
  implementation_notes: "All mechanics from design doc implemented"
}]->(design);

// ============================================================================
// RELATIONSHIPS - Decision -> Artifact (AFFECTS)
// ============================================================================

MATCH (decision:Decision {id: "dec_001"}), (artifact:Artifact {id: "design_boss_mechanics_v2"})
CREATE (decision)-[:AFFECTS {
  change_type: "balance_adjustment",
  before_value: "HP=50",
  after_value: "HP=35",
  impact_level: "high"
}]->(artifact);

MATCH (decision:Decision {id: "dec_002"}), (artifact:Artifact {id: "sprite_boss_v2"})
CREATE (decision)-[:AFFECTS {
  change_type: "technical_requirement",
  before_value: "low_contrast",
  after_value: "high_contrast",
  impact_level: "medium"
}]->(artifact);

// ============================================================================
// RELATIONSHIPS - Milestone -> Task (INCLUDES)
// ============================================================================

MATCH (milestone:Milestone {id: "milestone_boss_complete"}), (task:Task {id: "task_boss_sprite"})
CREATE (milestone)-[:INCLUDES {
  completion_status: "completed",
  contribution_percentage: 20
}]->(task);

MATCH (milestone:Milestone {id: "milestone_boss_complete"}), (task:Task {id: "task_boss_fight"})
CREATE (milestone)-[:INCLUDES {
  completion_status: "completed",
  contribution_percentage: 25
}]->(task);

MATCH (milestone:Milestone {id: "milestone_boss_complete"}), (task:Task {id: "task_boss_code"})
CREATE (milestone)-[:INCLUDES {
  completion_status: "completed",
  contribution_percentage: 30
}]->(task);

MATCH (milestone:Milestone {id: "milestone_boss_complete"}), (task:Task {id: "task_boss_qa"})
CREATE (milestone)-[:INCLUDES {
  completion_status: "pending",
  contribution_percentage: 25
}]->(task);

// ============================================================================
// RELATIONSHIPS - Agent -> Knowledge (LEARNED / CONTRIBUTED)
// ============================================================================

MATCH (agent:Agent {id: "artist_a"}), (knowledge:Knowledge {id: "know_001"})
CREATE (agent)-[:LEARNED {
  timestamp: datetime(),
  source: "experience",
  confidence: 0.95,
  application_count: 15
}]->(knowledge);

MATCH (agent:Agent {id: "artist_b"}), (knowledge:Knowledge {id: "know_001"})
CREATE (agent)-[:CONTRIBUTED {
  timestamp: datetime(),
  contribution_type: "validation",
  value_added: "confirmed through critique experience"
}]->(knowledge);

MATCH (agent:Agent {id: "designer_a"}), (knowledge:Knowledge {id: "know_002"})
CREATE (agent)-[:LEARNED {
  timestamp: datetime(),
  source: "playtest_data",
  confidence: 0.85,
  application_count: 8
}]->(knowledge);

MATCH (agent:Agent {id: "coder_a"}), (knowledge:Knowledge {id: "know_003"})
CREATE (agent)-[:CONTRIBUTED {
  timestamp: datetime(),
  contribution_type: "discovery",
  value_added: "identified best practice through implementation"
}]->(knowledge);

// ============================================================================
// RELATIONSHIPS - Knowledge -> Decision (SUPPORTS / INFORMED)
// ============================================================================

MATCH (knowledge:Knowledge {id: "know_001"}), (decision:Decision {id: "dec_002"})
CREATE (knowledge)-[:SUPPORTS {
  relevance_score: 0.95,
  application_context: "Technical constraint drove design decision"
}]->(decision);

MATCH (knowledge:Knowledge {id: "know_002"}), (decision:Decision {id: "dec_001"})
CREATE (knowledge)-[:SUPPORTS {
  relevance_score: 0.90,
  application_context: "Balance guidelines informed HP reduction"
}]->(decision);

MATCH (knowledge:Knowledge {id: "know_003"}), (artifact:Artifact {id: "code_boss_ai_v1"})
CREATE (knowledge)-[:APPLIED_TO {
  application_type: "technical_pattern",
  effectiveness: 0.88
}]->(artifact);

// ============================================================================
// RELATIONSHIPS - Agent -> Agent (COLLABORATES_WITH)
// ============================================================================

MATCH (a1:Agent {id: "artist_a"}), (a2:Agent {id: "artist_b"})
CREATE (a1)-[:COLLABORATES_WITH {
  collaboration_type: "peer_critique",
  interaction_count: 47,
  success_rate: 0.92,
  department: "Art"
}]->(a2);

MATCH (a1:Agent {id: "designer_a"}), (a2:Agent {id: "designer_b"})
CREATE (a1)-[:COLLABORATES_WITH {
  collaboration_type: "peer_critique",
  interaction_count: 34,
  success_rate: 0.88,
  department: "Design"
}]->(a2);

MATCH (a1:Agent {id: "coder_a"}), (a2:Agent {id: "coder_b"})
CREATE (a1)-[:COLLABORATES_WITH {
  collaboration_type: "peer_critique",
  interaction_count: 29,
  success_rate: 0.90,
  department: "Code"
}]->(a2);

// ============================================================================
// SCHEMA INITIALIZATION COMPLETE
// ============================================================================
// Nodes created: 50+
// Relationships created: 60+
// Node types: 8 (Agent, Conversation, Message, Artifact, Task, Decision, Milestone, Knowledge)
// Relationship types: 15+ (CREATED, CRITIQUED, PARTICIPATED_IN, PART_OF, PRODUCED,
//                          HAS_CONVERSATION, DEPENDS_ON, HAS_SUBTASK, REFERENCES,
//                          VERSION_OF, IMPLEMENTS, AFFECTS, INCLUDES, LEARNED,
//                          CONTRIBUTED, SUPPORTS, APPLIED_TO, COLLABORATES_WITH)
// ============================================================================
