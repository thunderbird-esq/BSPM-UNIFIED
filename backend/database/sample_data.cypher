// ============================================================================
// Neo4j Sample Data for Development and Testing
// ============================================================================
// Purpose: Provide realistic test data for the BSPM-UNIFIED system
// Note: This file supplements the schema with additional test scenarios
// ============================================================================

// ============================================================================
// ADDITIONAL SAMPLE CONVERSATIONS - QA Testing Flow
// ============================================================================

CREATE (conv_qa_001:Conversation {
  id: "conv_qa_001",
  task_id: "task_boss_qa",
  department: "QA",
  started_at: datetime() + duration('PT90M'),
  ended_at: datetime() + duration('PT120M'),
  message_count: 15,
  outcome: "bugs_found",
  iterations: 1,
  summary: "Found 3 bugs in boss fight: collision detection, HP display, death animation",
  duration_seconds: 1800,
  participants: ["qa_a", "qa_b"],
  conversation_type: "testing",
  resolution_status: "in_progress"
});

CREATE (conv_playtest_001:Conversation {
  id: "conv_playtest_001",
  task_id: "task_boss_qa",
  department: "Playtest",
  started_at: datetime() + duration('PT95M'),
  ended_at: datetime() + duration('PT130M'),
  message_count: 20,
  outcome: "feedback_provided",
  iterations: 1,
  summary: "Boss fight feels good, difficulty is balanced, attack patterns clear",
  duration_seconds: 2100,
  participants: ["playtester_a", "playtester_b"],
  conversation_type: "playtesting",
  resolution_status: "resolved"
});

// ============================================================================
// ADDITIONAL SAMPLE MESSAGES - QA and Playtest feedback
// ============================================================================

CREATE (msg_qa_001:Message {
  id: "msg_qa_001",
  type: "bug_report",
  from_agent: "qa_a",
  to_agent: "coder_a",
  content: "BUG: Boss collision detection fails when player is in bottom-left corner of arena. Player can pass through boss sprite.",
  timestamp: datetime() + duration('PT95M'),
  sentiment: "neutral",
  has_attachments: true,
  attachment_ids: ["bug_report_001"],
  conversation_id: "conv_qa_001",
  message_index: 3,
  is_system_message: false,
  mentions: ["coder_a"],
  priority: "high",
  bug_severity: "major"
});

CREATE (msg_qa_002:Message {
  id: "msg_qa_002",
  type: "bug_report",
  from_agent: "qa_a",
  to_agent: "coder_a",
  content: "BUG: HP bar doesn't update smoothly, shows discrete jumps instead of gradual decrease.",
  timestamp: datetime() + duration('PT100M'),
  sentiment: "neutral",
  has_attachments: false,
  attachment_ids: [],
  conversation_id: "conv_qa_001",
  message_index: 8,
  is_system_message: false,
  mentions: ["coder_a"],
  priority: "medium",
  bug_severity: "minor"
});

CREATE (msg_playtest_001:Message {
  id: "msg_playtest_001",
  type: "feedback",
  from_agent: "playtester_a",
  to_agent: "designer_a",
  content: "The boss fight feels great! The HP reduction to 35 was perfect. I died twice before winning, which felt challenging but fair.",
  timestamp: datetime() + duration('PT100M'),
  sentiment: "positive",
  has_attachments: false,
  attachment_ids: [],
  conversation_id: "conv_playtest_001",
  message_index: 5,
  is_system_message: false,
  mentions: ["designer_a"],
  priority: "normal"
});

CREATE (msg_playtest_002:Message {
  id: "msg_playtest_002",
  type: "feedback",
  from_agent: "playtester_b",
  to_agent: "designer_a",
  content: "Attack patterns are clearly telegraphed. I could learn and adapt. Suggest adding a brief pause after phase 1 to phase 2 transition.",
  timestamp: datetime() + duration('PT115M'),
  sentiment: "constructive",
  has_attachments: false,
  attachment_ids: [],
  conversation_id: "conv_playtest_001",
  message_index: 12,
  is_system_message: false,
  mentions: ["designer_a"],
  priority: "low"
});

