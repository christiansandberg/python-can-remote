CAN over network bridge for Python
==================================

Creates a CAN over TCP/IP bridge for use with python-can_.


Usage
-----

Start server from command line::

    $ python -m can_remote --interface=virtual --channel=0 --bitrate=500000


Create python-can bus:

.. code-block:: python

    import can
    import can_remote

    # Create a connection to server. Any config is passed to server.
    bus = can_remote.RemoteBus('ws://localhost:54701/', bitrate=500000)

    # Send messages
    msg = can.Message(arbitration_id=0x12345, data=[1,2,3,4,5,6,7,8])
    bus.send(msg)

    # Receive messages
    msg2 = bus.recv(1)
    print(msg2)

    # Disconnect
    bus.shutdown()


.. _python-can: https://python-can.readthedocs.org/en/stable/
