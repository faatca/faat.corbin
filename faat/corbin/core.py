import json
import logging
import pika

log = logging.getLogger(__name__)


class MessageApp:
    def __init__(self, url, router, name, *, mode="tenacious"):
        self._url = url
        self._router = router
        self._name = name
        self._mode = mode

    def serve(self):
        channel = self._connect()
        queue_name = self._initialize_schema(channel)
        self._process_messages(channel, queue_name)

    def _connect(self):
        log.debug("Connecting to broker")
        params = pika.URLParameters(self._url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        log.debug("Settings QOS")
        channel.basic_qos(prefetch_count=1)
        return channel

    def _initialize_schema(self, channel):
        log.debug("Initializing exchanges, queues, and bindings")
        func = MODES.get(self._mode)
        if func:
            return func(channel, self._name)
        if callable(self._mode):
            # Perhaps they passed in a schema initializing function of their own to use.
            return self._mode(channel, self._name)
        raise ValueError(f"Unknown mode: {self._mode}")

    def _process_messages(self, channel, queue_name):
        log.debug("Processing messages")
        for method, properties, body in channel.consume(queue_name):
            log.debug(f"Processing message: {len(body)} bytes")
            path = properties.headers.get("PATH")
            handler, path_params = self._router.find_handler(path)

            if handler is None:
                log.debug(f"No route found for request, ignoring: {path}")
                channel.basic_ack(method.delivery_tag)
                continue

            request = Request(path, body, path_params)
            try:
                handler(request)
            except Exception:
                log.exception("Failed to handle request")
                log.debug("Sending failure")
                channel.basic_nack(method.delivery_tag, requeue=False)
            else:
                log.debug("Acknowledging success")
                channel.basic_ack(method.delivery_tag)
            log.debug("Finished message")


def initialize_relaxed_schema(channel, name):
    exchange_name = name

    log.debug(f"Initializing exchange: {exchange_name}")
    channel.exchange_declare(exchange=exchange_name, exchange_type="fanout", durable=True)

    log.debug(f"Initializing queue")
    result = channel.queue_declare(queue="", exclusive=True)
    queue_name = result.method.queue
    log.debug(f"Made consumer queue: {queue_name}")

    log.debug("Binding queue")
    channel.queue_bind(exchange=exchange_name, queue=queue_name)
    return queue_name


def initialize_tenacious_schema(channel, name):
    # If the message fails in the main queue, it's dead lettered into the retry queue.
    # After a couple minutes of waiting in the retry queue, the messages drop back into the main
    # exchange for processing.
    exchange_name = name
    retry_exchange_name = name + ".retry"
    queue_name = name + "_q"
    retry_queue_name = name + "_retry_q"

    log.debug(f"Initializing exchange: {exchange_name}")
    channel.exchange_declare(exchange=exchange_name, exchange_type="fanout", durable=True)

    log.debug(f"Initializing retry exchange: {retry_exchange_name}")
    channel.exchange_declare(exchange=retry_exchange_name, exchange_type="fanout", durable=True)

    log.debug(f"Initializing queue: {queue_name}")
    channel.queue_declare(
        queue_name,
        durable=True,
        arguments={"x-dead-letter-exchange": retry_exchange_name, "x-queue-mode": "lazy"},
    )

    log.debug(f"Initializing retry queue: {retry_queue_name}")
    channel.queue_declare(
        retry_queue_name,
        durable=True,
        arguments={
            "x-queue-mode": "lazy",
            "x-dead-letter-exchange": exchange_name,
            "x-message-ttl": 2 * 60 * 1000,  # two minutes in milliseconds
        },
    )

    log.debug("Binding queue")
    channel.queue_bind(exchange=exchange_name, queue=queue_name)

    log.debug("Binding retry queue")
    channel.queue_bind(exchange=retry_exchange_name, queue=retry_queue_name)
    return queue_name


def initialize_existing_schema(channel, name):
    return name


MODES = {
    "relaxed": initialize_relaxed_schema,
    "tenacious": initialize_tenacious_schema,
    "existing": initialize_existing_schema,
}


class Request:
    def __init__(self, path, body, path_params):
        self.path = path
        self.body = body
        self.path_params = path_params
        self._json = UNASSIGNED

    def json(self):
        if self._json is UNASSIGNED:
            self._json = json.loads(self.body.decode())
        return self._json


UNASSIGNED = object()