// ============================================================================
// ADDITIONAL ARTIFACTS - Bug reports and test results
// ============================================================================

CREATE (artifact_bug_001:Artifact {
  id: "bug_report_001",
  type: "bug_report",
  name: "boss_collision_bug.json",
  path: "/temp_outputs/bugs/boss_collision_bug.json",
  created_at: datetime() + duration('PT95M'),
  version: 1,
  status: "open",
  file_size_bytes: 856,
  metadata: {
    bug_id: "BUG-001",
    severity: "major",
    reproducibility: "always",
    steps_to_reproduce: ["1. Start boss fight", "2. Move to bottom-left corner", "3. Boss charges through player"],
    expected_behavior: "Boss should collide with player and deal damage",
    actual_behavior: "Boss passes through player sprite",
    affected_versions: ["v0.1.0"]
  },
  checksum: "sha256_bug001",
  created_by: "qa_a",
  mime_type: "application/json"
});

CREATE (artifact_playtest_results:Artifact {
  id: "playtest_results_001",
  type: "test_results",
  name: "boss_playtest_results.json",
  path: "/temp_outputs/playtests/boss_playtest_results.json",
  created_at: datetime() + duration('PT130M'),
  version: 1,
  status: "complete",
  file_size_bytes: 2400,
  metadata: {
    test_session: "boss_fight_balance_001",
    participants: 2,
    total_attempts: 8,
    success_rate: 0.625,
    average_attempts_to_win: 2.5,
    difficulty_rating: 7.5,
    fun_rating: 8.5,
    feedback_summary: "Boss fight is well-balanced and fun"
  },
  checksum: "sha256_playtest001",
  created_by: "playtester_a",
  mime_type: "application/json"
});

CREATE (artifact_code_fix_001:Artifact {
  id: "code_collision_fix_v1",
  type: "code",
  name: "boss_collision_fix.gbsscript",
  path: "/project_files/scenes/level_3/boss_collision_fix.gbsscript",
  created_at: datetime() + duration('PT140M'),
  version: 1,
  status: "in_review",
  file_size_bytes: 1200,
  metadata: {
    language: "gbstudio_script",
    line_count: 34,
    complexity: "medium",
    fixes: ["BUG-001"],
    changes: ["improved corner collision detection", "added boundary checks"]
  },
  checksum: "sha256_fix001",
  created_by: "coder_a",
  mime_type: "text/plain"
});

// ============================================================================
// ADDITIONAL TASKS - Bug fixing and polish
// ============================================================================

CREATE (task_bug_fix_001:Task {
  id: "task_bug_fix_collision",
  user_request: "Fix boss collision detection bug in bottom-left corner",
  status: "in_progress",
  priority: "high",
  started_at: datetime() + duration('PT96M'),
  completed_at: null,
  estimated_completion: datetime() + duration('PT150M'),
  progress: 60,
  assigned_departments: ["Code"],
  assigned_agents: ["coder_a"],
  blockers: [],
  parent_task_id: "task_boss_implementation",
  subtask_count: 0,
  deliverables: []
});

CREATE (task_polish_001:Task {
  id: "task_boss_polish",
  user_request: "Polish boss fight based on playtest feedback",
  status: "pending",
  priority: "medium",
  started_at: null,
  completed_at: null,
  estimated_completion: datetime() + duration('PT180M'),
  progress: 0,
  assigned_departments: ["Design", "Code"],
  assigned_agents: ["designer_a", "coder_a"],
  blockers: ["task_bug_fix_collision"],
  parent_task_id: "task_boss_implementation",
  subtask_count: 0,
  deliverables: []
});

// ============================================================================
// ADDITIONAL DECISIONS - Bug fixes and polish decisions
// ============================================================================

CREATE (decision_bug_fix:Decision {
  id: "dec_bug_fix_001",
  description: "Prioritize collision bug fix over new features",
  rationale: "Major bug affecting core gameplay, must be fixed before release",
  made_by: ["pm_agent"],
  approved_by: "pm_agent",
  timestamp: datetime() + duration('PT96M'),
  impact: "quality",
  confidence: 1.0,
  data_sources: ["qa_report", "severity_assessment"],
  affected_systems: ["boss_ai", "collision_detection"],
  decision_type: "prioritization",
  reversible: false
});

