// ============================================================================
// Neo4j Performance Indexes
// ============================================================================
// Purpose: Optimize query performance for common access patterns
// Index types: B-tree indexes, Vector indexes for semantic search
// ============================================================================

// ============================================================================
// AGENT INDEXES - Fast lookups for agent queries
// ============================================================================

// Primary lookup by agent ID
CREATE INDEX agent_id_index IF NOT EXISTS
FOR (a:Agent) ON (a.id);

// Filter by department (Art, Design, Code, QA, Playtest, PM)
CREATE INDEX agent_department_index IF NOT EXISTS
FOR (a:Agent) ON (a.department);

// Filter by role (executor, critic, manager)
CREATE INDEX agent_role_index IF NOT EXISTS
FOR (a:Agent) ON (a.role);

// Filter by status (active, inactive, busy)
CREATE INDEX agent_status_index IF NOT EXISTS
FOR (a:Agent) ON (a.status);

// Search agents by name
CREATE INDEX agent_name_index IF NOT EXISTS
FOR (a:Agent) ON (a.name);

// Performance metrics queries
CREATE INDEX agent_performance_score_index IF NOT EXISTS
FOR (a:Agent) ON (a.performance_score);

// Composite index for common query pattern: department + role
CREATE INDEX agent_dept_role_composite IF NOT EXISTS
FOR (a:Agent) ON (a.department, a.role);

// ============================================================================
// CONVERSATION INDEXES - Fast conversation retrieval
// ============================================================================

// Primary lookup by conversation ID
CREATE INDEX conversation_id_index IF NOT EXISTS
FOR (c:Conversation) ON (c.id);

// Find conversations for a specific task
CREATE INDEX conversation_task_index IF NOT EXISTS
FOR (c:Conversation) ON (c.task_id);

// Filter by department
CREATE INDEX conversation_department_index IF NOT EXISTS
FOR (c:Conversation) ON (c.department);

// Time-based queries (recent conversations)
CREATE INDEX conversation_started_at_index IF NOT EXISTS
FOR (c:Conversation) ON (c.started_at);

CREATE INDEX conversation_ended_at_index IF NOT EXISTS
FOR (c:Conversation) ON (c.ended_at);

// Filter by outcome (approved, rejected, approved_with_changes)
CREATE INDEX conversation_outcome_index IF NOT EXISTS
FOR (c:Conversation) ON (c.outcome);

// Filter by conversation type
CREATE INDEX conversation_type_index IF NOT EXISTS
FOR (c:Conversation) ON (c.conversation_type);

// Resolution status queries
CREATE INDEX conversation_resolution_index IF NOT EXISTS
FOR (c:Conversation) ON (c.resolution_status);

// Composite index: task + department
CREATE INDEX conversation_task_dept_composite IF NOT EXISTS
FOR (c:Conversation) ON (c.task_id, c.department);

// ============================================================================
// MESSAGE INDEXES - Fast message queries and semantic search
// ============================================================================

// Primary lookup by message ID
CREATE INDEX message_id_index IF NOT EXISTS
FOR (m:Message) ON (m.id);

// Filter by message type (peer_message, critique_message, approval_message, pm_coordination)
CREATE INDEX message_type_index IF NOT EXISTS
FOR (m:Message) ON (m.type);

// Time-based queries (message history)
CREATE INDEX message_timestamp_index IF NOT EXISTS
FOR (m:Message) ON (m.timestamp);

// Find messages in a conversation
CREATE INDEX message_conversation_index IF NOT EXISTS
FOR (m:Message) ON (m.conversation_id);

// Find messages from/to specific agents
CREATE INDEX message_from_agent_index IF NOT EXISTS
FOR (m:Message) ON (m.from_agent);

CREATE INDEX message_to_agent_index IF NOT EXISTS
FOR (m:Message) ON (m.to_agent);

// Filter by sentiment (positive, negative, neutral, constructive)
CREATE INDEX message_sentiment_index IF NOT EXISTS
FOR (m:Message) ON (m.sentiment);

// Filter messages with attachments
CREATE INDEX message_has_attachments_index IF NOT EXISTS
FOR (m:Message) ON (m.has_attachments);

