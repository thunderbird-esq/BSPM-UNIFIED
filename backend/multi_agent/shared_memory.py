"""
Shared Memory System

Cross-department knowledge sharing for BSPM-UNIFIED.
All 12 agents can query collective memory and learn from each other.
"""

from typing import List, Dict, Optional
from datetime import timedelta
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from sentence_transformers import SentenceTransformer
import logging
import asyncio

from .embeddings import create_embedding, cosine_similarity

logger = logging.getLogger(__name__)


class SharedMemory:
    """
    Cross-department knowledge sharing system.

    All agents can query collective memory to:
    - Access best practices from other departments
    - Cross-reference decisions
    - Identify project bottlenecks
    - Get overall project state
    - Learn from successful patterns

    Example:
        >>> shared = SharedMemory(
        ...     neo4j_uri="bolt://localhost:7687",
        ...     neo4j_user="neo4j",
        ...     neo4j_password="password123"
        ... )
        >>> best_practices = await shared.get_best_practices(
        ...     department="art",
        ...     min_approvals=3
        ... )
        >>> shared.close()
    """

    # Department definitions for BSPM-UNIFIED
    DEPARTMENTS = {
        'art': ['art_director', 'pixel_artist', 'animator'],
        'design': ['game_designer', 'level_designer', 'narrative_designer'],
        'audio': ['audio_director', 'sound_designer', 'composer'],
        'code': ['technical_director', 'gameplay_programmer', 'tools_programmer']
    }

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password123",
        embedding_model: str = 'all-MiniLM-L6-v2'
    ):
        """
        Initialize shared memory system.

        Args:
            neo4j_uri: Neo4j database connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            embedding_model: Sentence transformer model name
        """
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
            logger.info("Connected to Neo4j for shared memory")
        except ServiceUnavailable:
            logger.error(f"Could not connect to Neo4j at {neo4j_uri}")
            raise
        except Exception as e:
            logger.error(f"Error initializing Neo4j driver: {e}")
            raise

        # Load embedding model
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            logger.info(f"Loaded embedding model '{embedding_model}' for shared memory")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.driver:
            self.driver.close()
            logger.info("Closed Neo4j connection for shared memory")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    async def get_best_practices(
        self,
        department: str,
        min_approvals: int = 3,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get best practices from a department.

        Returns patterns that have been successful multiple times.

        Args:
            department: Department name ('art', 'design', 'audio', 'code')
            min_approvals: Minimum number of successful uses
            limit: Maximum practices to return

        Returns:
            List of best practices:
            [{
                "practice_id": "practice_123",
                "title": "4-frame walk cycles",
                "description": "Use 4 frames for character walk animations",
                "approvals": 12,
                "success_rate": 0.95,
                "examples": [...],
                "learned_from": ["art_director", "animator"]
            }]

        Example:
            >>> practices = await shared.get_best_practices(
            ...     department="art",
            ...     min_approvals=5
            ... )
        """
        logger.info(f"Getting best practices for department '{department}'")

        def _query_best_practices():
            with self.driver.session() as session:
                # Get agents in department
                agents = self.DEPARTMENTS.get(department, [])

                query = """
                MATCH (k:Knowledge)
                WHERE k.usage_count >= $min_approvals
                  AND k.confidence >= 0.8
                OPTIONAL MATCH (agent:Agent)-[:LEARNED]->(k)
                WHERE agent.id IN $agents
                WITH k, collect(DISTINCT agent.id) as learned_by, count(agent) as agent_count
                WHERE agent_count > 0
                RETURN
                    k.id as practice_id,
                    k.topic as title,
                    k.content as description,
                    k.usage_count as approvals,
                    k.confidence as success_rate,
                    learned_by
                ORDER BY k.usage_count DESC, k.confidence DESC
                LIMIT $limit
                """

                result = session.run(
                    query,
                    min_approvals=min_approvals,
                    agents=agents,
                    limit=limit
                )

                practices = []
                for record in result:
                    practices.append({
                        'practice_id': record['practice_id'],
                        'title': record['title'],
                        'description': record['description'],
                        'approvals': record['approvals'],
                        'success_rate': float(record['success_rate']),
                        'learned_from': record['learned_by'],
                        'department': department
                    })

                return practices

        loop = asyncio.get_event_loop()
        practices = await loop.run_in_executor(None, _query_best_practices)

        logger.info(f"Found {len(practices)} best practices for '{department}'")
        return practices

    async def cross_reference_decisions(
        self,
        topic: str,
        departments: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find related decisions across multiple departments.

        Uses semantic search to find relevant decisions.

        Args:
            topic: Query string (e.g., "character design")
            departments: Optional list of departments to search
            limit: Maximum decisions to return

        Returns:
            List of decisions:
            [{
                "decision_id": "dec_123",
                "decision": {...},
                "department": "art",
                "made_by": "art_director",
                "similarity": 0.92,
                "impact": "high",
                "timestamp": "2024-01-15T10:30:00"
            }]

        Example:
            >>> decisions = await shared.cross_reference_decisions(
            ...     topic="boss character design",
            ...     departments=["art", "design"]
            ... )
        """
        logger.info(f"Cross-referencing decisions for: {topic}")

        query_embedding = create_embedding(topic, self.embedding_model)

        def _query_decisions():
            with self.driver.session() as session:
                # Build agent filter
                agents_filter = ""
                params = {"limit": limit * 2}  # Get more for semantic filtering

                if departments:
                    all_agents = []
                    for dept in departments:
                        all_agents.extend(self.DEPARTMENTS.get(dept, []))
                    agents_filter = "AND agent.id IN $agents"
                    params["agents"] = all_agents

                query = f"""
                MATCH (agent:Agent)-[:MADE]->(decision:Decision)
                WHERE 1=1 {agents_filter}
                RETURN
                    decision.id as decision_id,
                    decision,
                    agent.id as made_by
                ORDER BY decision.timestamp DESC
                LIMIT $limit
                """

                result = session.run(query, **params)

                decisions = []
                for record in result:
                    decision = dict(record['decision'])
                    decision_text = f"{decision.get('title', '')} {decision.get('description', '')}"

                    if decision_text.strip():
                        decision_embedding = create_embedding(
                            decision_text,
                            self.embedding_model
                        )
                        similarity = cosine_similarity(query_embedding, decision_embedding)

                        # Determine department
                        agent_id = record['made_by']
                        department = None
                        for dept, agents in self.DEPARTMENTS.items():
                            if agent_id in agents:
                                department = dept
                                break

                        decisions.append({
                            'decision_id': record['decision_id'],
                            'decision': decision,
                            'department': department or 'unknown',
                            'made_by': agent_id,
                            'similarity': float(similarity),
                            'impact': decision.get('impact', 'unknown'),
                            'timestamp': str(decision.get('timestamp', ''))
                        })

                return decisions

        loop = asyncio.get_event_loop()
        decisions = await loop.run_in_executor(None, _query_decisions)

        # Sort by similarity and return top results
        decisions.sort(key=lambda x: x['similarity'], reverse=True)
        top_decisions = decisions[:limit]

        logger.info(f"Found {len(top_decisions)} cross-referenced decisions")
        return top_decisions

    async def find_bottlenecks(self, time_range: Optional[timedelta] = None) -> List[Dict]:
        """
        Identify project bottlenecks by analyzing task dependencies.

        Args:
            time_range: Optional time window (default: last 7 days)

        Returns:
            List of bottlenecks:
            [{
                "task_id": "task_123",
                "task": {...},
                "blocked_tasks": 5,
                "waiting_time": 3600,
                "assigned_to": "pixel_artist",
                "priority": "high"
            }]

        Example:
            >>> bottlenecks = await shared.find_bottlenecks(
            ...     time_range=timedelta(days=7)
            ... )
        """
        logger.info("Finding project bottlenecks")

        if time_range is None:
            time_range = timedelta(days=7)

        def _query_bottlenecks():
            with self.driver.session() as session:
                query = """
                MATCH (t:Task)
                WHERE t.status IN ['in_progress', 'pending']
                  AND t.created_at > datetime() - duration($duration)
                OPTIONAL MATCH (blocked:Task)-[:DEPENDS_ON]->(t)
                WHERE blocked.status = 'pending'
                WITH t, count(blocked) as blocked_count
                WHERE blocked_count > 0
                OPTIONAL MATCH (agent:Agent)-[:ASSIGNED_TO]->(t)
                RETURN
                    t.id as task_id,
                    t,
                    blocked_count,
                    agent.id as assigned_to,
                    duration.between(t.created_at, datetime()).seconds as waiting_time
                ORDER BY blocked_count DESC, waiting_time DESC
                LIMIT 20
                """

                params = {
                    "duration": f"P{time_range.days}DT{time_range.seconds}S"
                }

                result = session.run(query, **params)

                bottlenecks = []
                for record in result:
                    task = dict(record['t'])
                    bottlenecks.append({
                        'task_id': record['task_id'],
                        'task': task,
                        'blocked_tasks': record['blocked_count'],
                        'waiting_time': record.get('waiting_time', 0),
                        'assigned_to': record.get('assigned_to', 'unassigned'),
                        'priority': task.get('priority', 'medium'),
                        'title': task.get('title', 'Untitled')
                    })

                return bottlenecks

        loop = asyncio.get_event_loop()
        bottlenecks = await loop.run_in_executor(None, _query_bottlenecks)

        logger.info(f"Found {len(bottlenecks)} bottlenecks")
        return bottlenecks

    async def get_project_state(self) -> Dict:
        """
        Get current state of entire project.

        Returns:
            Project state dictionary:
            {
                "completed_milestones": [{"id": "...", "title": "..."}],
                "active_tasks": [{"id": "...", "title": "...", "status": "..."}],
                "recent_decisions": [...],
                "department_activity": {
                    "art": {"active_tasks": 5, "completed": 12},
                    "design": {"active_tasks": 3, "completed": 8},
                    ...
                },
                "blockers": [...],
                "total_artifacts": 45,
                "knowledge_items": 23
            }

        Example:
            >>> state = await shared.get_project_state()
            >>> print(f"Active tasks: {len(state['active_tasks'])}")
        """
        logger.info("Getting project state")

        def _query_project_state():
            with self.driver.session() as session:
                # Get milestones
                milestones_query = """
                MATCH (m:Milestone)
                WHERE m.status = 'complete'
                RETURN
                    m.id as id,
                    m.title as title,
                    m.completed_at as completed_at
                ORDER BY m.completed_at DESC
                LIMIT 10
                """
                milestones = [
                    {
                        'id': r['id'],
                        'title': r['title'],
                        'completed_at': str(r['completed_at'])
                    }
                    for r in session.run(milestones_query)
                ]

                # Get active tasks
                tasks_query = """
                MATCH (t:Task)
                WHERE t.status IN ['in_progress', 'pending']
                OPTIONAL MATCH (agent:Agent)-[:ASSIGNED_TO]->(t)
                RETURN
                    t.id as id,
                    t.title as title,
                    t.status as status,
                    t.priority as priority,
                    agent.id as assigned_to
                ORDER BY t.priority DESC, t.created_at ASC
                LIMIT 20
                """
                active_tasks = [
                    {
                        'id': r['id'],
                        'title': r['title'],
                        'status': r['status'],
                        'priority': r.get('priority', 'medium'),
                        'assigned_to': r.get('assigned_to', 'unassigned')
                    }
                    for r in session.run(tasks_query)
                ]

                # Get recent decisions
                decisions_query = """
                MATCH (d:Decision)
                OPTIONAL MATCH (agent:Agent)-[:MADE]->(d)
                RETURN
                    d.id as id,
                    d.title as title,
                    d.timestamp as timestamp,
                    agent.id as made_by
                ORDER BY d.timestamp DESC
                LIMIT 5
                """
                recent_decisions = [
                    {
                        'id': r['id'],
                        'title': r['title'],
                        'timestamp': str(r['timestamp']),
                        'made_by': r.get('made_by', 'unknown')
                    }
                    for r in session.run(decisions_query)
                ]

                # Get department activity
                activity_query = """
                MATCH (agent:Agent)-[:ASSIGNED_TO]->(t:Task)
                RETURN
                    agent.id as agent_id,
                    t.status as status,
                    count(t) as task_count
                """
                activity_result = session.run(activity_query)

                department_activity = {dept: {'active_tasks': 0, 'completed': 0}
                                       for dept in self.DEPARTMENTS.keys()}

                for record in activity_result:
                    agent_id = record['agent_id']
                    status = record['status']
                    count = record['task_count']

                    # Find department
                    for dept, agents in self.DEPARTMENTS.items():
                        if agent_id in agents:
                            if status in ['in_progress', 'pending']:
                                department_activity[dept]['active_tasks'] += count
                            elif status == 'complete':
                                department_activity[dept]['completed'] += count
                            break

                # Get artifact and knowledge counts
                counts_query = """
                MATCH (a:Artifact)
                WITH count(a) as artifact_count
                MATCH (k:Knowledge)
                RETURN artifact_count, count(k) as knowledge_count
                """
                counts_result = session.run(counts_query).single()
                total_artifacts = counts_result['artifact_count'] if counts_result else 0
                knowledge_items = counts_result['knowledge_count'] if counts_result else 0

                return {
                    'completed_milestones': milestones,
                    'active_tasks': active_tasks,
                    'recent_decisions': recent_decisions,
                    'department_activity': department_activity,
                    'total_artifacts': total_artifacts,
                    'knowledge_items': knowledge_items
                }

        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(None, _query_project_state)

        # Add blockers from find_bottlenecks
        bottlenecks = await self.find_bottlenecks(timedelta(days=7))
        state['blockers'] = bottlenecks[:5]  # Top 5 blockers

        logger.info("Retrieved project state")
        return state

    async def get_collaboration_patterns(self, limit: int = 10) -> List[Dict]:
        """
        Identify successful collaboration patterns between agents.

        Returns:
            List of collaboration patterns:
            [{
                "agents": ["art_director", "game_designer"],
                "collaboration_count": 15,
                "success_rate": 0.93,
                "common_tasks": ["character design", "level layout"]
            }]
        """
        logger.info("Getting collaboration patterns")

        def _query_patterns():
            with self.driver.session() as session:
                query = """
                MATCH (a1:Agent)-[:COLLABORATED_WITH]-(a2:Agent)
                WHERE id(a1) < id(a2)
                WITH a1, a2, count(*) as collab_count
                OPTIONAL MATCH (a1)-[:WORKED_ON]->(t:Task)<-[:WORKED_ON]-(a2)
                WHERE t.status = 'complete'
                WITH a1, a2, collab_count, count(DISTINCT t) as success_count
                WHERE collab_count > 0
                RETURN
                    a1.id as agent1,
                    a2.id as agent2,
                    collab_count,
                    success_count,
                    toFloat(success_count) / collab_count as success_rate
                ORDER BY collab_count DESC
                LIMIT $limit
                """

                result = session.run(query, limit=limit)

                patterns = []
                for record in result:
                    patterns.append({
                        'agents': [record['agent1'], record['agent2']],
                        'collaboration_count': record['collab_count'],
                        'success_rate': float(record.get('success_rate', 0.0))
                    })

                return patterns

        loop = asyncio.get_event_loop()
        patterns = await loop.run_in_executor(None, _query_patterns)

        logger.info(f"Found {len(patterns)} collaboration patterns")
        return patterns

    async def get_department_knowledge_gaps(self, department: str) -> List[Dict]:
        """
        Identify knowledge gaps in a department by finding topics with:
        - Low confidence scores
        - Few knowledge items
        - Repeated failures

        Args:
            department: Department name

        Returns:
            List of knowledge gaps:
            [{
                "topic": "sprite_shadows",
                "confidence": 0.4,
                "failure_count": 3,
                "needed_by": ["pixel_artist", "animator"]
            }]
        """
        logger.info(f"Identifying knowledge gaps for department '{department}'")

        def _query_gaps():
            with self.driver.session() as session:
                agents = self.DEPARTMENTS.get(department, [])

                query = """
                MATCH (agent:Agent)-[:WORKED_ON]->(t:Task)
                WHERE agent.id IN $agents
                  AND t.status IN ['failed', 'rejected']
                WITH t.topic as topic, count(*) as failure_count,
                     collect(DISTINCT agent.id) as needed_by
                OPTIONAL MATCH (k:Knowledge {topic: topic})
                WITH topic, failure_count, needed_by,
                     avg(k.confidence) as avg_confidence,
                     count(k) as knowledge_count
                WHERE knowledge_count < 3 OR avg_confidence < 0.7
                RETURN
                    topic,
                    coalesce(avg_confidence, 0.0) as confidence,
                    failure_count,
                    needed_by
                ORDER BY failure_count DESC, confidence ASC
                LIMIT 10
                """

                result = session.run(query, agents=agents)

                gaps = []
                for record in result:
                    gaps.append({
                        'topic': record['topic'],
                        'confidence': float(record['confidence']),
                        'failure_count': record['failure_count'],
                        'needed_by': record['needed_by'],
                        'department': department
                    })

                return gaps

        loop = asyncio.get_event_loop()
        gaps = await loop.run_in_executor(None, _query_gaps)

        logger.info(f"Found {len(gaps)} knowledge gaps")
        return gaps

    async def get_trending_topics(
        self,
        time_range: Optional[timedelta] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get trending topics based on recent activity.

        Args:
            time_range: Time window (default: last 7 days)
            limit: Maximum topics to return

        Returns:
            List of trending topics:
            [{
                "topic": "boss_design",
                "activity_count": 25,
                "departments": ["art", "design"],
                "trend": "rising"
            }]
        """
        if time_range is None:
            time_range = timedelta(days=7)

        logger.info("Getting trending topics")

        def _query_trending():
            with self.driver.session() as session:
                query = """
                MATCH (t:Task)
                WHERE t.created_at > datetime() - duration($duration)
                  AND t.topic IS NOT NULL
                WITH t.topic as topic, count(*) as activity_count
                ORDER BY activity_count DESC
                LIMIT $limit
                RETURN topic, activity_count
                """

                params = {
                    "duration": f"P{time_range.days}DT{time_range.seconds}S",
                    "limit": limit
                }

                result = session.run(query, **params)

                trending = []
                for record in result:
                    trending.append({
                        'topic': record['topic'],
                        'activity_count': record['activity_count'],
                        'trend': 'rising'
                    })

                return trending

        loop = asyncio.get_event_loop()
        trending = await loop.run_in_executor(None, _query_trending)

        logger.info(f"Found {len(trending)} trending topics")
        return trending


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def main():
        shared = SharedMemory(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password123"
        )

        try:
            # Get best practices
            practices = await shared.get_best_practices(
                department="art",
                min_approvals=3
            )
            print(f"Found {len(practices)} best practices")

            # Get project state
            state = await shared.get_project_state()
            print(f"Active tasks: {len(state['active_tasks'])}")
            print(f"Total artifacts: {state['total_artifacts']}")

            # Find bottlenecks
            bottlenecks = await shared.find_bottlenecks()
            print(f"Found {len(bottlenecks)} bottlenecks")

        finally:
            shared.close()

    asyncio.run(main())