CREATE (decision_phase_transition:Decision {
  id: "dec_004",
  description: "Add 1-second pause during boss phase transition",
  rationale: "Playtester feedback suggests transition is too abrupt, brief pause improves player experience",
  made_by: ["designer_a"],
  approved_by: "pm_agent",
  timestamp: datetime() + duration('PT135M'),
  impact: "player_experience",
  confidence: 0.75,
  data_sources: ["playtest_feedback"],
  affected_systems: ["boss_ai", "animation_timing"],
  decision_type: "polish",
  reversible: true
});

// ============================================================================
// ADDITIONAL KNOWLEDGE - Lessons learned
// ============================================================================

CREATE (knowledge_collision:Knowledge {
  id: "know_005",
  topic: "gbstudio_collision_corner_cases",
  content: "GBStudio collision detection can fail at arena boundaries. Always add explicit boundary checks for corners.",
  source: "bug_discovery",
  confidence: 0.92,
  last_validated: datetime(),
  usage_count: 1,
  related_topics: ["collision_detection", "gbstudio_bugs", "quality_assurance"],
  knowledge_type: "bug_pattern",
  department: "Code",
  validated_by: ["coder_a", "qa_a"]
});

CREATE (knowledge_playtest_timing:Knowledge {
  id: "know_006",
  topic: "boss_phase_transition_timing",
  content: "Players need brief moment to recognize phase changes. 0.5-1 second pause between phases improves clarity.",
  source: "playtest_feedback",
  confidence: 0.80,
  last_validated: datetime(),
  usage_count: 1,
  related_topics: ["boss_design", "player_psychology", "pacing"],
  knowledge_type: "design_pattern",
  department: "Design",
  validated_by: ["playtester_a", "playtester_b"]
});

CREATE (knowledge_qa_process:Knowledge {
  id: "know_007",
  topic: "corner_collision_testing",
  content: "Always test collision detection at all four corners of the arena. Common bug location.",
  source: "qa_methodology",
  confidence: 0.95,
  last_validated: datetime(),
  usage_count: 3,
  related_topics: ["testing_strategy", "collision_detection", "qa_best_practices"],
  knowledge_type: "testing_pattern",
  department: "QA",
  validated_by: ["qa_a", "qa_b"]
});

// ============================================================================
// RELATIONSHIPS - QA Conversation
// ============================================================================

MATCH (agent:Agent {id: "qa_a"}), (conv:Conversation {id: "conv_qa_001"})
CREATE (agent)-[:PARTICIPATED_IN {
  message_count: 8,
  role: "executor",
  started_at: datetime() + duration('PT90M'),
  ended_at: datetime() + duration('PT120M')
}]->(conv);

MATCH (agent:Agent {id: "qa_b"}), (conv:Conversation {id: "conv_qa_001"})
CREATE (agent)-[:PARTICIPATED_IN {
  message_count: 7,
  role: "critic",
  started_at: datetime() + duration('PT90M'),
  ended_at: datetime() + duration('PT120M')
}]->(conv);

// Playtest Conversation
MATCH (agent:Agent {id: "playtester_a"}), (conv:Conversation {id: "conv_playtest_001"})
CREATE (agent)-[:PARTICIPATED_IN {
  message_count: 10,
  role: "executor",
  started_at: datetime() + duration('PT95M'),
  ended_at: datetime() + duration('PT130M')
}]->(conv);

MATCH (agent:Agent {id: "playtester_b"}), (conv:Conversation {id: "conv_playtest_001"})
CREATE (agent)-[:PARTICIPATED_IN {
  message_count: 10,
  role: "critic",
  started_at: datetime() + duration('PT95M'),
  ended_at: datetime() + duration('PT130M')
}]->(conv);

