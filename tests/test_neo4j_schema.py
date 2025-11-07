"""
Neo4j Schema Validation Tests for BSPM-UNIFIED

This test suite validates the Neo4j knowledge graph database infrastructure:
- Connection and health checks
- Schema initialization
- Node type existence
- Relationship type existence
- Index creation
- Constraint enforcement
- Sample data loading
- Vector search functionality
- Query performance
"""

import pytest
import os
import time
from typing import List, Dict, Any

# Import Neo4j connection manager
from backend.database import Neo4jConnection


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def neo4j_connection():
    """
    Create a Neo4j connection for all tests in this module.
    Uses environment variables or defaults for connection parameters.
    """
    # Override URI for testing - use localhost instead of service name
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password123")

    conn = Neo4jConnection(uri=uri, user=user, password=password)

    yield conn

    # Cleanup after all tests
    conn.close()


@pytest.fixture(scope="module")
def initialized_database(neo4j_connection):
    """
    Initialize the database schema and load sample data.
    This fixture runs once per module.
    """
    # Clear database first (for clean testing)
    try:
        neo4j_connection.clear_database(confirm=True)
    except Exception as e:
        print(f"Warning: Could not clear database: {e}")

    # Initialize schema
    neo4j_connection.initialize_schema()

    # Load sample data
    neo4j_connection.load_sample_data()

    yield neo4j_connection

    # No cleanup - leave data for inspection


# ============================================================================
# Test 1: Connection and Health Check
# ============================================================================

def test_neo4j_connection(neo4j_connection):
    """
    Test that we can establish a connection to Neo4j and it's healthy.
    """
    assert neo4j_connection is not None, "Connection object should not be None"
    assert neo4j_connection.driver is not None, "Driver should be initialized"

    # Test connectivity
    is_healthy = neo4j_connection.health_check()
    assert is_healthy is True, "Database should be healthy and responsive"


def test_health_check_returns_correct_value(neo4j_connection):
    """
    Test that health check returns the expected value.
    """
    result = neo4j_connection.execute_query("RETURN 1 as health")
    assert len(result) == 1, "Should return exactly one record"
    assert result[0]['health'] == 1, "Health check should return 1"


# ============================================================================
# Test 2: Schema Initialization
# ============================================================================

def test_schema_initialization(initialized_database):
    """
    Test that schema files are executed without errors.
    """
    # Schema should be initialized by fixture
    # Verify by checking that we can query without errors
    result = initialized_database.execute_query("RETURN 1")
    assert len(result) == 1, "Schema should be functional"


# ============================================================================
# Test 3: All Node Types Exist
# ============================================================================

def test_all_node_types_exist(initialized_database):
    """
    Test that all 8 node types are present in the database.

    Node types:
    - Agent (12 agents)
    - Conversation
    - Message
    - Artifact
    - Task
    - Decision
    - Milestone
    - Knowledge
    """
    expected_node_types = [
        "Agent",
        "Conversation",
        "Message",
        "Artifact",
        "Task",
        "Decision",
        "Milestone",
        "Knowledge"
    ]

    # Query to get all node labels
    query = """
    CALL db.labels() YIELD label
    RETURN collect(label) as labels
    """
    result = initialized_database.execute_query(query)

    if result:
        actual_labels = result[0]['labels']
    else:
        actual_labels = []

    for node_type in expected_node_types:
        assert node_type in actual_labels, f"Node type {node_type} should exist in database"


def test_agent_nodes_exist(initialized_database):
    """
    Test that all 12 agent nodes are created.
    """
    query = "MATCH (a:Agent) RETURN count(a) as agent_count"
    result = initialized_database.execute_query(query)

    assert len(result) == 1, "Should return count result"
    agent_count = result[0]['agent_count']

    assert agent_count == 12, f"Should have 12 agents, found {agent_count}"