// Composite index: conversation + timestamp for chronological ordering
CREATE INDEX message_conv_time_composite IF NOT EXISTS
FOR (m:Message) ON (m.conversation_id, m.timestamp);

// ============================================================================
// ARTIFACT INDEXES - Fast artifact retrieval
// ============================================================================

// Primary lookup by artifact ID
CREATE INDEX artifact_id_index IF NOT EXISTS
FOR (ar:Artifact) ON (ar.id);

// Filter by artifact type (sprite, code, design_document, build, etc.)
CREATE INDEX artifact_type_index IF NOT EXISTS
FOR (ar:Artifact) ON (ar.type);

// Filter by status (draft, in_review, approved, rejected)
CREATE INDEX artifact_status_index IF NOT EXISTS
FOR (ar:Artifact) ON (ar.status);

// Time-based queries (recently created artifacts)
CREATE INDEX artifact_created_at_index IF NOT EXISTS
FOR (ar:Artifact) ON (ar.created_at);

// Version management
CREATE INDEX artifact_version_index IF NOT EXISTS
FOR (ar:Artifact) ON (ar.version);

// Find artifacts by creator
CREATE INDEX artifact_created_by_index IF NOT EXISTS
FOR (ar:Artifact) ON (ar.created_by);

// Search by artifact name
CREATE INDEX artifact_name_index IF NOT EXISTS
FOR (ar:Artifact) ON (ar.name);

// MIME type filtering (for file type queries)
CREATE INDEX artifact_mime_type_index IF NOT EXISTS
FOR (ar:Artifact) ON (ar.mime_type);

// Composite index: type + status
CREATE INDEX artifact_type_status_composite IF NOT EXISTS
FOR (ar:Artifact) ON (ar.type, ar.status);

// ============================================================================
// TASK INDEXES - Fast task queries and scheduling
// ============================================================================

// Primary lookup by task ID
CREATE INDEX task_id_index IF NOT EXISTS
FOR (t:Task) ON (t.id);

// Filter by status (pending, in_progress, completed, blocked)
CREATE INDEX task_status_index IF NOT EXISTS
FOR (t:Task) ON (t.status);

// Priority-based queries (high, medium, low)
CREATE INDEX task_priority_index IF NOT EXISTS
FOR (t:Task) ON (t.priority);

// Time-based queries
CREATE INDEX task_started_at_index IF NOT EXISTS
FOR (t:Task) ON (t.started_at);

CREATE INDEX task_completed_at_index IF NOT EXISTS
FOR (t:Task) ON (t.completed_at);

CREATE INDEX task_estimated_completion_index IF NOT EXISTS
FOR (t:Task) ON (t.estimated_completion);

// Progress tracking
CREATE INDEX task_progress_index IF NOT EXISTS
FOR (t:Task) ON (t.progress);

// Parent task navigation
CREATE INDEX task_parent_task_id_index IF NOT EXISTS
FOR (t:Task) ON (t.parent_task_id);

// Composite index: status + priority for task queue
CREATE INDEX task_status_priority_composite IF NOT EXISTS
FOR (t:Task) ON (t.status, t.priority);

// ============================================================================
// DECISION INDEXES - Decision history and impact analysis
// ============================================================================

// Primary lookup by decision ID
CREATE INDEX decision_id_index IF NOT EXISTS
FOR (d:Decision) ON (d.id);

// Time-based queries (decision history)
CREATE INDEX decision_timestamp_index IF NOT EXISTS
FOR (d:Decision) ON (d.timestamp);

// Impact filtering
CREATE INDEX decision_impact_index IF NOT EXISTS
FOR (d:Decision) ON (d.impact);

// Decision type filtering
CREATE INDEX decision_type_index IF NOT EXISTS
FOR (d:Decision) ON (d.decision_type);

// Confidence level queries
CREATE INDEX decision_confidence_index IF NOT EXISTS
FOR (d:Decision) ON (d.confidence);

// Reversibility queries
CREATE INDEX decision_reversible_index IF NOT EXISTS
FOR (d:Decision) ON (d.reversible);