// Messages part of conversations
MATCH (msg:Message {id: "msg_qa_001"}), (conv:Conversation {id: "conv_qa_001"})
CREATE (msg)-[:PART_OF]->(conv);

MATCH (msg:Message {id: "msg_qa_002"}), (conv:Conversation {id: "conv_qa_001"})
CREATE (msg)-[:PART_OF]->(conv);

MATCH (msg:Message {id: "msg_playtest_001"}), (conv:Conversation {id: "conv_playtest_001"})
CREATE (msg)-[:PART_OF]->(conv);

MATCH (msg:Message {id: "msg_playtest_002"}), (conv:Conversation {id: "conv_playtest_001"})
CREATE (msg)-[:PART_OF]->(conv);

// Artifacts created by agents
MATCH (agent:Agent {id: "qa_a"}), (artifact:Artifact {id: "bug_report_001"})
CREATE (agent)-[:CREATED {
  version: 1,
  timestamp: datetime() + duration('PT95M'),
  time_spent_seconds: 300,
  tool_used: "manual"
}]->(artifact);

MATCH (agent:Agent {id: "playtester_a"}), (artifact:Artifact {id: "playtest_results_001"})
CREATE (agent)-[:CREATED {
  version: 1,
  timestamp: datetime() + duration('PT130M'),
  time_spent_seconds: 600,
  tool_used: "testing_framework"
}]->(artifact);

MATCH (agent:Agent {id: "coder_a"}), (artifact:Artifact {id: "code_collision_fix_v1"})
CREATE (agent)-[:CREATED {
  version: 1,
  timestamp: datetime() + duration('PT140M'),
  time_spent_seconds: 2400,
  tool_used: "gbstudio_api"
}]->(artifact);

// Conversations produced artifacts
MATCH (conv:Conversation {id: "conv_qa_001"}), (artifact:Artifact {id: "bug_report_001"})
CREATE (conv)-[:PRODUCED {
  final_version: true,
  iterations: 1,
  timestamp: datetime() + duration('PT120M')
}]->(artifact);

MATCH (conv:Conversation {id: "conv_playtest_001"}), (artifact:Artifact {id: "playtest_results_001"})
CREATE (conv)-[:PRODUCED {
  final_version: true,
  iterations: 1,
  timestamp: datetime() + duration('PT130M')
}]->(artifact);

// Tasks have conversations
MATCH (task:Task {id: "task_boss_qa"}), (conv:Conversation {id: "conv_qa_001"})
CREATE (task)-[:HAS_CONVERSATION]->(conv);

MATCH (task:Task {id: "task_boss_qa"}), (conv:Conversation {id: "conv_playtest_001"})
CREATE (task)-[:HAS_CONVERSATION]->(conv);

// Task dependencies
MATCH (t1:Task {id: "task_polish_001"}), (t2:Task {id: "task_bug_fix_collision"})
CREATE (t1)-[:DEPENDS_ON {
  dependency_type: "blocking",
  reason: "Cannot polish until critical bugs are fixed"
}]->(t2);

// Parent task relationships
MATCH (parent:Task {id: "task_boss_implementation"}), (child:Task {id: "task_bug_fix_collision"})
CREATE (parent)-[:HAS_SUBTASK]->(child);

MATCH (parent:Task {id: "task_boss_implementation"}), (child:Task {id: "task_polish_001"})
CREATE (parent)-[:HAS_SUBTASK]->(child);

// Artifact fixes bug
MATCH (fix:Artifact {id: "code_collision_fix_v1"}), (bug:Artifact {id: "bug_report_001"})
CREATE (fix)-[:FIXES {
  fix_type: "bug_fix",
  verification_status: "pending"
}]->(bug);

// Artifact references original code
MATCH (fix:Artifact {id: "code_collision_fix_v1"}), (original:Artifact {id: "code_boss_ai_v1"})
CREATE (fix)-[:PATCHES {
  patch_type: "bug_fix",
  lines_changed: 15
}]->(original);

// Decisions affect artifacts
MATCH (decision:Decision {id: "dec_bug_fix_001"}), (task:Task {id: "task_bug_fix_collision"})
CREATE (decision)-[:CREATED_TASK]->(task);