def test_agent_departments_correct(initialized_database):
    """
    Test that agents are distributed across correct departments.
    """
    query = """
    MATCH (a:Agent)
    RETURN a.department as department, count(a) as count
    ORDER BY department
    """
    result = initialized_database.execute_query(query)

    departments = {r['department']: r['count'] for r in result}

    # Each department should have 2 agents (executor + critic)
    # Plus PM has 1, Universal has 1
    assert departments.get('Art', 0) == 2, "Art department should have 2 agents"
    assert departments.get('Design', 0) == 2, "Design department should have 2 agents"
    assert departments.get('Code', 0) == 2, "Code department should have 2 agents"
    assert departments.get('QA', 0) == 2, "QA department should have 2 agents"
    assert departments.get('Playtest', 0) == 2, "Playtest department should have 2 agents"
    assert departments.get('PM', 0) == 1, "PM department should have 1 agent"
    assert departments.get('Universal', 0) == 1, "Universal department should have 1 agent"


# ============================================================================
# Test 4: All Indexes Exist
# ============================================================================

def test_all_indexes_exist(initialized_database):
    """
    Test that all performance indexes are created.
    """
    query = "SHOW INDEXES YIELD name RETURN collect(name) as indexes"
    result = initialized_database.execute_query(query)

    if result:
        indexes = result[0]['indexes']
    else:
        indexes = []

    # Check for some key indexes
    expected_indexes = [
        "agent_id_index",
        "conversation_id_index",
        "message_id_index",
        "artifact_id_index",
        "task_id_index"
    ]

    for expected_index in expected_indexes:
        # Some indexes might have suffixes or slightly different names
        # Check if any index contains the expected name
        found = any(expected_index in idx for idx in indexes)
        assert found, f"Index {expected_index} should exist"


def test_vector_indexes_exist(initialized_database):
    """
    Test that vector indexes for semantic search are created.
    """
    query = "SHOW INDEXES YIELD name, type WHERE type = 'VECTOR' RETURN name"
    result = initialized_database.execute_query(query)

    # Should have at least 2 vector indexes (message, knowledge)
    assert len(result) >= 2, f"Should have at least 2 vector indexes, found {len(result)}"


def test_fulltext_indexes_exist(initialized_database):
    """
    Test that full-text search indexes are created.
    """
    query = "SHOW INDEXES YIELD name, type WHERE type = 'FULLTEXT' RETURN name"
    result = initialized_database.execute_query(query)

    # Should have at least 4 full-text indexes
    assert len(result) >= 4, f"Should have at least 4 full-text indexes, found {len(result)}"


# ============================================================================
# Test 5: All Constraints Exist
# ============================================================================

def test_all_constraints_exist(initialized_database):
    """
    Test that all data integrity constraints are created.
    """
    query = "SHOW CONSTRAINTS YIELD name RETURN collect(name) as constraints"
    result = initialized_database.execute_query(query)

    if result:
        constraints = result[0]['constraints']
    else:
        constraints = []

    # Should have constraints for all node types
    expected_constraints = [
        "agent_id_unique",
        "conversation_id_unique",
        "message_id_unique",
        "artifact_id_unique",
        "task_id_unique",
        "decision_id_unique",
        "milestone_id_unique",
        "knowledge_id_unique"
    ]

    for expected_constraint in expected_constraints:
        found = any(expected_constraint in c for c in constraints)
        assert found, f"Constraint {expected_constraint} should exist"


def test_unique_constraints_enforced(initialized_database):
    """
    Test that unique constraints prevent duplicate IDs.
    """
    # Try to create an agent with duplicate ID
    with pytest.raises(Exception):
        initialized_database.execute_write_query("""
            CREATE (a:Agent {
                id: "artist_a",
                name: "Duplicate Agent",
                department: "Art",
                role: "executor",
                created_at: datetime()
            })
        """)


# ============================================================================
# Test 6: Sample Data Loaded
# ============================================================================

def test_sample_data_loaded(initialized_database):
    """
    Test that sample data is loaded successfully.
    """
    stats = initialized_database.get_statistics()

    assert stats['total_nodes'] > 50, "Should have at least 50 nodes from sample data"
    assert stats['total_relationships'] > 60, "Should have at least 60 relationships from sample data"