// ============================================================================
// MILESTONE INDEXES - Project tracking and reporting
// ============================================================================

// Primary lookup by milestone ID
CREATE INDEX milestone_id_index IF NOT EXISTS
FOR (mi:Milestone) ON (mi.id);

// Time-based queries (milestone timeline)
CREATE INDEX milestone_date_index IF NOT EXISTS
FOR (mi:Milestone) ON (mi.date);

CREATE INDEX milestone_estimated_completion_index IF NOT EXISTS
FOR (mi:Milestone) ON (mi.estimated_completion);

// Status filtering (pending, in_progress, complete)
CREATE INDEX milestone_status_index IF NOT EXISTS
FOR (mi:Milestone) ON (mi.status);

// Progress tracking
CREATE INDEX milestone_completion_percentage_index IF NOT EXISTS
FOR (mi:Milestone) ON (mi.completion_percentage);

// Milestone name search
CREATE INDEX milestone_name_index IF NOT EXISTS
FOR (mi:Milestone) ON (mi.name);

// ============================================================================
// KNOWLEDGE INDEXES - Knowledge retrieval and learning
// ============================================================================

// Primary lookup by knowledge ID
CREATE INDEX knowledge_id_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.id);

// Topic-based search
CREATE INDEX knowledge_topic_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.topic);

// Filter by knowledge type
CREATE INDEX knowledge_type_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.knowledge_type);

// Department-specific knowledge
CREATE INDEX knowledge_department_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.department);

// Confidence level filtering
CREATE INDEX knowledge_confidence_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.confidence);

// Usage tracking (frequently applied knowledge)
CREATE INDEX knowledge_usage_count_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.usage_count);

// Last validation time
CREATE INDEX knowledge_last_validated_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.last_validated);

// Source filtering
CREATE INDEX knowledge_source_index IF NOT EXISTS
FOR (k:Knowledge) ON (k.source);

// ============================================================================
// VECTOR INDEXES - Semantic search using embeddings
// ============================================================================

// Vector index for message semantic search
// Uses all-MiniLM-L6-v2 embeddings (384 dimensions)
// Cosine similarity for finding related messages
CALL db.index.vector.createNodeIndex(
  'message_embedding_index',
  'Message',
  'embedding',
  384,
  'cosine'
) YIELD name, type, createStatement
RETURN name, type, createStatement;

// Vector index for knowledge semantic search
// Enables finding related knowledge based on content similarity
CALL db.index.vector.createNodeIndex(
  'knowledge_embedding_index',
  'Knowledge',
  'embedding',
  384,
  'cosine'
) YIELD name, type, createStatement
RETURN name, type, createStatement;

// ============================================================================
// FULL-TEXT SEARCH INDEXES - Text search capabilities
// ============================================================================

// Full-text search on message content
CALL db.index.fulltext.createNodeIndex(
  'message_content_fulltext',
  ['Message'],
  ['content']
) YIELD name, type, createStatement
RETURN name, type, createStatement;

// Full-text search on knowledge content
CALL db.index.fulltext.createNodeIndex(
  'knowledge_content_fulltext',
  ['Knowledge'],
  ['content', 'topic']
) YIELD name, type, createStatement
RETURN name, type, createStatement;

// Full-text search on decision descriptions
CALL db.index.fulltext.createNodeIndex(
  'decision_description_fulltext',
  ['Decision'],
  ['description', 'rationale']
) YIELD name, type, createStatement
RETURN name, type, createStatement;

// Full-text search on task descriptions
CALL db.index.fulltext.createNodeIndex(
  'task_description_fulltext',
  ['Task'],
  ['user_request']
) YIELD name, type, createStatement
RETURN name, type, createStatement;

// ============================================================================
// RELATIONSHIP INDEXES - Fast relationship traversal
// ============================================================================

// Note: Neo4j 5.x automatically indexes relationship types
// Additional relationship property indexes can be added as needed

// ============================================================================
// INDEX CREATION COMPLETE
// ============================================================================
// Total indexes: 70+
// - 50+ B-tree property indexes
// - 2 vector indexes for semantic search
// - 4 full-text search indexes
// - Multiple composite indexes for common query patterns
// ============================================================================
