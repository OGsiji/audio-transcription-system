import json
import logging
from typing import Dict, Any, List
from confluent_kafka import Consumer, Producer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
import os
from src.config.settings import settings
from src.monitoring.health_check import KafkaMonitorService
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider

# Configure logging
environment = settings.NODE_ENV
log_level = logging.DEBUG if environment == "development" else logging.INFO

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Reduce third-party noise
logging.getLogger("kafka").setLevel(logging.WARNING)


class KafkaService:
    """
    Kafka Service with multi-topic support for video classification workflow
    """

    def __init__(self):
        # Initialize monitoring service
        self.monitor = KafkaMonitorService()

        # Define topics for the enhanced video classification workflow
        self.topics = {
            "input": settings.INPUT_TOPIC,  # file-service topic (CircoPost data)
            "safety_output": "classification.safety_check_passed",
            "quality_output": "classification.quality_analysis",
        }

        # Base configuration for both producer and consumer
        self.base_conf = {
            "bootstrap.servers": settings.KAFKA_BROKER,
            "client.id": f"{settings.MICROSERVICE_CLIENTID}_enhanced",
            "client.dns.lookup": "use_all_dns_ips",
            "reconnect.backoff.ms": "1000",
            "reconnect.backoff.max.ms": "10000",
            "retry.backoff.ms": "1000",
        }

        # Configure authentication based on settings
        if settings.KAFKA_SSL:
            if settings.KAFKA_AUTH_TYPE == "SCRAM":
                self.base_conf.update(
                    {
                        "security.protocol": "SASL_SSL",
                        "sasl.mechanism": "SCRAM-SHA-512",
                        "sasl.username": settings.KAFKA_USERNAME,
                        "sasl.password": settings.KAFKA_PASSWORD,
                        "enable.ssl.certificate.verification": settings.KAFKA_AUTH_TYPE
                        == "SCRAM",
                        "log_level": 2,
                    }
                )
            elif settings.KAFKA_AUTH_TYPE == "IAM":

                def oauth_cb(oauth_config):
                    auth_token, expiry_ms = MSKAuthTokenProvider.generate_auth_token(
                        settings.AWS_REGION
                    )
                    return auth_token, expiry_ms / 1000

                self.base_conf.update(
                    {
                        "security.protocol": "SASL_SSL",
                        "sasl.mechanisms": "OAUTHBEARER",
                        "oauth_cb": oauth_cb,
                    }
                )
        else:
            self.base_conf["security.protocol"] = "PLAINTEXT"

        # Enhanced Producer Configuration
        self.producer_conf = self.base_conf.copy()
        self.producer_conf.update(
            {
                "log_level": settings.LOG_LEVEL,
                "acks": "all",  # Wait for all replicas to acknowledge
                "retries": 5,
                "retry.backoff.ms": "1000",
                "enable.idempotence": "true",  # Prevent duplicate messages
                "compression.type": "gzip",  # Compress messages
                "batch.size": 16384,
                "linger.ms": 5,  # Small delay to batch messages
            }
        )

        # Enhanced Consumer Configuration
        self.consumer_conf = self.base_conf.copy()
        self.consumer_conf.update(
            {
                "group.id": f"{settings.MICROSERVICE_GROUPID}_enhanced",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True,
                "auto.commit.interval.ms": 5000,
                "max.poll.interval.ms": 300000,  # 5 minutes max processing time
                "session.timeout.ms": 30000,
                "heartbeat.interval.ms": 3000,
            }
        )

        # Initialize clients
        self.producer = None
        self.consumer = None
        self.admin_client = None

        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize enhanced Kafka clients with error handling"""
        try:
            self.producer = Producer(self.producer_conf)
            self.consumer = Consumer(self.consumer_conf)
            self.admin_client = AdminClient({**self.producer_conf})

            # Test connection
            self.admin_client.poll(3)

            try:
                cluster_metadata = self.admin_client.list_topics(timeout=10)
                logging.info(
                    f"Connected to Kafka cluster with {len(cluster_metadata.topics)} topics"
                )
            except Exception as e:
                logging.error(f"Failed to fetch cluster metadata: {e}")

            # Update monitoring status
            self.monitor.update_kafka_connection(True)
            logging.info("Enhanced Kafka clients initialized successfully")
        except Exception as e:
            self.monitor.update_kafka_connection(False)
            logging.error(f"Failed to initialize Enhanced Kafka clients: {e}")
            raise

    async def create_topics_if_not_exist(self):
        """Create all required topics for the enhanced workflow"""
        try:
            # Define topic configurations
            topic_configs = {
                self.topics["safety_output"]: {
                    "num_partitions": 3,
                    "replication_factor": 1,
                    "config": {
                        "retention.ms": "604800000",  # 7 days
                        "cleanup.policy": "delete",
                    },
                },
                self.topics["quality_output"]: {
                    "num_partitions": 3,
                    "replication_factor": 1,
                    "config": {
                        "retention.ms": "604800000",  # 7 days
                        "cleanup.policy": "delete",
                    },
                },
            }

            new_topics = []
            for topic_name, config in topic_configs.items():
                new_topic = NewTopic(
                    topic_name,
                    num_partitions=config["num_partitions"],
                    replication_factor=config["replication_factor"],
                    config=config.get("config", {}),
                )
                new_topics.append(new_topic)

            # Create topics
            fs = self.admin_client.create_topics(new_topics)

            for topic, f in fs.items():
                try:
                    f.result()
                    logging.info(f"Enhanced topic '{topic}' created successfully")
                except KafkaException as e:
                    if e.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                        logging.info(f"Enhanced topic '{topic}' already exists")
                    else:
                        logging.error(f"Failed to create enhanced topic '{topic}': {e}")

        except Exception as e:
            logging.error(f"Error in enhanced topic creation: {e}")

    async def produce_safety_result(self, data: Dict[str, Any]):
        """Produce safety check and tagging results to safety topic"""
        return await self._produce_message(
            self.topics["safety_output"], data, "safety_result"
        )

    async def produce_quality_result(self, data: Dict[str, Any]):
        """Produce quality and description analysis results to quality topic"""
        return await self._produce_message(
            self.topics["quality_output"], data, "quality_result"
        )

    async def produce(self, topic: str, data: Dict[str, Any]):
        """Generic produce method for backward compatibility"""
        return await self._produce_message(topic, data, "generic")

    async def _produce_message(
        self, topic: str, data: Dict[str, Any], message_type: str
    ):
        """Internal method to produce messages with enhanced error handling and monitoring"""
        try:
            # Ensure topic exists
            await self.create_topics_if_not_exist()

            # Add metadata to message
            enhanced_data = {
                "timestamp": self._get_current_timestamp(),
                "message_type": message_type,
                "service": "enhanced-video-classification",
                "version": "2.0.0",
                "data": data,
            }

            # Convert data to JSON
            data_json = json.dumps(enhanced_data, ensure_ascii=False).encode("utf-8")

            # Add message key based on jobId for partitioning
            message_key = data.get("jobId", "default").encode("utf-8")

            # Produce message with callback
            def delivery_callback(err, msg):
                if err:
                    logging.error(f"Message delivery failed to {topic}: {err}")
                    self.monitor.update_producer_status("Failed")
                else:
                    logging.info(
                        f"Message delivered to {topic} "
                        f"[partition: {msg.partition()}, offset: {msg.offset()}]"
                    )

            self.producer.produce(
                topic=topic,
                key=message_key,
                value=data_json,
                callback=delivery_callback,
            )

            # Flush to ensure delivery
            self.producer.flush(timeout=10)

            logging.info(
                f"Enhanced message produced to topic {topic} for job {data.get('jobId', 'unknown')}"
            )
            return {
                "status": "success",
                "message": f"Message produced to {topic}",
                "jobId": data.get("jobId", "unknown"),
                "timestamp": enhanced_data["timestamp"],
            }

        except Exception as e:
            logging.error(f"Error producing enhanced message to {topic}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "jobId": data.get("jobId", "unknown"),
                "timestamp": self._get_current_timestamp(),
            }

    async def consume(self, topics: List[str], message_handler, stop_event=None):
        """Enhanced consume method with improved error handling and monitoring"""
        try:
            self._subscribe_to_topics(topics)
            await self._consume_messages_enhanced(stop_event, message_handler)
        except Exception as e:
            logging.error(f"Fatal error in enhanced consume method: {e}")
            self.monitor.update_consumer_status("Failed")
        finally:
            self._close_consumer()

    def _subscribe_to_topics(self, topics: List[str]):
        """Subscribe to topics with enhanced logging"""
        self.consumer.subscribe(topics)
        logging.info(f"Enhanced consumer subscribed to topics: {topics}")
        self.monitor.update_consumer_status("Subscribed")

    async def _consume_messages_enhanced(self, stop_event, message_handler):
        """Enhanced message consumption with better error handling and monitoring"""
        consecutive_errors = 0
        max_consecutive_errors = 5

        while stop_event is None or not stop_event.is_set():
            try:
                msg = self.consumer.poll(1.0)

                if msg is None:
                    consecutive_errors = 0  # Reset error count on successful poll
                    continue

                if msg.error():
                    self._handle_message_error_enhanced(msg)
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logging.error(
                            f"Too many consecutive errors ({consecutive_errors}), stopping consumer"
                        )
                        break
                    continue

                # Reset error count on successful message
                consecutive_errors = 0
                await self._process_message_enhanced(msg, message_handler)

            except Exception as e:
                consecutive_errors += 1
                logging.error(f"Unexpected error in message consumption: {e}")

                if consecutive_errors >= max_consecutive_errors:
                    logging.error(
                        f"Too many consecutive errors ({consecutive_errors}), stopping consumer"
                    )
                    break

    def _handle_message_error_enhanced(self, msg):
        """Enhanced message error handling"""
        if msg.error().code() == KafkaError._PARTITION_EOF:
            logging.debug(
                f"Reached end of partition: {msg.topic()}[{msg.partition()}] at offset {msg.offset()}"
            )
        elif msg.error().code() == KafkaError._UNKNOWN_TOPIC_OR_PART:
            logging.error(f"Unknown topic or partition: {msg.error()}")
            self.monitor.update_consumer_status("Topic Error")
        else:
            logging.error(f"Enhanced consumer error: {msg.error()}")
            self.monitor.update_consumer_status("Error")

    async def _process_message_enhanced(self, msg, message_handler):
        """Enhanced message processing with metadata extraction"""
        try:
            # Decode message
            message_data = json.loads(msg.value().decode("utf-8"))

            # Extract metadata if present
            if "data" in message_data and "message_type" in message_data:
                # Enhanced message format
                actual_data = message_data["data"]
                message_type = message_data.get("message_type", "unknown")
                service_version = message_data.get("version", "unknown")

                logging.info(
                    f"Processing enhanced message of type '{message_type}' "
                    f"from service version '{service_version}'"
                )
            else:
                # Legacy message format
                actual_data = message_data
                logging.info("Processing legacy format message")

            # Add message metadata for handler
            actual_data["_kafka_metadata"] = {
                "topic": msg.topic(),
                "partition": msg.partition(),
                "offset": msg.offset(),
                "key": msg.key().decode("utf-8") if msg.key() else None,
                "timestamp": msg.timestamp()[1] if msg.timestamp()[0] == 1 else None,
            }

            # Process message
            await message_handler(actual_data)

            # Update monitoring
            self.monitor.update_consumer_status("Processing")

        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode enhanced message JSON: {e}")
        except Exception as e:
            logging.error(f"Error processing enhanced message: {e}")

    def _close_consumer(self):
        """Enhanced consumer closing with better error handling"""
        try:
            self.consumer.close()
            self.monitor.update_consumer_status("Closed")
            logging.info("Enhanced consumer closed successfully")
        except Exception as e:
            logging.error(f"Error closing enhanced consumer: {e}")

    async def close_consumer(self):
        """Async method to close consumer"""
        try:
            self.consumer.close()
            self.monitor.update_consumer_status("Closed")
            logging.info("Enhanced consumer is closed")
        except Exception as e:
            logging.error(f"Issues closing the enhanced consumer: {e}")

    def get_topics_info(self) -> Dict[str, str]:
        """Get information about configured topics"""
        return {
            "input_topic": self.topics["input"],
            "safety_output_topic": self.topics["safety_output"],
            "quality_output_topic": self.topics["quality_output"],
            "consumer_group": self.consumer_conf.get("group.id"),
            "client_id": self.base_conf.get("client.id"),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get enhanced health status of Kafka service"""
        try:
            # Test producer
            producer_status = "healthy" if self.producer else "unhealthy"

            # Test consumer
            consumer_status = "healthy" if self.consumer else "unhealthy"

            # Test admin client
            admin_status = "healthy"
            try:
                self.admin_client.list_topics(timeout=5)
            except Exception:
                admin_status = "unhealthy"

            return {
                "producer": producer_status,
                "consumer": consumer_status,
                "admin_client": admin_status,
                "topics": self.get_topics_info(),
                "connection": self.monitor.get_health_status().get(
                    "kafka_connection", False
                ),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_current_timestamp(self) -> int:
        """Get current timestamp in milliseconds"""
        import time

        return int(time.time() * 1000)