MATCH (decision:Decision {id: "dec_004"}), (task:Task {id: "task_polish_001"})
CREATE (decision)-[:CREATED_TASK]->(task);

// Knowledge learned from experience
MATCH (agent:Agent {id: "coder_a"}), (knowledge:Knowledge {id: "know_005"})
CREATE (agent)-[:LEARNED {
  timestamp: datetime() + duration('PT95M'),
  source: "bug_discovery",
  confidence: 0.92,
  application_count: 1
}]->(knowledge);

MATCH (agent:Agent {id: "qa_a"}), (knowledge:Knowledge {id: "know_007"})
CREATE (agent)-[:CONTRIBUTED {
  timestamp: datetime() + duration('PT120M'),
  contribution_type: "discovery",
  value_added: "identified testing pattern through experience"
}]->(knowledge);

MATCH (agent:Agent {id: "playtester_a"}), (knowledge:Knowledge {id: "know_006"})
CREATE (agent)-[:CONTRIBUTED {
  timestamp: datetime() + duration('PT130M'),
  contribution_type: "feedback",
  value_added: "identified player experience issue"
}]->(knowledge);

// Knowledge supports decisions
MATCH (knowledge:Knowledge {id: "know_005"}), (decision:Decision {id: "dec_bug_fix_001"})
CREATE (knowledge)-[:SUPPORTS {
  relevance_score: 0.95,
  application_context: "Bug discovery informed prioritization decision"
}]->(decision);

MATCH (knowledge:Knowledge {id: "know_006"}), (decision:Decision {id: "dec_004"})
CREATE (knowledge)-[:SUPPORTS {
  relevance_score: 0.90,
  application_context: "Player feedback informed design decision"
}]->(decision);

// Milestone updates
MATCH (milestone:Milestone {id: "milestone_boss_complete"}), (task:Task {id: "task_bug_fix_collision"})
CREATE (milestone)-[:INCLUDES {
  completion_status: "in_progress",
  contribution_percentage: 10
}]->(task);

MATCH (milestone:Milestone {id: "milestone_boss_complete"}), (task:Task {id: "task_polish_001"})
CREATE (milestone)-[:INCLUDES {
  completion_status: "pending",
  contribution_percentage: 5
}]->(task);

// Agent collaborations - QA and Playtest
MATCH (a1:Agent {id: "qa_a"}), (a2:Agent {id: "qa_b"})
CREATE (a1)-[:COLLABORATES_WITH {
  collaboration_type: "peer_testing",
  interaction_count: 28,
  success_rate: 0.94,
  department: "QA"
}]->(a2);

MATCH (a1:Agent {id: "playtester_a"}), (a2:Agent {id: "playtester_b"})
CREATE (a1)-[:COLLABORATES_WITH {
  collaboration_type: "peer_playtesting",
  interaction_count: 19,
  success_rate: 0.89,
  department: "Playtest"
}]->(a2);

// Cross-department collaboration
MATCH (qa:Agent {id: "qa_a"}), (coder:Agent {id: "coder_a"})
CREATE (qa)-[:COLLABORATES_WITH {
  collaboration_type: "bug_reporting",
  interaction_count: 15,
  success_rate: 0.87,
  department: "Cross-Departmental"
}]->(coder);

MATCH (playtester:Agent {id: "playtester_a"}), (designer:Agent {id: "designer_a"})
CREATE (playtester)-[:COLLABORATES_WITH {
  collaboration_type: "feedback",
  interaction_count: 22,
  success_rate: 0.91,
  department: "Cross-Departmental"
}]->(designer);

// ============================================================================
// SAMPLE DATA LOADING COMPLETE
// ============================================================================
// Additional nodes created: 20+
// Additional relationships created: 35+
// Total scenarios covered:
// - Boss fight creation (Art + Design + Code)
// - QA testing and bug discovery
// - Playtest feedback and balance validation
// - Bug fixing workflow
// - Polish and iteration
// - Cross-departmental collaboration
// - Knowledge extraction from experience
// ============================================================================
