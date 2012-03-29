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

    old = self._event
    self._event = event.AsyncResult()
    old.set(work)