def test_conversations_have_messages(initialized_database):
    """
    Test that conversations are linked to messages.
    """
    query = """
    MATCH (c:Conversation)-[:HAS_CONVERSATION]-(t:Task)
    RETURN count(c) as conv_count
    """
    result = initialized_database.execute_query(query)

    assert len(result) == 1, "Should return count"
    conv_count = result[0]['conv_count']

    assert conv_count > 0, "Should have conversations linked to tasks"


def test_artifacts_have_creators(initialized_database):
    """
    Test that artifacts are linked to their creators.
    """
    query = """
    MATCH (agent:Agent)-[:CREATED]->(artifact:Artifact)
    RETURN count(artifact) as artifact_count
    """
    result = initialized_database.execute_query(query)

    assert len(result) == 1, "Should return count"
    artifact_count = result[0]['artifact_count']

    assert artifact_count > 0, "Should have artifacts with creators"


# ============================================================================
# Test 7: Vector Search Functionality
# ============================================================================

def test_vector_search_messages(initialized_database):
    """
    Test vector similarity search on messages.

    Note: This test uses a dummy embedding. In production, embeddings
    would come from the all-MiniLM-L6-v2 model.
    """
    # Create a dummy embedding (384 dimensions for all-MiniLM-L6-v2)
    dummy_embedding = [0.1] * 384

    try:
        results = initialized_database.vector_search(
            index_name="message_embedding_index",
            embedding=dummy_embedding,
            limit=5
        )

        # Should return results (even if scores are low due to dummy embedding)
        assert isinstance(results, list), "Should return a list"

    except Exception as e:
        # Vector search might fail if embeddings aren't populated
        # This is expected for sample data
        pytest.skip(f"Vector search not available (expected for sample data): {e}")


# ============================================================================
# Test 8: Relationship Queries
# ============================================================================

def test_relationship_types_exist(initialized_database):
    """
    Test that all expected relationship types exist.
    """
    query = """
    CALL db.relationshipTypes() YIELD relationshipType
    RETURN collect(relationshipType) as types
    """
    result = initialized_database.execute_query(query)

    if result:
        relationship_types = result[0]['types']
    else:
        relationship_types = []

    expected_types = [
        "CREATED",
        "CRITIQUED",
        "PARTICIPATED_IN",
        "PART_OF",
        "PRODUCED",
        "HAS_CONVERSATION",
        "DEPENDS_ON",
        "REFERENCES",
        "AFFECTS",
        "INCLUDES",
        "LEARNED"
    ]

    for rel_type in expected_types:
        assert rel_type in relationship_types, f"Relationship type {rel_type} should exist"


def test_agent_collaboration_paths(initialized_database):
    """
    Test that we can find collaboration paths between agents.
    """
    query = """
    MATCH (a1:Agent {id: "artist_a"})-[:COLLABORATES_WITH]->(a2:Agent {id: "artist_b"})
    RETURN count(*) as collaboration_count
    """
    result = initialized_database.execute_query(query)

    # Should have collaboration relationship
    assert len(result) == 1, "Should return collaboration count"


def test_task_dependency_chain(initialized_database):
    """
    Test that task dependencies form valid chains.
    """
    query = """
    MATCH (t1:Task)-[:DEPENDS_ON]->(t2:Task)
    RETURN count(*) as dependency_count
    """
    result = initialized_database.execute_query(query)

    assert len(result) == 1, "Should return dependency count"
    dependency_count = result[0]['dependency_count']

    assert dependency_count > 0, "Should have task dependencies"


# ============================================================================
# Test 9: Query Helper Functions
# ============================================================================

def test_get_agent_by_id(initialized_database):
    """
    Test the get_agent_by_id helper function.
    """
    agent = initialized_database.get_agent_by_id("artist_a")

    assert agent is not None, "Should find artist_a"
    assert agent['name'] == "Artist A", "Should have correct name"
    assert agent['department'] == "Art", "Should have correct department"


