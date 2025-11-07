"""
Agent Memory System

Individual memory for each of the 12 agents in BSPM-UNIFIED.
Enables conversation recall, work history, knowledge queries, and learning.
"""

from typing import List, Dict, Optional
from datetime import timedelta
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from sentence_transformers import SentenceTransformer
import logging
import asyncio
from functools import wraps

from .embeddings import (
    create_embedding,
    cosine_similarity,
    embedding_to_list
)

logger = logging.getLogger(__name__)


def async_neo4j_operation(func):
    """Decorator to run Neo4j operations in executor for async support."""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(self, *args, **kwargs))
    return wrapper


class AgentMemory:
    """
    Memory system for individual agents.

    Provides access to:
    - Past conversations with semantic search
    - Work history and artifact recall
    - Knowledge queries and learning
    - Similar task identification
    - Related artifact discovery

    Example:
        >>> memory = AgentMemory(
        ...     agent_id="art_director",
        ...     neo4j_uri="bolt://localhost:7687"
        ... )
        >>> conversations = await memory.remember_conversation(
        ...     topic="boss sprite creation",
        ...     limit=5
        ... )
        >>> memory.close()
    """

    def __init__(
        self,
        agent_id: str,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password123",
        embedding_model: str = 'all-MiniLM-L6-v2'
    ):
        """
        Initialize agent memory system.

        Args:
            agent_id: Unique identifier for the agent (e.g., "art_director")
            neo4j_uri: Neo4j database connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            embedding_model: Sentence transformer model name
        """
        self.agent_id = agent_id
        self.neo4j_uri = neo4j_uri

        try:
            self.driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j for agent '{agent_id}'")
        except ServiceUnavailable:
            logger.error(f"Could not connect to Neo4j at {neo4j_uri}")
            raise
        except Exception as e:
            logger.error(f"Error initializing Neo4j driver: {e}")
            raise

        # Load embedding model
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            logger.info(
                f"Loaded embedding model '{embedding_model}' for agent '{agent_id}'"
            )
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise

        # Ensure agent node exists
        self._ensure_agent_exists()

    def _ensure_agent_exists(self):
        """Create agent node if it doesn't exist."""
        try:
            with self.driver.session() as session:
                session.run(
                    """
                    MERGE (a:Agent {id: $agent_id})
                    ON CREATE SET
                        a.created_at = datetime(),
                        a.updated_at = datetime()
                    ON MATCH SET
                        a.updated_at = datetime()
                    """,
                    agent_id=self.agent_id
                )
        except Exception as e:
            logger.error(f"Error ensuring agent exists: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.driver:
            self.driver.close()
            logger.info(f"Closed Neo4j connection for agent '{self.agent_id}'")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    async def remember_conversation(
        self,
        topic: str,
        time_range: Optional[timedelta] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Retrieve past conversations on similar topics using semantic search.

        Args:
            topic: Query string (e.g., "boss sprite creation")
            time_range: Optional time filter (e.g., timedelta(days=7))
            limit: Maximum conversations to return

        Returns:
            List of conversations with messages, ranked by relevance:
            [{
                "conversation_id": "conv_123",
                "conversation": {...},
                "messages": [...],
                "similarity": 0.92,
                "summary": "Created boss sprite with critiques",
                "started_at": "2024-01-15T10:30:00",
                "message_count": 12
            }]

        Example:
            >>> conversations = await memory.remember_conversation(
            ...     topic="sprite animation feedback",
            ...     time_range=timedelta(days=30),
            ...     limit=3
            ... )
        """
        logger.info(
            f"Agent '{self.agent_id}' remembering conversations about: {topic}"
        )

        # Create embedding for topic
        query_embedding = create_embedding(topic, self.embedding_model)

        def _query_conversations():
            with self.driver.session() as session:
                # Build time filter
                time_filter = ""
                params = {"agent_id": self.agent_id}

                if time_range:
                    time_filter = "AND conv.started_at > datetime() - duration($duration)"
                    # Convert timedelta to ISO 8601 duration
                    params["duration"] = f"P{time_range.days}DT{time_range.seconds}S"

                query = f"""
                MATCH (agent:Agent {{id: $agent_id}})
                      -[:PARTICIPATED_IN]->(conv:Conversation)
                OPTIONAL MATCH (conv)-[:HAS_MESSAGE]->(msg:Message)
                WHERE 1=1 {time_filter}
                WITH conv, collect(msg) as messages
                RETURN
                    conv.id as conversation_id,
                    conv,
                    messages,
                    size(messages) as message_count
                ORDER BY conv.started_at DESC
                LIMIT 20
                """

                result = session.run(query, **params)

                conversations = []
                for record in result:
                    conv = dict(record['conv'])
                    messages = [dict(m) for m in record['messages'] if m]

                    # Build conversation text for semantic comparison
                    conv_texts = []
                    if conv.get('summary'):
                        conv_texts.append(conv['summary'])
                    if conv.get('topic'):
                        conv_texts.append(conv['topic'])

                    # Add message contents
                    for msg in messages[:10]:  # Limit to first 10 messages for performance
                        if msg.get('content'):
                            conv_texts.append(msg['content'][:500])  # Limit message length

                    conv_text = " ".join(conv_texts)

                    # Calculate semantic similarity
                    if conv_text.strip():
                        conv_embedding = create_embedding(conv_text, self.embedding_model)
                        similarity = cosine_similarity(query_embedding, conv_embedding)
                    else:
                        similarity = 0.0

                    conversations.append({
                        'conversation_id': record['conversation_id'],
                        'conversation': conv,
                        'messages': messages,
                        'similarity': float(similarity),
                        'summary': conv.get('summary', ''),
                        'started_at': str(conv.get('started_at', '')),
                        'message_count': record['message_count']
                    })

                return conversations

        # Run in executor for async
        loop = asyncio.get_event_loop()
        conversations = await loop.run_in_executor(None, _query_conversations)

        # Sort by similarity and return top results
        conversations.sort(key=lambda x: x['similarity'], reverse=True)
        top_conversations = conversations[:limit]

        logger.info(
            f"Found {len(top_conversations)} relevant conversations for '{topic}'"
        )
        return top_conversations

    async def recall_work(
        self,
        artifact_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Recall past artifacts created by this agent.

        Args:
            artifact_type: Filter by type ("sprite", "code", "design", "music", etc.)
            status: Filter by status ("approved", "rejected", "in_progress", "complete")
            limit: Maximum artifacts to return

        Returns:
            List of artifacts with metadata:
            [{
                "artifact_id": "artifact_123",
                "artifact": {...},
                "created_at": "2024-01-15T14:30:00",
                "version": 2,
                "type": "sprite",
                "status": "approved"
            }]

        Example:
            >>> artifacts = await memory.recall_work(
            ...     artifact_type="sprite",
            ...     status="approved",
            ...     limit=10
            ... )
        """
        logger.info(
            f"Agent '{self.agent_id}' recalling work "
            f"(type={artifact_type}, status={status})"
        )

        def _query_artifacts():
            with self.driver.session() as session:
                filters = []
                params = {"agent_id": self.agent_id, "limit": limit}

                if artifact_type:
                    filters.append("artifact.type = $artifact_type")
                    params["artifact_type"] = artifact_type

                if status:
                    filters.append("artifact.status = $status")
                    params["status"] = status

                where_clause = " AND ".join(filters) if filters else "1=1"

                query = f"""
                MATCH (agent:Agent {{id: $agent_id}})
                      -[r:CREATED]->(artifact:Artifact)
                WHERE {where_clause}
                RETURN
                    artifact.id as artifact_id,
                    artifact,
                    r.timestamp as created_at,
                    r.version as version
                ORDER BY r.timestamp DESC
                LIMIT $limit
                """

                result = session.run(query, **params)

                return [
                    {
                        'artifact_id': record['artifact_id'],
                        'artifact': dict(record['artifact']),
                        'created_at': str(record['created_at']),
                        'version': record.get('version', 1),
                        'type': dict(record['artifact']).get('type', 'unknown'),
                        'status': dict(record['artifact']).get('status', 'unknown')
                    }
                    for record in result
                ]

        loop = asyncio.get_event_loop()
        artifacts = await loop.run_in_executor(None, _query_artifacts)

        logger.info(f"Recalled {len(artifacts)} artifacts")
        return artifacts

    async def query_knowledge(
        self,
        topic: str,
        min_confidence: float = 0.7,
        limit: int = 3
    ) -> List[Dict]:
        """
        Query learned knowledge on a topic using semantic search.

        Args:
            topic: Query string (e.g., "sprite animation best practices")
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            limit: Maximum knowledge items to return

        Returns:
            List of knowledge items ranked by relevance:
            [{
                "knowledge_id": "know_123",
                "knowledge": {...},
                "similarity": 0.95,
                "topic": "sprite_animation",
                "content": "Use 4-6 frames for walk cycles",
                "confidence": 0.9,
                "usage_count": 15,
                "source": "experience"
            }]

        Example:
            >>> knowledge = await memory.query_knowledge(
            ...     topic="color palette selection",
            ...     min_confidence=0.8
            ... )
        """
        logger.info(f"Agent '{self.agent_id}' querying knowledge: {topic}")

        query_embedding = create_embedding(topic, self.embedding_model)

        def _query_knowledge():
            with self.driver.session() as session:
                query = """
                MATCH (k:Knowledge)
                WHERE k.confidence >= $min_confidence
                RETURN
                    k.id as knowledge_id,
                    k
                ORDER BY k.usage_count DESC, k.confidence DESC
                LIMIT 20
                """

                result = session.run(query, min_confidence=min_confidence)

                knowledge_items = []
                for record in result:
                    k = dict(record['k'])
                    k_content = k.get('content', '')

                    # Calculate semantic similarity
                    if k_content.strip():
                        k_embedding = create_embedding(k_content, self.embedding_model)
                        similarity = cosine_similarity(query_embedding, k_embedding)
                    else:
                        similarity = 0.0

                    knowledge_items.append({
                        'knowledge_id': record['knowledge_id'],
                        'knowledge': k,
                        'similarity': float(similarity),
                        'topic': k.get('topic', ''),
                        'content': k_content,
                        'confidence': k.get('confidence', 0.0),
                        'usage_count': k.get('usage_count', 0),
                        'source': k.get('source', 'unknown')
                    })

                return knowledge_items

        loop = asyncio.get_event_loop()
        knowledge_items = await loop.run_in_executor(None, _query_knowledge)

        # Sort by similarity and return top results
        knowledge_items.sort(key=lambda x: x['similarity'], reverse=True)
        top_knowledge = knowledge_items[:limit]

        logger.info(f"Found {len(top_knowledge)} relevant knowledge items")
        return top_knowledge

    async def find_similar_past_tasks(
        self,
        current_task: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Find similar tasks completed in the past using semantic search.

        Returns tasks with outcomes and timing information.

        Args:
            current_task: Description of current task
            limit: Maximum similar tasks to return

        Returns:
            List of similar tasks:
            [{
                "task_id": "task_123",
                "task": {...},
                "similarity": 0.88,
                "duration": 3600,
                "outcome": "success",
                "user_request": "Create enemy sprite"
            }]

        Example:
            >>> similar_tasks = await memory.find_similar_past_tasks(
            ...     current_task="Design a boss character sprite",
            ...     limit=5
            ... )
        """
        logger.info(f"Finding similar tasks to: {current_task}")

        query_embedding = create_embedding(current_task, self.embedding_model)

        def _query_tasks():
            with self.driver.session() as session:
                query = """
                MATCH (t:Task)
                WHERE t.status = 'complete'
                RETURN
                    t.id as task_id,
                    t
                ORDER BY t.started_at DESC
                LIMIT 50
                """

                result = session.run(query)

                similar_tasks = []
                for record in result:
                    task = dict(record['t'])
                    task_description = task.get('user_request', '') or task.get('description', '')

                    if task_description.strip():
                        task_embedding = create_embedding(
                            task_description,
                            self.embedding_model
                        )
                        similarity = cosine_similarity(query_embedding, task_embedding)

                        if similarity > 0.7:  # Relevance threshold
                            similar_tasks.append({
                                'task_id': record['task_id'],
                                'task': task,
                                'similarity': float(similarity),
                                'duration': task.get('duration_seconds', 0),
                                'outcome': task.get('outcome', 'unknown'),
                                'user_request': task_description
                            })

                return similar_tasks

        loop = asyncio.get_event_loop()
        similar_tasks = await loop.run_in_executor(None, _query_tasks)

        # Sort by similarity and return top results
        similar_tasks.sort(key=lambda x: x['similarity'], reverse=True)
        top_tasks = similar_tasks[:limit]

        logger.info(f"Found {len(top_tasks)} similar tasks")
        return top_tasks

    async def get_related_artifacts(
        self,
        artifact_id: str,
        relationship: Optional[str] = None
    ) -> List[Dict]:
        """
        Get artifacts related to a given artifact.

        Args:
            artifact_id: ID of source artifact
            relationship: Optional filter ("REFERENCES", "DEPENDS_ON", "DERIVED_FROM")

        Returns:
            List of related artifacts with relationship information:
            [{
                "artifact_id": "artifact_456",
                "artifact": {...},
                "relationship": "REFERENCES",
                "relationship_data": {...}
            }]

        Example:
            >>> related = await memory.get_related_artifacts(
            ...     artifact_id="sprite_boss_v2",
            ...     relationship="DERIVED_FROM"
            ... )
        """
        logger.info(
            f"Getting related artifacts for '{artifact_id}' "
            f"(relationship={relationship})"
        )

        def _query_related():
            with self.driver.session() as session:
                if relationship:
                    query = f"""
                    MATCH (source:Artifact {{id: $artifact_id}})
                          -[r:{relationship}]-(related:Artifact)
                    RETURN
                        related.id as artifact_id,
                        related,
                        type(r) as rel_type,
                        r
                    """
                else:
                    query = """
                    MATCH (source:Artifact {id: $artifact_id})
                          -[r]-(related:Artifact)
                    RETURN
                        related.id as artifact_id,
                        related,
                        type(r) as rel_type,
                        r
                    """

                result = session.run(query, artifact_id=artifact_id)

                return [
                    {
                        'artifact_id': record['artifact_id'],
                        'artifact': dict(record['related']),
                        'relationship': record['rel_type'],
                        'relationship_data': dict(record['r'])
                    }
                    for record in result
                ]

        loop = asyncio.get_event_loop()
        related_artifacts = await loop.run_in_executor(None, _query_related)

        logger.info(f"Found {len(related_artifacts)} related artifacts")
        return related_artifacts

    async def log_message(
        self,
        message_type: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Log a message to the knowledge graph.

        Args:
            message_type: Type of message ("request", "response", "system", "critique")
            content: Message content
            metadata: Optional additional metadata

        Returns:
            message_id: UUID of created message

        Example:
            >>> message_id = await memory.log_message(
            ...     message_type="request",
            ...     content="Create a boss sprite with fire effects",
            ...     metadata={"priority": "high"}
            ... )
        """
        logger.info(f"Logging {message_type} message for agent '{self.agent_id}'")

        def _create_message():
            with self.driver.session() as session:
                # Create embedding for semantic search
                embedding = create_embedding(content, self.embedding_model)
                embedding_list = embedding_to_list(embedding)

                query = """
                CREATE (m:Message {
                    id: randomUUID(),
                    type: $type,
                    from_agent: $agent_id,
                    content: $content,
                    timestamp: datetime(),
                    embedding: $embedding,
                    metadata: $metadata
                })
                WITH m
                MATCH (agent:Agent {id: $agent_id})
                CREATE (agent)-[:SENT]->(m)
                RETURN m.id as message_id
                """

                result = session.run(
                    query,
                    agent_id=self.agent_id,
                    type=message_type,
                    content=content,
                    embedding=embedding_list,
                    metadata=metadata or {}
                )

                return result.single()['message_id']

        loop = asyncio.get_event_loop()
        message_id = await loop.run_in_executor(None, _create_message)

        logger.info(f"Created message: {message_id}")
        return message_id

    async def create_knowledge(
        self,
        topic: str,
        content: str,
        source: str = "experience",
        confidence: float = 0.8
    ) -> str:
        """
        Create a new knowledge node from learned experience.

        Args:
            topic: Knowledge topic/category (e.g., "sprite_animation")
            content: Knowledge content (e.g., "Use 4-6 frames for walk cycles")
            source: Source of knowledge ("experience", "documentation", "feedback")
            confidence: Confidence level (0.0 to 1.0)

        Returns:
            knowledge_id: UUID of created knowledge node

        Example:
            >>> knowledge_id = await memory.create_knowledge(
            ...     topic="color_palettes",
            ...     content="GB Studio sprites work best with 4-color palettes",
            ...     source="experience",
            ...     confidence=0.9
            ... )
        """
        logger.info(
            f"Creating knowledge for agent '{self.agent_id}': "
            f"topic='{topic}', confidence={confidence}"
        )

        def _create_knowledge():
            with self.driver.session() as session:
                embedding = create_embedding(content, self.embedding_model)
                embedding_list = embedding_to_list(embedding)

                query = """
                CREATE (k:Knowledge {
                    id: randomUUID(),
                    topic: $topic,
                    content: $content,
                    source: $source,
                    confidence: $confidence,
                    last_validated: datetime(),
                    usage_count: 0,
                    embedding: $embedding
                })
                WITH k
                MATCH (agent:Agent {id: $agent_id})
                CREATE (agent)-[:LEARNED {
                    timestamp: datetime(),
                    confidence: $confidence
                }]->(k)
                RETURN k.id as knowledge_id
                """

                result = session.run(
                    query,
                    agent_id=self.agent_id,
                    topic=topic,
                    content=content,
                    source=source,
                    confidence=confidence,
                    embedding=embedding_list
                )

                return result.single()['knowledge_id']

        loop = asyncio.get_event_loop()
        knowledge_id = await loop.run_in_executor(None, _create_knowledge)

        logger.info(f"Created knowledge: {knowledge_id}")
        return knowledge_id

    async def update_knowledge_usage(self, knowledge_id: str):
        """
        Increment usage count when knowledge is accessed.

        Args:
            knowledge_id: ID of knowledge node
        """
        def _update_usage():
            with self.driver.session() as session:
                session.run(
                    """
                    MATCH (k:Knowledge {id: $knowledge_id})
                    SET k.usage_count = k.usage_count + 1,
                        k.last_accessed = datetime()
                    """,
                    knowledge_id=knowledge_id
                )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _update_usage)

    async def get_agent_stats(self) -> Dict:
        """
        Get statistics about agent's memory and activity.

        Returns:
            Dictionary with statistics:
            {
                "total_conversations": 42,
                "total_messages": 350,
                "total_artifacts": 28,
                "total_knowledge": 15,
                "most_common_artifact_type": "sprite",
                "knowledge_topics": ["animation", "color", "design"]
            }
        """
        def _get_stats():
            with self.driver.session() as session:
                query = """
                MATCH (agent:Agent {id: $agent_id})
                OPTIONAL MATCH (agent)-[:PARTICIPATED_IN]->(conv:Conversation)
                OPTIONAL MATCH (agent)-[:SENT]->(msg:Message)
                OPTIONAL MATCH (agent)-[:CREATED]->(art:Artifact)
                OPTIONAL MATCH (agent)-[:LEARNED]->(k:Knowledge)
                RETURN
                    count(DISTINCT conv) as conversations,
                    count(DISTINCT msg) as messages,
                    count(DISTINCT art) as artifacts,
                    count(DISTINCT k) as knowledge,
                    collect(DISTINCT art.type) as artifact_types,
                    collect(DISTINCT k.topic) as knowledge_topics
                """

                result = session.run(query, agent_id=self.agent_id)
                record = result.single()

                artifact_types = [t for t in record['artifact_types'] if t]
                knowledge_topics = [t for t in record['knowledge_topics'] if t]

                most_common_type = None
                if artifact_types:
                    from collections import Counter
                    most_common_type = Counter(artifact_types).most_common(1)[0][0]

                return {
                    'total_conversations': record['conversations'],
                    'total_messages': record['messages'],
                    'total_artifacts': record['artifacts'],
                    'total_knowledge': record['knowledge'],
                    'most_common_artifact_type': most_common_type,
                    'knowledge_topics': knowledge_topics
                }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_stats)


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def main():
        memory = AgentMemory(
            agent_id="art_director",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password123"
        )

        try:
            # Remember conversations
            conversations = await memory.remember_conversation(
                topic="boss sprite design",
                limit=3
            )
            print(f"Found {len(conversations)} relevant conversations")

            # Query knowledge
            knowledge = await memory.query_knowledge(
                topic="sprite animation",
                min_confidence=0.7,
                limit=3
            )
            print(f"Found {len(knowledge)} knowledge items")

            # Get stats
            stats = await memory.get_agent_stats()
            print(f"Agent stats: {stats}")

        finally:
            memory.close()

    asyncio.run(main())
