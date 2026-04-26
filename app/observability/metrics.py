from prometheus_client import Counter, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "order_service_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "order_service_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

ORDERS_CREATED_TOTAL = Counter(
    "order_service_orders_created_total",
    "Total orders created",
)

CACHE_HITS_TOTAL = Counter(
    "order_service_cache_hits_total",
    "Total Redis cache hits",
    ["cache_name"],
)

CACHE_MISSES_TOTAL = Counter(
    "order_service_cache_misses_total",
    "Total Redis cache misses",
    ["cache_name"],
)

OUTBOX_EVENTS_PUBLISHED_TOTAL = Counter(
    "order_service_outbox_events_published_total",
    "Total outbox events published",
    ["topic", "event_type"],
)

KAFKA_EVENTS_PROCESSED_TOTAL = Counter(
    "order_service_kafka_events_processed_total",
    "Total Kafka events processed",
    ["topic", "event_type"],
)

KAFKA_EVENTS_SKIPPED_TOTAL = Counter(
    "order_service_kafka_events_skipped_total",
    "Total Kafka events skipped because they were already processed",
    ["topic", "event_type"],
)