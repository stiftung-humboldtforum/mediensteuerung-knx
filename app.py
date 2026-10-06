import asyncio
import os
import ssl

import asyncclick as click
from aiomqtt import MqttError

from api import Api
from knx import KNX
from mqtt_client import Client
from misc import logger


class App:
    def __init__(self, client):
        self.api = Api()
        self.client = client

    async def setup(self):
        # api.get is blocking (requests); fetch off the event loop, then build
        # KNX on the loop (XKNX construction may bind to the running loop).
        response = await asyncio.to_thread(self.api.get, '/api/')
        self.locations = response.json()['locations']
        self.knx = KNX(self.client, self.locations)

    async def start(self):
        await self.knx.start()

    async def reload(self):
        await self.knx.stop()
        await self.setup()
        await self.start()


async def run(ssl_context):
    async with Client(
            os.environ['MQTT_HOSTNAME'],
            identifier='knx',
            port=8883,
            keepalive=60,
            tls_context=ssl_context,
            max_concurrent_outgoing_calls=2000,
    ) as client:
        await client.subscribe('api/data-refresh')
        app = App(client)
        await app.setup()
        await app.start()
        async for message in client.messages:
            if message.topic.matches('api/data-refresh'):
                logger.info('Reload signal received.')
                await app.reload()


@click.command()
@click.option('--ca_certificate', default='/opt/tls/ca_certificate.pem')
@click.option('--client_certificate', default='/opt/tls/client_certificate.pem')
@click.option('--client_key', default='/opt/tls/client_key.pem')
async def main(ca_certificate, client_certificate, client_key):
    ssl_context = ssl.create_default_context(cafile=ca_certificate)
    ssl_context.load_cert_chain(
        client_certificate, client_key)
    # Reconnect with backoff instead of exiting on broker disconnect.
    while True:
        try:
            await run(ssl_context)
        except MqttError as e:
            logger.error('MQTT connection lost (%s); reconnecting in 5s', e)
            await asyncio.sleep(5)


if __name__ == '__main__':
    main()
