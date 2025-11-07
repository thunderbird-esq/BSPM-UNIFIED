#!/usr/bin/env python3
"""
Initialize Memory System for BSPM-UNIFIED Multi-Agent Studio

This script:
1. Connects to Neo4j database
2. Creates necessary indexes and constraints
3. Initializes agent nodes for all 12 agents
4. Seeds initial knowledge base
5. Verifies the setup

Usage:
    python scripts/init_memory.py [--neo4j-uri URI] [--neo4j-user USER] [--neo4j-password PASSWORD]

Environment variables:
    NEO4J_URI: Neo4j connection URI (default: bolt://localhost:7687)
    NEO4J_USER: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password (default: password123)
"""

import argparse
import os
import sys
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, ClientError
import logging
from typing import Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Define the 12 agents across 4 departments
AGENTS = {
    'art': [
        {'id': 'art_director', 'name': 'Art Director', 'role': 'critic'},
        {'id': 'pixel_artist', 'name': 'Pixel Artist', 'role': 'executor'},
        {'id': 'animator', 'name': 'Animator', 'role': 'executor'},
    ],
    'design': [
        {'id': 'game_designer', 'name': 'Game Designer', 'role': 'critic'},
        {'id': 'level_designer', 'name': 'Level Designer', 'role': 'executor'},
        {'id': 'narrative_designer', 'name': 'Narrative Designer', 'role': 'executor'},
    ],
    'audio': [
        {'id': 'audio_director', 'name': 'Audio Director', 'role': 'critic'},
        {'id': 'sound_designer', 'name': 'Sound Designer', 'role': 'executor'},
        {'id': 'composer', 'name': 'Composer', 'role': 'executor'},
    ],
    'code': [
        {'id': 'technical_director', 'name': 'Technical Director', 'role': 'critic'},
        {'id': 'gameplay_programmer', 'name': 'Gameplay Programmer', 'role': 'executor'},
        {'id': 'tools_programmer', 'name': 'Tools Programmer', 'role': 'executor'},
    ]
}


# Initial knowledge base entries
INITIAL_KNOWLEDGE = [
    {
        'topic': 'sprite_design',
        'content': 'GB Studio sprites should use 4-color palettes for best compatibility',
        'confidence': 0.95,
        'source': 'documentation',
        'department': 'art'
    },
    {
        'topic': 'animation',
        'content': 'Character walk cycles work best with 4-6 frames for smooth motion',
        'confidence': 0.9,
        'source': 'experience',
        'department': 'art'
    },
    {
        'topic': 'level_design',
        'content': 'Keep initial levels simple with clear objectives to help players learn',
        'confidence': 0.85,
        'source': 'best_practice',
        'department': 'design'
    },
    {
        'topic': 'audio',
        'content': 'Loop points in background music should be seamless for continuous play',
        'confidence': 0.9,
        'source': 'best_practice',
        'department': 'audio'
    },
    {
        'topic': 'code_optimization',
        'content': 'Minimize script complexity in GB Studio to maintain performance on GB hardware',
        'confidence': 0.95,
        'source': 'documentation',
        'department': 'code'
    }
]


