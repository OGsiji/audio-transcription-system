import logging
from datetime import datetime
from typing import Dict, Any


class KafkaMonitorService:
    """
    Singleton health monitoring service for Kafka components
    """

    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize monitoring attributes"""
        self.kafka_broker_connection = False
        self.consumer_status = "Not Started"
        self.producer_status = False
        self.last_successful_message = None
        self.error_count = 0

    def update_kafka_connection(self, connection_status: bool):
        """Update Kafka broker connection status"""
        self.kafka_broker_connection = connection_status

    def update_consumer_status(self, status: str):
        """Update consumer operational status"""
        self.consumer_status = status

    def update_producer_status(self, status: bool):
        """Update producer operational status"""
        self.producer_status = status

    def get_health_status(self) -> Dict[str, Any]:
        """
        Generate comprehensive health status
        """
        return {
            "status": "healthy" if self.kafka_broker_connection else "unhealthy",
            "kafka_broker_connection": self.kafka_broker_connection,
            "last_successful_message": (
                str(self.last_successful_message)
                if self.last_successful_message
                else None
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }
