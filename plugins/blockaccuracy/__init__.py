# block accurracy checking
import time
import eventlet

from eventlet.green import time, threading
from peak.util import plugins

from blockaccuracy import BlockAccuracy

def main(bitHopper):
    obj = BlockAccuracy(bitHopper)
    return obj