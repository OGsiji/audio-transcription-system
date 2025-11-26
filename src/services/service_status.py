from datetime import datetime
import threading


class ServiceStatus:
    """
    Thread-safe service status tracking mechanism.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance.startup_time = datetime.now()
                    cls._instance.kafka_connected = False
                    cls._instance.total_messages_processed = 0
                    cls._instance.last_processed_time = None
                    cls._instance.last_error = None
        return cls._instance

    def increment_messages(self):
        """
        Increment message processing count in a thread-safe manner.
        """
        with self._lock:
            self.total_messages_processed += 1
            self.last_processed_time = datetime.now()

    def set_kafka_connection(self, status: bool):
        """
        Update Kafka connection status.
        """
        with self._lock:
            self.kafka_connected = status

    def record_error(self, error: str):
        """
        Record the last encountered error.
        """
        with self._lock:
            self.last_error = error
