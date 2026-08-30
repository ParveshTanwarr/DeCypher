from neo4j import GraphDatabase
from app.config import settings

class Neo4jConnection:
    def __init__(self):
        self.driver = None

    def connect(self):
        if not self.driver:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )

    def close(self):
        if self.driver:
            self.driver.close()

    def query(self, cypher_query: str, parameters: dict = None):
        self.connect()
        with self.driver.session() as session:
            result = session.run(cypher_query, parameters or {})
            return [record.data() for record in result]

neo4j_conn = Neo4jConnection()