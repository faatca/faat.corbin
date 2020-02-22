faat.corbin package
====================

This package simplifies the effort required to set up a worker process around RabbitMQ.

This package is compatible with the [faat.granger](https://github.com/faatca/faat.granger) framework, except this package runs synchronously.
It doesn't under asyncio.

It takes a platform independent, but opinionated approach to working with RabbitMQ.
Taking inspiration from modern web frameworks,
it simplifies the development of a worker applications to process messages.


## Installation ##

Install it with your favourite python package installer.

```cmd
py -m venv venv
venv\Scripts\pip install faat.corbin
```

## Getting Started ##

The following example provides a basic look at how this framework can be used.

```python
import argparse
import logging
import os
from time import sleep
from faat.corbin import MessageApp, Router

log = logging.getLogger(__name__)
routes = Router()


def main():
    parser = argparse.ArgumentParser(description="Render letters for a message queue")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )
    logging.getLogger("pika").setLevel(logging.WARNING)

    app = MessageApp(url=os.environ["AMQP_URL"], router=routes, name="greetings", mode="tenacious")
    app.serve()


@routes.route("/reports/welcome-letter/<name>")
def welcome_letter(request):
    name = request.path_params["name"]
    content = f"Hi {name}! Welcome."
    print(content)
    sleep(1)


@routes.route("/reports/dismissal/<id:int>")
def terminate_user(request):
    letter_id = request.path_params["id"]
    data = request.json()
    print(f"-- Letter {letter_id} --")
    print(f"Hi {data['name']}. We are {data['emotion']} to see you go.")
    sleep(1)


@routes.default
def default_route(request):
    log.warning(f"Unrecognized letter request: {request.path} - {request.body}")
    sleep(1)


if __name__ == "__main__":
    main()
```

Post messages to the exchange however, you like.
However, the `PATH` variable should be included as a header on the posted message.

```python
import argparse
import logging
import os
import sys
import pika

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Pushes a message to be processed")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("exchange")
    parser.add_argument("path")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    )
    logging.getLogger("pika").setLevel(logging.WARNING)

    url = os.environ["AMQP_URL"]
    body = sys.stdin.read().encode()

    log.debug("Connecting to broker")
    params = pika.URLParameters(url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    log.debug("Preparing message")
    properties = pika.BasicProperties(headers={"PATH": args.path})

    log.debug("Posting message")
    channel.basic_publish(exchange=args.exchange, routing_key="", body=body, properties=properties)


if __name__ == "__main__":
    main()
```