class MemorySystemInitializer:
    """Initialize the Neo4j-based memory system."""

    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize the memory system.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None

    def connect(self) -> bool:
        """
        Connect to Neo4j database.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600
            )
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            logger.info(f"Successfully connected to Neo4j at {self.uri}")
            return True
        except ServiceUnavailable:
            logger.error(f"Could not connect to Neo4j at {self.uri}")
            logger.error("Please ensure Neo4j is running and accessible")
            return False
        except Exception as e:
            logger.error(f"Error connecting to Neo4j: {e}")
            return False

    def close(self):
        """Close database connection."""
        if self.driver:
            self.driver.close()
            logger.info("Closed Neo4j connection")

    def create_constraints(self):
        """Create uniqueness constraints and indexes."""
        logger.info("Creating constraints and indexes...")

        constraints = [
            "CREATE CONSTRAINT agent_id IF NOT EXISTS FOR (a:Agent) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (a:Artifact) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT knowledge_id IF NOT EXISTS FOR (k:Knowledge) REQUIRE k.id IS UNIQUE",
            "CREATE CONSTRAINT conversation_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT message_id IF NOT EXISTS FOR (m:Message) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT decision_id IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX agent_department IF NOT EXISTS FOR (a:Agent) ON (a.department)",
            "CREATE INDEX artifact_type IF NOT EXISTS FOR (a:Artifact) ON (a.type)",
            "CREATE INDEX artifact_status IF NOT EXISTS FOR (a:Artifact) ON (a.status)",
            "CREATE INDEX knowledge_topic IF NOT EXISTS FOR (k:Knowledge) ON (k.topic)",
            "CREATE INDEX knowledge_confidence IF NOT EXISTS FOR (k:Knowledge) ON (k.confidence)",
            "CREATE INDEX task_status IF NOT EXISTS FOR (t:Task) ON (t.status)",
            "CREATE INDEX message_type IF NOT EXISTS FOR (m:Message) ON (m.type)",
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"Created constraint: {constraint.split('FOR')[1].split('REQUIRE')[0].strip()}")
                except ClientError as e:
                    if "already exists" in str(e):
                        logger.debug("Constraint already exists")
                    else:
                        logger.warning(f"Error creating constraint: {e}")

            for index in indexes:
                try:
                    session.run(index)
                    logger.info(f"Created index: {index.split('FOR')[1].split('ON')[0].strip()}")
                except ClientError as e:
                    if "already exists" in str(e):
                        logger.debug("Index already exists")
                    else:
                        logger.warning(f"Error creating index: {e}")

        logger.info("Constraints and indexes created successfully")

    def initialize_agents(self):
        """Create agent nodes for all 12 agents."""
        logger.info("Initializing agent nodes...")

        with self.driver.session() as session:
            for department, agents in AGENTS.items():
                for agent in agents:
                    query = """
                    MERGE (a:Agent {id: $id})
                    ON CREATE SET
                        a.name = $name,
                        a.role = $role,
                        a.department = $department,
                        a.created_at = datetime(),
                        a.updated_at = datetime()
                    ON MATCH SET
                        a.updated_at = datetime()
                    RETURN a.id as agent_id, a.name as name
                    """

                    result = session.run(
                        query,
                        id=agent['id'],
                        name=agent['name'],
                        role=agent['role'],
                        department=department
                    )

                    record = result.single()
                    logger.info(f"Initialized agent: {record['name']} ({record['agent_id']})")

        logger.info(f"Successfully initialized {sum(len(agents) for agents in AGENTS.values())} agents")

    def seed_knowledge(self):
        """Seed initial knowledge base."""
        logger.info("Seeding initial knowledge...")

        with self.driver.session() as session:
            for knowledge in INITIAL_KNOWLEDGE:
                query = """
                CREATE (k:Knowledge {
                    id: randomUUID(),
                    topic: $topic,
                    content: $content,
                    confidence: $confidence,
                    source: $source,
                    last_validated: datetime(),
                    usage_count: 0
                })
                RETURN k.id as knowledge_id, k.topic as topic
                """

                result = session.run(
                    query,
                    topic=knowledge['topic'],
                    content=knowledge['content'],
                    confidence=knowledge['confidence'],
                    source=knowledge['source']
                )

                record = result.single()
                logger.info(f"Created knowledge: {record['topic']} ({record['knowledge_id']})")

        logger.info(f"Successfully seeded {len(INITIAL_KNOWLEDGE)} knowledge entries")

    def create_department_relationships(self):
        """Create relationships between agents in the same department."""
        logger.info("Creating department relationships...")

        with self.driver.session() as session:
            for department, agents in AGENTS.items():
                agent_ids = [agent['id'] for agent in agents]

                query = """
                MATCH (a:Agent)
                WHERE a.id IN $agent_ids
                WITH collect(a) as agents
                UNWIND agents as a1
                UNWIND agents as a2
                WITH a1, a2
                WHERE id(a1) < id(a2)
                MERGE (a1)-[:SAME_DEPARTMENT]->(a2)
                """

                session.run(query, agent_ids=agent_ids)

                logger.info(f"Created relationships for {department} department")

        logger.info("Department relationships created successfully")

    def verify_setup(self) -> Dict:
        """
        Verify the memory system setup.

        Returns:
            Dictionary with verification results
        """
        logger.info("Verifying setup...")

        with self.driver.session() as session:
            # Count agents
            agent_count = session.run("MATCH (a:Agent) RETURN count(a) as count").single()['count']

            # Count knowledge
            knowledge_count = session.run("MATCH (k:Knowledge) RETURN count(k) as count").single()['count']

            # Count relationships
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']

            # Get agent list
            agents = session.run("MATCH (a:Agent) RETURN a.id as id, a.name as name ORDER BY a.id").values()

            results = {
                'agents': agent_count,
                'knowledge': knowledge_count,
                'relationships': rel_count,
                'agent_list': agents
            }

            logger.info("Verification complete:")
            logger.info(f"  - Agents: {agent_count}")
            logger.info(f"  - Knowledge entries: {knowledge_count}")
            logger.info(f"  - Relationships: {rel_count}")

            return results

    def run(self):
        """Run the complete initialization process."""
        logger.info("Starting memory system initialization...")

        if not self.connect():
            logger.error("Failed to connect to Neo4j. Exiting.")
            return False

        try:
            self.create_constraints()
            self.initialize_agents()
            self.seed_knowledge()
            self.create_department_relationships()
            results = self.verify_setup()

            logger.info("=" * 60)
            logger.info("Memory system initialization complete!")
            logger.info("=" * 60)
            logger.info(f"Initialized {results['agents']} agents across 4 departments")
            logger.info(f"Seeded {results['knowledge']} knowledge entries")
            logger.info(f"Created {results['relationships']} relationships")
            logger.info("")
            logger.info("Agent list:")
            for agent_id, agent_name in results['agent_list']:
                logger.info(f"  - {agent_name} ({agent_id})")

            return True

        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            return False

        finally:
            self.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize BSPM-UNIFIED Memory System"
    )
    parser.add_argument(
        '--neo4j-uri',
        default=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        help='Neo4j connection URI (default: bolt://localhost:7687)'
    )
    parser.add_argument(
        '--neo4j-user',
        default=os.getenv('NEO4J_USER', 'neo4j'),
        help='Neo4j username (default: neo4j)'
    )
    parser.add_argument(
        '--neo4j-password',
        default=os.getenv('NEO4J_PASSWORD', 'password123'),
        help='Neo4j password (default: password123)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize the memory system
    initializer = MemorySystemInitializer(
        uri=args.neo4j_uri,
        user=args.neo4j_user,
        password=args.neo4j_password
    )

    success = initializer.run()

    if success:
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Install dependencies: pip install -r backend/requirements.txt")
        logger.info("2. Run tests: pytest tests/test_memory_system.py -v")
        logger.info("3. Start using the memory system in your agents!")
        sys.exit(0)
    else:
        logger.error("Initialization failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
