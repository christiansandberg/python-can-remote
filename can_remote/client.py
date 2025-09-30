import logging
try:
    import ssl
    # Create SSL context which allows self-signed cerificates
    DEFAULT_SSL_CONTEXT = ssl.create_default_context()
    DEFAULT_SSL_CONTEXT.check_hostname = False
    DEFAULT_SSL_CONTEXT.verify_mode = ssl.CERT_NONE
except ImportError:
    ssl = None
    DEFAULT_SSL_CONTEXT = None
import can
from .protocol import RemoteProtocolBase, RemoteError
from .websocket import WebSocket, WebsocketClosed


logger = logging.getLogger(__name__)


class RemoteBus(can.bus.BusABC):
    """CAN bus over a network connection bridge."""

    def __init__(self, channel, ssl_context=None, **config):
        """
        :param str channel:
            Address of server as ws://host:port/path.
        :param ssl.SSLContext ssl_context:
            SSL context to use for secure connections.
            The default will allow self-signed cerificates.
        """
        url = channel if "://" in channel else "ws://" + channel
        if ssl_context is None:
            ssl_context = DEFAULT_SSL_CONTEXT
        websocket = WebSocket(url, ["can.binary+json.v1", "can.json.v1"],
                              ssl_context=ssl_context)
        self.remote_protocol = RemoteClientProtocol(config, websocket)
        self.socket = websocket.socket
        self.channel_info = self.remote_protocol.channel_info
        self.channel = channel
        super().__init__(channel)

    def fileno(self):
        return self.socket.fileno()

    def recv(self, timeout=None):
        """Block waiting for a message from the Bus.

        :param float timeout: Seconds to wait for a message.

        :return:
            None on timeout or a Message object.
        :rtype: can.Message
        :raises can.interfaces.remote.protocol.RemoteError:
        """
        event = self.remote_protocol.recv(timeout)
        if isinstance(event, can.Message):
            return event
        return None

    def send(self, msg, timeout=None):
        """Transmit a message to CAN bus.

        :param can.Message msg: A Message object.
        """
        self.remote_protocol.send_msg(msg)

    def _send_periodic_internal(
        self,
        msgs,
        period,
        duration = None,
        autostart = True,
        modifier_callback = None,
    ):
        """Start sending a message at a given period on the remote bus."""
        task = CyclicSendTask(self, msgs, period, duration)
        if autostart:
            task.start()
        return task

    def shutdown(self):
        """Close socket connection."""

        if self._is_shutdown:
            logger.debug("%s is already shut down", self.__class__)
            return

        # Give threads a chance to finish up
        logger.debug('Closing connection to server')
        self.remote_protocol.close()
        while True:
            try:
                self.remote_protocol.recv(1)
            except WebsocketClosed:
                break
            except RemoteError:
                pass
        # Shutdown on parent side for proper state 
        # (like _is_shutdown flag must be False when shutdown is finished)
        super().shutdown()
        logger.debug('Network connection closed')


class RemoteClientProtocol(RemoteProtocolBase):

    def __init__(self, config, websocket):
        super(RemoteClientProtocol, self).__init__(websocket)
        self.send_bus_request(config)
        event = self.recv(5)
        if event is None:
            raise RemoteError("No response from server")
        if event.get("type") != "bus_response":
            raise RemoteError("Invalid response from server")
        self.channel_info = '%s on %s' % (
            event["payload"]["channel_info"], websocket.url)

    def send_bus_request(self, config):
        self.send("bus_request", {"config": config})

    def send_periodic_start(self, msg: can.Message, period: float, duration: float):
        msg_payload = {
            "arbitration_id": msg.arbitration_id,
            "is_extended_id": msg.is_extended_id,
            "is_remote_frame": msg.is_remote_frame,
            "is_error_frame": msg.is_error_frame,
            "is_fd": msg.is_fd,
            "bitrate_switch": msg.bitrate_switch,
            "dlc": msg.dlc,
            "data": list(msg.data),
        }
        payload = {
            "period": period,
            "duration": duration,
            "msg": msg_payload
        }
        self.send("periodic_start", payload)

    def send_periodic_stop(self, arbitration_id):
        self.send("periodic_stop", arbitration_id)


class CyclicSendTask(can.broadcastmanager.LimitedDurationCyclicSendTaskABC,
                     can.broadcastmanager.RestartableCyclicTaskABC,
                     can.broadcastmanager.ModifiableCyclicTaskABC):

    def __init__(self, bus, messages, period, duration=None):
        """
        :param bus: The remote connection to use.
        :param message: The message to be sent periodically.
        :param period: The rate in seconds at which to send the message.
        """
        assert isinstance(bus, RemoteBus)
        self.bus = bus
        super(CyclicSendTask, self).__init__(messages, period, duration)

    def start(self):
        for msg in self.messages:
            self.bus.remote_protocol.send_periodic_start(msg,
                                                  self.period,
                                                  self.duration)

    def stop(self):
        for msg in self.messages:
            self.bus.remote_protocol.send_periodic_stop(msg.arbitration_id)

    def modify_data(self, messages):
        self.stop()
        super(self).modify_data(messages)
        for msg in self.messages:
            self.bus.remote_protocol.send_periodic_start(msg,
                                                self.period,
                                                self.duration)
