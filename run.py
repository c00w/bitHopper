import bitHopper
bitHopper.setup_miner()
bitHopper.setup_control()
import gevent

while True:
    gevent.sleep(100)

