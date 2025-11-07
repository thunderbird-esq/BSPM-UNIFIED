// ============================================================================
// Neo4j Data Integrity Constraints
// ============================================================================
// Purpose: Enforce data integrity rules for the BSPM-UNIFIED knowledge graph
// Node Types: Agent, Conversation, Message, Artifact, Task, Decision, Milestone, Knowledge
// ============================================================================

// ============================================================================
// UNIQUE CONSTRAINTS - Ensure IDs are unique across all nodes
// ============================================================================

// Agent: Each agent must have a unique ID
CREATE CONSTRAINT agent_id_unique IF NOT EXISTS
FOR (a:Agent)
REQUIRE a.id IS UNIQUE;

// Conversation: Each conversation must have a unique ID
CREATE CONSTRAINT conversation_id_unique IF NOT EXISTS
FOR (c:Conversation)
REQUIRE c.id IS UNIQUE;

// Message: Each message must have a unique ID
CREATE CONSTRAINT message_id_unique IF NOT EXISTS
FOR (m:Message)
REQUIRE m.id IS UNIQUE;

// Artifact: Each artifact must have a unique ID
CREATE CONSTRAINT artifact_id_unique IF NOT EXISTS
FOR (ar:Artifact)
REQUIRE ar.id IS UNIQUE;

// Task: Each task must have a unique ID
CREATE CONSTRAINT task_id_unique IF NOT EXISTS
FOR (t:Task)
REQUIRE t.id IS UNIQUE;

// Decision: Each decision must have a unique ID
CREATE CONSTRAINT decision_id_unique IF NOT EXISTS
FOR (d:Decision)
REQUIRE d.id IS UNIQUE;

// Milestone: Each milestone must have a unique ID
CREATE CONSTRAINT milestone_id_unique IF NOT EXISTS
FOR (mi:Milestone)
REQUIRE mi.id IS UNIQUE;

// Knowledge: Each knowledge entry must have a unique ID
CREATE CONSTRAINT knowledge_id_unique IF NOT EXISTS
FOR (k:Knowledge)
REQUIRE k.id IS UNIQUE;

// ============================================================================
// EXISTENCE CONSTRAINTS - Required fields that must exist
// ============================================================================

// Agent required fields
CREATE CONSTRAINT agent_name_exists IF NOT EXISTS
FOR (a:Agent)
REQUIRE a.name IS NOT NULL;

CREATE CONSTRAINT agent_department_exists IF NOT EXISTS
FOR (a:Agent)
REQUIRE a.department IS NOT NULL;

CREATE CONSTRAINT agent_role_exists IF NOT EXISTS
FOR (a:Agent)
REQUIRE a.role IS NOT NULL;

CREATE CONSTRAINT agent_created_at_exists IF NOT EXISTS
FOR (a:Agent)
REQUIRE a.created_at IS NOT NULL;

// Conversation required fields
CREATE CONSTRAINT conversation_task_id_exists IF NOT EXISTS
FOR (c:Conversation)
REQUIRE c.task_id IS NOT NULL;

CREATE CONSTRAINT conversation_department_exists IF NOT EXISTS
FOR (c:Conversation)
REQUIRE c.department IS NOT NULL;

CREATE CONSTRAINT conversation_started_at_exists IF NOT EXISTS
FOR (c:Conversation)
REQUIRE c.started_at IS NOT NULL;

// Message required fields
CREATE CONSTRAINT message_type_exists IF NOT EXISTS
FOR (m:Message)
REQUIRE m.type IS NOT NULL;

CREATE CONSTRAINT message_from_agent_exists IF NOT EXISTS
FOR (m:Message)
REQUIRE m.from_agent IS NOT NULL;

CREATE CONSTRAINT message_content_exists IF NOT EXISTS
FOR (m:Message)
REQUIRE m.content IS NOT NULL;

CREATE CONSTRAINT message_timestamp_exists IF NOT EXISTS
FOR (m:Message)
REQUIRE m.timestamp IS NOT NULL;

CREATE CONSTRAINT message_conversation_id_exists IF NOT EXISTS
FOR (m:Message)
REQUIRE m.conversation_id IS NOT NULL;

// Artifact required fields
CREATE CONSTRAINT artifact_type_exists IF NOT EXISTS
FOR (ar:Artifact)
REQUIRE ar.type IS NOT NULL;

CREATE CONSTRAINT artifact_name_exists IF NOT EXISTS
FOR (ar:Artifact)
REQUIRE ar.name IS NOT NULL;

CREATE CONSTRAINT artifact_created_at_exists IF NOT EXISTS
FOR (ar:Artifact)
REQUIRE ar.created_at IS NOT NULL;

CREATE CONSTRAINT artifact_status_exists IF NOT EXISTS
FOR (ar:Artifact)
REQUIRE ar.status IS NOT NULL;

// Task required fields
CREATE CONSTRAINT task_user_request_exists IF NOT EXISTS
FOR (t:Task)
REQUIRE t.user_request IS NOT NULL;

CREATE CONSTRAINT task_status_exists IF NOT EXISTS
FOR (t:Task)
REQUIRE t.status IS NOT NULL;

CREATE CONSTRAINT task_started_at_exists IF NOT EXISTS
FOR (t:Task)
REQUIRE t.started_at IS NOT NULL;

// Decision required fields
CREATE CONSTRAINT decision_description_exists IF NOT EXISTS
FOR (d:Decision)
REQUIRE d.description IS NOT NULL;

CREATE CONSTRAINT decision_timestamp_exists IF NOT EXISTS
FOR (d:Decision)
REQUIRE d.timestamp IS NOT NULL;

CREATE CONSTRAINT decision_made_by_exists IF NOT EXISTS
FOR (d:Decision)
REQUIRE d.made_by IS NOT NULL;

// Milestone required fields
CREATE CONSTRAINT milestone_name_exists IF NOT EXISTS
FOR (mi:Milestone)
REQUIRE mi.name IS NOT NULL;

CREATE CONSTRAINT milestone_date_exists IF NOT EXISTS
FOR (mi:Milestone)
REQUIRE mi.date IS NOT NULL;

CREATE CONSTRAINT milestone_status_exists IF NOT EXISTS
FOR (mi:Milestone)
REQUIRE mi.status IS NOT NULL;

// Knowledge required fields
CREATE CONSTRAINT knowledge_topic_exists IF NOT EXISTS
FOR (k:Knowledge)
REQUIRE k.topic IS NOT NULL;

CREATE CONSTRAINT knowledge_content_exists IF NOT EXISTS
FOR (k:Knowledge)
REQUIRE k.content IS NOT NULL;

CREATE CONSTRAINT knowledge_confidence_exists IF NOT EXISTS
FOR (k:Knowledge)
REQUIRE k.confidence IS NOT NULL;

// ============================================================================
// CONSTRAINT VALIDATION COMPLETED
// ============================================================================
// Total constraints: 40+
// - 8 unique ID constraints (one per node type)
// - 30+ existence constraints (required fields)
// ============================================================================
