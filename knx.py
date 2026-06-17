import os
import time
from mqtt_client import Client
from xknx import XKNX
from xknx.io import SecureConfig, ConnectionConfig, ConnectionType
from xknx.devices import Device, Switch

from misc import logger

logger.info(f"KNX Gateway IP: {os.environ['KNX_GATEWAY_IP']}")
logger.info(f"KNXKEYS file exists: {os.path.exists(os.environ['KNXKEYS_FILE_PATH'])}")
logger.info(f"KNXKEYS file path: {os.environ['KNXKEYS_FILE_PATH']}")

# Logging für die SecureConfig
secure_config = SecureConfig(
    knxkeys_file_path=os.environ['KNXKEYS_FILE_PATH'],
    knxkeys_password=os.environ['KNXKEYS_PASSWORD']
)
logger.info("SecureConfig created successfully")

# Logging für die ConnectionConfig
connection_config = ConnectionConfig(
    connection_type=ConnectionType.TUNNELING,
    gateway_ip=os.environ['KNX_GATEWAY_IP'],
    secure_config=secure_config,
    local_ip=None
)
logger.info(f"ConnectionConfig created with type: {connection_config.connection_type}")

class KNX:
    def __init__(self, mqtt_client: Client, locations: list[dict]):
        self.mqtt_client = mqtt_client
        self.xknx = XKNX(device_updated_cb=self.device_updated_cb,
                         connection_config=connection_config,
                         daemon_mode=False)
        self.switches: dict[int, Switch] = {}
        self.locations = locations

        for location in locations:
            if 'knx_switch_group_addresses' in location['custom_fields']:
                knx_switch_group_addresses = location['custom_fields']['knx_switch_group_addresses']
                # invert is a parallel newline-separated field; split it the same
                # way (it was read raw and indexed per character -> always False).
                invert_lines = (location['custom_fields'].get(
                    'invert_knx_switch_group_addresses') or '').splitlines()
                if knx_switch_group_addresses:
                    knx_switch_group_addresses = knx_switch_group_addresses.splitlines()
                    for i, address in enumerate(knx_switch_group_addresses):
                        try:
                            invert = invert_lines[i].strip().lower() == 'true'
                        except IndexError:
                            invert = False
                        self.add_switch(location['id'], address, invert)

    def add_switch(self, name, address, invert=False):
        try:
            switch = Switch(self.xknx,
                            name=name,
                            group_address=address,
                            invert=invert)
        except Exception:
            logger.exception(
                'Failed to add switch for location id "%s", group address "%s"',
                name, address)
            # Undo any partial device registration so it can't become a ghost
            # device that later crashes device_updated_cb.
            try:
                self.xknx.devices.remove(str(name))
            except Exception:
                pass
            return
        self.switches[name] = switch
        logger.info(
            'Added switch for location with id "%s", group address "%s", inverted "%s"',
            name, address, invert)

    async def start(self):
        await self.xknx.start()

    async def stop(self):
        await self.xknx.stop()

    async def device_updated_cb(self, device: Device):
        # A failed add_switch can leave a ghost device registered in xknx but
        # absent from self.switches; ignore updates for it instead of KeyError.
        switch = self.switches.get(int(device.name))
        if switch is None:
            return
        logger.info('knx/switch/%s %s',
                    device.name,
                    switch.state)
        state = switch.state
        group_address = str(switch.switch.group_address)
        if state != None:
            await self.mqtt_client.publish_json(f'knx/switch/{device.name}', {'state': state, 'time': int(time.time() * 1000), 'group_address': group_address}, qos=1)
