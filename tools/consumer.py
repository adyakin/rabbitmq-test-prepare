#!/usr/bin/env python3
import pika
import datetime
import json
import time
import sys, os
from pprint import pprint


RMQ_USER="test1"
RMQ_PASS="test"
RMQ_VHOST="test1"

RMQ_HOSTS = {
    "r2": {"host": "10.0.0.4", "working": True},
    "r3": {"host": "10.0.0.6", "working": True},
    "r1": {"host": "10.0.0.11", "working": True}
}

QUEUE_NAME = "py-test-1"
DELAY = 1
serial = 0

def main():
    while(True):
        try:
            chosen_one = list({k: v for k, v in RMQ_HOSTS.items() if v["working"] == True }.keys())[0]
            print(f"connecting to rabbitmq host {RMQ_HOSTS[chosen_one]['host']}")
            rabbitmq_url = pika.URLParameters(f"amqp://{RMQ_USER}:{RMQ_PASS}@{RMQ_HOSTS[chosen_one]['host']}/{RMQ_VHOST}")
            connection = pika.BlockingConnection(rabbitmq_url)
            channel = connection.channel()
            channel.basic_qos(prefetch_count=1)
            channel.queue_declare(queue=QUEUE_NAME,
                                durable = True,
                                auto_delete = False)

            def callback(ch, method, properties, body):
                data = json.loads(body)
                now = time.time()
                elapsed = now - data['time']
                print(f"{chosen_one}: serial: {data['serial']}, elapsed: {elapsed}, from: {data['to']}, msg: {data['message']}")

            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=True)

            print(' [*] Waiting for messages. To exit press CTRL+C')
            channel.start_consuming()

        except IndexError:
            print("No working hosts to continue, stopping")        
            break
        except pika.exceptions.ConnectionClosedByBroker as err:
            print("Connection closed by broker: {}, retrying...".format(err))
            print(f"Marking {chosen_one} as unhealthy.")
            RMQ_HOSTS[chosen_one]["working"] = False
            time.sleep(5)
            continue
        except pika.exceptions.AMQPChannelError as err:
            print("Caught a channel error: {}, stopping...".format(err))
            break
        except pika.exceptions.AMQPConnectionError:
            print("Connection was closed, retrying...")
            print(f"Marking {chosen_one} as unhealthy.")
            RMQ_HOSTS[chosen_one]["working"] = False        
            time.sleep(5)
            continue
        except KeyboardInterrupt:
            print("Keyboard interrupt, aborting")
            connection.close()
            break


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)