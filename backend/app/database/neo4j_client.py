import threading
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver
from app.config import settings


class Neo4jConnection:
    def __init__(self):
        self._driver: Optional[Driver] = None
        self._lock = threading.Lock()

    def get_driver(self) -> Driver:
        if self._driver is None:
            with self._lock:
                if self._driver is None:
                    self._driver = GraphDatabase.driver(
                        settings.NEO4J_URI,
                        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                        max_connection_lifetime=30 * 60,
                        max_connection_pool_size=50,
                        connection_acquisition_timeout=30.0,
                    )
        return self._driver

    def close(self):
        with self._lock:
            if self._driver:
                self._driver.close()
                self._driver = None

    def query(self, cypher_query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a managed read transaction with automatic retry on transient errors."""
        driver = self.get_driver()
        with driver.session() as session:
            def _read_tx(tx):
                result = tx.run(cypher_query, parameters or {})
                return [record.data() for record in result]
            return session.execute_read(_read_tx)

    def write(self, cypher_query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a managed write transaction with automatic retry."""
        driver = self.get_driver()
        with driver.session() as session:
            def _write_tx(tx):
                result = tx.run(cypher_query, parameters or {})
                return [record.data() for record in result]
            return session.execute_write(_write_tx)


neo4j_conn = Neo4jConnection()