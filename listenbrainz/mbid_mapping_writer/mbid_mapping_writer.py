import json
import pika
import time
import threading

from flask import current_app
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_PLAYING_NOW
from listenbrainz.mbid_mapping_writer.job_queue import MappingJobQueue


class MBIDMappingWriter(threading.Thread):

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app
        self.queue = MappingJobQueue(app)

    def callback(self, channel, method, properties, body):
        # When we receive new listens, add the listens to the priority queue
        listens = json.loads(body)
        self.queue.add_new_listens(listens, delivery_tag)

        # Now check to see if other jobs have completed that we need to ack.
        tags = self.queue.get_completed_delivery_tags()
        for tag in tags:
            channel.basic_ack(delivery_tag=tag)


    def create_and_bind_exchange_and_queue(self, channel, exchange, queue):
        channel.exchange_declare(exchange=exchange, exchange_type='fanout')
        channel.queue_declare(callback=lambda x: None, queue=queue, durable=True)
        channel.queue_bind(callback=lambda x: None, exchange=exchange, queue=queue)

    def on_open_callback(self, channel):
        self.create_and_bind_exchange_and_queue(channel, current_app.config['UNIQUE_EXCHANGE'], current_app.config['UNIQUE_QUEUE'])
        channel.basic_consume(self.callback_listen, queue=current_app.config['UNIQUE_QUEUE'])

    def on_open(self, connection):
        connection.channel(self.on_open_callback)

    def init_rabbitmq_connection(self):
        while True:
            try:
                credentials = pika.PlainCredentials(current_app.config['RABBITMQ_USERNAME'], current_app.config['RABBITMQ_PASSWORD'])
                connection_parameters = pika.ConnectionParameters(
                    host=current_app.config['RABBITMQ_HOST'],
                    port=current_app.config['RABBITMQ_PORT'],
                    virtual_host=current_app.config['RABBITMQ_VHOST'],
                    credentials=credentials,
                )
                self.connection = pika.SelectConnection(parameters=connection_parameters, on_open_callback=self.on_open)
                break
            except Exception as e:
                current_app.logger.error("Error while connecting to RabbitMQ: %s", str(e), exc_info=True)
                time.sleep(3)


    def run(self):

        # start the queue stuffer thread
        self.queue.start()

        with self.app.app_context():
            while True:
                current_app.logger.info("Starting MBID mapping writer...")
                self.init_rabbitmq_connection()
                try:
                    self.connection.ioloop.start()
                except KeyboardInterrupt:
                    self.queue.terminate()
                    current_app.logger.error("Keyboard interrupt!")
                    break
                except Exception as e:
                    current_app.logger.error("Error in MBID Mapping Writer: %s", str(e), exc_info=True)
                    time.sleep(3)
