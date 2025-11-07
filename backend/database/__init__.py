"""
Neo4j Database Connection Manager for BSPM-UNIFIED Multi-Agent Game Studio

This module provides database connectivity, schema management, and query utilities
for the knowledge graph that powers the 12-agent collaborative system.

Features:
- Connection management with automatic retry
- Schema initialization from Cypher files
- Sample data loading for development
- Vector similarity search
- Health checks and monitoring
- Query helpers for common patterns
"""

import os
import time
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import logging

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jConnection:
    """
    Manages Neo4j database connections and provides query methods for the
    BSPM-UNIFIED knowledge graph.

    This class handles all interactions with the Neo4j database, including:
    - Connection lifecycle management
    - Schema initialization
    - Data loading
    - Query execution
    - Vector search
    - Health monitoring
    """

    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
        database: str = None,
        max_retry_attempts: int = 3,
        retry_delay_seconds: int = 2
    ):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j connection URI (defaults to NEO4J_URI env var or bolt://localhost:7687)
            user: Neo4j username (defaults to NEO4J_USER env var or 'neo4j')
            password: Neo4j password (defaults to NEO4J_PASSWORD env var or 'password123')
            database: Neo4j database name (defaults to NEO4J_DATABASE env var or 'neo4j')
            max_retry_attempts: Maximum number of connection retry attempts
            retry_delay_seconds: Delay between retry attempts
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password123")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        self.max_retry_attempts = max_retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

        self.driver: Optional[Driver] = None
        self._connect()

    def _connect(self):
        """
        Establish connection to Neo4j with retry logic.

        Raises:
            ServiceUnavailable: If connection fails after all retry attempts
            AuthError: If authentication fails
        """
        for attempt in range(1, self.max_retry_attempts + 1):
            try:
                logger.info(f"Connecting to Neo4j at {self.uri} (attempt {attempt}/{self.max_retry_attempts})")
                self.driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password)
                )
                # Test connection
                self.driver.verify_connectivity()
                logger.info("Successfully connected to Neo4j")
                return
            except ServiceUnavailable as e:
                logger.warning(f"Connection attempt {attempt} failed: {e}")
                if attempt < self.max_retry_attempts:
                    time.sleep(self.retry_delay_seconds)
                else:
                    logger.error("Max retry attempts reached, connection failed")
                    raise
            except AuthError as e:
                logger.error(f"Authentication failed: {e}")
                raise

    def close(self):
        """Close database connection and cleanup resources."""
        if self.driver:
            logger.info("Closing Neo4j connection")
            self.driver.close()
            self.driver = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters dictionary
            database: Database name (defaults to instance database)

        Returns:
            List of result dictionaries

        Raises:
            ServiceUnavailable: If database is not available
        """
        if not self.driver:
            raise RuntimeError("Database connection not established")

        db = database or self.database
        parameters = parameters or {}

        try:
            with self.driver.session(database=db) as session:
                result = session.run(query, parameters)
                records = [dict(record) for record in result]
                logger.debug(f"Query returned {len(records)} records")
                return records
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Parameters: {parameters}")
            raise

    def execute_write_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a write query in a transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters dictionary
            database: Database name (defaults to instance database)

        Returns:
            List of result dictionaries
        """
        if not self.driver:
            raise RuntimeError("Database connection not established")

        db = database or self.database
        parameters = parameters or {}

        def _execute_tx(tx):
            result = tx.run(query, parameters)
            return [dict(record) for record in result]

        try:
            with self.driver.session(database=db) as session:
                records = session.execute_write(_execute_tx)
                logger.debug(f"Write query returned {len(records)} records")
                return records
        except Exception as e:
            logger.error(f"Write query execution failed: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Parameters: {parameters}")
            raise

    def _execute_cypher_file(self, file_path: str):
        """
        Execute a Cypher file containing multiple statements.

        Args:
            file_path: Path to .cypher file

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Cypher file not found: {file_path}")

        logger.info(f"Executing Cypher file: {file_path}")

        with open(path, 'r') as f:
            content = f.read()

        # Split by semicolon, filter empty statements
        statements = [s.strip() for s in content.split(';') if s.strip()]

        # Filter out comments and empty lines
        statements = [
            s for s in statements
            if s and not s.startswith('//') and len(s) > 5
        ]

        logger.info(f"Found {len(statements)} statements in {file_path}")

        for i, statement in enumerate(statements, 1):
            try:
                # Handle CALL statements differently (they don't end with semicolon in splits)
                if 'CALL db.index.vector.createNodeIndex' in statement or \
                   'CALL db.index.fulltext.createNodeIndex' in statement:
                    logger.debug(f"Executing index creation statement {i}/{len(statements)}")
                    self.execute_query(statement)
                else:
                    self.execute_write_query(statement)

            except Exception as e:
                # Some statements may fail if already exist (indexes, constraints)
                # Log but continue
                logger.debug(f"Statement {i} raised exception (may be expected): {e}")

        logger.info(f"Completed execution of {file_path}")

    def initialize_schema(self, schema_dir: Optional[str] = None):
        """
        Initialize database schema from Cypher files.

        Executes files in order:
        1. constraints.cypher - Data integrity constraints
        2. neo4j_schema.cypher - Node and relationship definitions
        3. indexes.cypher - Performance indexes

        Args:
            schema_dir: Directory containing schema files (defaults to backend/database)
        """
        if schema_dir is None:
            # Default to backend/database directory
            schema_dir = Path(__file__).parent
        else:
            schema_dir = Path(schema_dir)

        logger.info(f"Initializing schema from: {schema_dir}")

        # Define execution order
        schema_files = [
            "constraints.cypher",
            "neo4j_schema.cypher",
            "indexes.cypher"
        ]

        for filename in schema_files:
            file_path = schema_dir / filename
            if file_path.exists():
                self._execute_cypher_file(str(file_path))
            else:
                logger.warning(f"Schema file not found: {file_path}")

        logger.info("Schema initialization complete")

    def load_sample_data(self, schema_dir: Optional[str] = None):
        """
        Load sample data for development and testing.

        Args:
            schema_dir: Directory containing sample_data.cypher (defaults to backend/database)
        """
        if schema_dir is None:
            schema_dir = Path(__file__).parent
        else:
            schema_dir = Path(schema_dir)

        sample_data_file = schema_dir / "sample_data.cypher"

        if sample_data_file.exists():
            logger.info("Loading sample data")
            self._execute_cypher_file(str(sample_data_file))
            logger.info("Sample data loaded successfully")
        else:
            logger.warning(f"Sample data file not found: {sample_data_file}")

    def clear_database(self, confirm: bool = False):
        """
        Clear all data from the database.

        WARNING: This deletes ALL nodes and relationships!

        Args:
            confirm: Must be True to proceed (safety check)

        Raises:
            ValueError: If confirm is not True
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to clear database")

        logger.warning("CLEARING ALL DATABASE DATA")

        # Delete all nodes and relationships
        self.execute_write_query("MATCH (n) DETACH DELETE n")

        logger.info("Database cleared")

    def health_check(self) -> bool:
        """
        Check if database is accessible and responsive.

        Returns:
            True if database is healthy, False otherwise
        """
        try:
            result = self.execute_query("RETURN 1 as health")
            return len(result) > 0 and result[0].get('health') == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with node counts, relationship counts, etc.
        """
        stats = {}

        # Total node count
        result = self.execute_query("MATCH (n) RETURN count(n) as total_nodes")
        stats['total_nodes'] = result[0]['total_nodes'] if result else 0

        # Node counts by label
        result = self.execute_query("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY count DESC
        """)
        stats['nodes_by_type'] = {r['label']: r['count'] for r in result}

        # Total relationship count
        result = self.execute_query("MATCH ()-[r]->() RETURN count(r) as total_relationships")
        stats['total_relationships'] = result[0]['total_relationships'] if result else 0

        # Relationship counts by type
        result = self.execute_query("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
        """)
        stats['relationships_by_type'] = {r['type']: r['count'] for r in result}

        return stats

    def vector_search(
        self,
        index_name: str,
        embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Perform vector similarity search.

        Args:
            index_name: Name of vector index (e.g., 'message_embedding_index')
            embedding: Query embedding vector
            limit: Maximum number of results
            min_score: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of (node_properties, score) tuples, ordered by score descending
        """
        query = f"""
        CALL db.index.vector.queryNodes(
            $index_name,
            $limit,
            $embedding
        ) YIELD node, score
        WHERE score >= $min_score
        RETURN properties(node) as node, score
        ORDER BY score DESC
        """

        results = self.execute_query(query, {
            "index_name": index_name,
            "embedding": embedding,
            "limit": limit,
            "min_score": min_score
        })

        return [(r['node'], r['score']) for r in results]

    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent properties or None if not found
        """
        result = self.execute_query(
            "MATCH (a:Agent {id: $agent_id}) RETURN a",
            {"agent_id": agent_id}
        )
        return result[0]['a'] if result else None

    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages in a conversation, ordered by timestamp.

        Args:
            conversation_id: Conversation identifier

        Returns:
            List of message properties
        """
        query = """
        MATCH (m:Message {conversation_id: $conversation_id})
        RETURN m
        ORDER BY m.timestamp ASC
        """
        results = self.execute_query(query, {"conversation_id": conversation_id})
        return [r['m'] for r in results]

    def get_task_artifacts(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all artifacts produced for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of artifact properties
        """
        query = """
        MATCH (t:Task {id: $task_id})-[:HAS_CONVERSATION]->(c:Conversation)-[:PRODUCED]->(a:Artifact)
        RETURN DISTINCT a
        ORDER BY a.created_at DESC
        """
        results = self.execute_query(query, {"task_id": task_id})
        return [r['a'] for r in results]

    def get_agent_knowledge(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get all knowledge learned by an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of knowledge properties
        """
        query = """
        MATCH (a:Agent {id: $agent_id})-[:LEARNED]->(k:Knowledge)
        RETURN k
        ORDER BY k.usage_count DESC
        """
        results = self.execute_query(query, {"agent_id": agent_id})
        return [r['k'] for r in results]


# Convenience function for getting a connection
def get_connection(**kwargs) -> Neo4jConnection:
    """
    Create and return a Neo4j connection.

    Args:
        **kwargs: Arguments passed to Neo4jConnection constructor

    Returns:
        Neo4jConnection instance
    """
    return Neo4jConnection(**kwargs)


# Export main class
__all__ = ['Neo4jConnection', 'get_connection']