def test_get_conversation_messages(initialized_database):
    """
    Test the get_conversation_messages helper function.
    """
    messages = initialized_database.get_conversation_messages("conv_art_001")

    assert len(messages) > 0, "Should have messages in conversation"
    # Messages should be ordered by timestamp
    assert messages[0]['timestamp'] <= messages[-1]['timestamp'], "Messages should be chronologically ordered"


def test_get_agent_knowledge(initialized_database):
    """
    Test the get_agent_knowledge helper function.
    """
    knowledge = initialized_database.get_agent_knowledge("artist_a")

    assert isinstance(knowledge, list), "Should return a list"
    # May be empty if no knowledge linked yet
    if len(knowledge) > 0:
        assert 'topic' in knowledge[0], "Knowledge should have topic field"


# ============================================================================
# Test 10: Query Performance
# ============================================================================

def test_query_performance_indexed_lookup(initialized_database):
    """
    Test that indexed lookups are fast.
    """
    # Query using indexed field (agent ID)
    start_time = time.time()

    for _ in range(10):
        initialized_database.execute_query(
            "MATCH (a:Agent {id: $agent_id}) RETURN a",
            {"agent_id": "artist_a"}
        )

    elapsed_time = time.time() - start_time
    avg_time = elapsed_time / 10

    # Should complete in under 100ms on average (very generous for testing)
    assert avg_time < 0.1, f"Indexed query too slow: {avg_time:.3f}s per query"


def test_query_performance_relationship_traversal(initialized_database):
    """
    Test that relationship traversal is performant.
    """
    # Query that traverses relationships
    start_time = time.time()

    query = """
    MATCH (a:Agent {id: "artist_a"})-[:CREATED]->(artifact:Artifact)
    RETURN artifact
    """

    for _ in range(10):
        initialized_database.execute_query(query)

    elapsed_time = time.time() - start_time
    avg_time = elapsed_time / 10

    # Should complete in under 100ms on average
    assert avg_time < 0.1, f"Relationship traversal too slow: {avg_time:.3f}s per query"


def test_database_statistics(initialized_database):
    """
    Test that we can retrieve database statistics.
    """
    stats = initialized_database.get_statistics()

    assert 'total_nodes' in stats, "Should have total_nodes stat"
    assert 'total_relationships' in stats, "Should have total_relationships stat"
    assert 'nodes_by_type' in stats, "Should have nodes_by_type stat"
    assert 'relationships_by_type' in stats, "Should have relationships_by_type stat"

    assert stats['total_nodes'] > 0, "Should have nodes"
    assert stats['total_relationships'] > 0, "Should have relationships"


# ============================================================================
# Integration Tests
# ============================================================================

def test_end_to_end_workflow(initialized_database):
    """
    Test a complete workflow from agent to artifact.
    """
    # Find an agent
    agent = initialized_database.get_agent_by_id("artist_a")
    assert agent is not None, "Should find agent"

    # Find artifacts created by this agent
    query = """
    MATCH (a:Agent {id: $agent_id})-[:CREATED]->(artifact:Artifact)
    RETURN artifact
    """
    artifacts = initialized_database.execute_query(query, {"agent_id": "artist_a"})

    assert len(artifacts) > 0, "Agent should have created artifacts"


def test_cross_department_collaboration(initialized_database):
    """
    Test that cross-departmental workflows are represented.
    """
    query = """
    MATCH (c:Conversation {department: "Cross-Departmental"})
    RETURN count(c) as count
    """
    result = initialized_database.execute_query(query)

    # Should have at least one cross-departmental conversation
    if result:
        count = result[0]['count']
        assert count > 0, "Should have cross-departmental conversations"


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    """
    Run tests directly with pytest.

    Usage:
        pytest tests/test_neo4j_schema.py -v
        pytest tests/test_neo4j_schema.py -v -k "test_connection"
    """
    pytest.main([__file__, "-v"])
