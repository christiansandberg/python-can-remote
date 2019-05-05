import logging
import json
import struct
from can import CanError, Message

from .websocket import WebSocket, WebsocketClosed


LOGGER = logging.getLogger(__name__)

# Timestamp, arbitration ID, DLC, flags
BINARY_MSG_STRUCT = struct.Struct(">dIBB")
BINARY_MESSAGE_TYPE = 1

IS_EXTENDED_ID = 0x1
IS_REMOTE_FRAME = 0x2
IS_ERROR_FRAME = 0x4
IS_FD = 0x8
IS_BRS = 0x10
IS_ESI = 0x20


class RemoteProtocolBase(object):

    def __init__(self, websocket):
        self._ws = websocket
        self._use_binary = websocket.protocol == "can.binary+json.v1"

    def recv(self, timeout=None):
        try:
            if not self._ws.wait(timeout):
                return None
            data = self._ws.read()
            if isinstance(data, bytearray):
                if data[0] == BINARY_MESSAGE_TYPE:
                    timestamp, arb_id, dlc, flags = \
                        BINARY_MSG_STRUCT.unpack_from(data, 1)
                    return Message(timestamp=timestamp,
                                   arbitration_id=arb_id,
                                   dlc=dlc,
                                   is_extended_id=bool(flags & IS_EXTENDED_ID),
                                   is_remote_frame=bool(flags & IS_REMOTE_FRAME),
                                   is_error_frame=bool(flags & IS_ERROR_FRAME),
                                   is_fd=bool(flags & IS_FD),
                                   bitrate_switch=bool(flags & IS_BRS),
                                   error_state_indicator=bool(flags & IS_ESI),
                                   data=data[15:])
                else:
                    return None
            event = json.loads(data)
            if not isinstance(event, dict):
                raise TypeError("Message is not a dictionary")
            if "type" not in event:
                raise ValueError("Message must contain a 'type' key")
            if event["type"] == "error":
                raise RemoteError(event["payload"])
            if event["type"] == "message":
                return Message(**event["payload"])
        except (ValueError, TypeError, KeyError) as exc:
            LOGGER.warning("An error occurred: %s", exc)
            self.send_error(exc)
            return None
        return event

    def send(self, event_type, payload):
        self._ws.send(json.dumps({"type": event_type, "payload": payload}))

    def send_msg(self, msg):
        if self._use_binary:
            flags = 0
            if msg.is_extended_id:
                flags |= IS_EXTENDED_ID
            if msg.is_remote_frame:
                flags |= IS_REMOTE_FRAME
            if msg.is_error_frame:
                flags |= IS_ERROR_FRAME
            if msg.is_fd:
                flags |= IS_FD
            if msg.bitrate_switch:
                flags |= IS_BRS
            if msg.error_state_indicator:
                flags |= IS_ESI
            data = BINARY_MSG_STRUCT.pack(msg.timestamp,
                                          msg.arbitration_id,
                                          msg.dlc,
                                          flags)
            payload = bytearray([BINARY_MESSAGE_TYPE])
            payload.extend(data)
            payload.extend(msg.data)
            self._ws.send(payload)
        else:
            payload = {
                "timestamp": msg.timestamp,
                "arbitration_id": msg.arbitration_id,
                "is_extended_id": msg.is_extended_id,
                "is_remote_frame": msg.is_remote_frame,
                "is_error_frame": msg.is_error_frame,
                "dlc": msg.dlc,
                "data": list(msg.data),
            }
            if msg.is_fd:
                payload["is_fd"] = True
                payload["bitrate_switch"] = msg.bitrate_switch
                payload["error_state_indicator"] = msg.error_state_indicator
            self.send("message", payload)

    def send_error(self, exc):
        self.send("error", str(exc))

    def close(self):
        self._ws.close()

    def terminate(self, exc):
        self._ws.close(1011, str(exc))


class RemoteError(CanError):
    pass
