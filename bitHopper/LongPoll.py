"""
Simple module that blocks longpoll sockets until we get a longpoll back
"""

from gevent.event import AsyncResult

_event = AsyncResult()

def wait():
    """
    Gets the New Block work unit to send to clients
    """
    return _event.get()

def trigger(work):
    """
    Call to trigger a LP
    """
    global _event
    old = _event
    _event = AsyncResult()
    old.set(work)
