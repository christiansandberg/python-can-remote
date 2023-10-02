CAN over network bridge for Python
==================================

Creates a CAN over TCP/IP bridge for use with python-can_.


Installation
------------

Install using pip::

    $ pip install python-can-remote


Usage
-----

Start server from command line::

    $ python -m can_remote --interface=virtual --channel=0 --bitrate=500000


Create python-can bus:

.. code-block:: python

    import can

    # Create a connection to server. Any config is passed to server.
    bus = can.Bus('ws://localhost:54701/',
                  bustype='remote',
                  bitrate=500000,
                  receive_own_messages=True)

    # Send messages
    msg = can.Message(arbitration_id=0x12345, data=[1,2,3,4,5,6,7,8])
    bus.send(msg)

    # Receive messages
    msg2 = bus.recv(1)
    print(msg2)

    # Disconnect
    bus.shutdown()


Web interface
-------------

There is also a basic web interface for inspecting the CAN traffic
using a browser.
It is available on the same address using HTTP, e.g. http://localhost:54701/.


.. _python-can: https://python-can.readthedocs.org/en/stable/

dev 分支改动
------------

这个分支在`master@0.2.1`基础上做了一些修改, 具体改动如下:

1. 启动 `RemoteServer` 后立即打开 `target_bus`, 并从 `target_bus` 中 `recv message`.
2. `recv` 有效 `message` 后, 遍历所有 `connected client list`, 并分发 `message`
3. 当有 `client` 连上后, 放入 `connected client list`
4. `client` 关闭后, 从 `connected client list` 中移除.