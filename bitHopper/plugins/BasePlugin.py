import traceback, logging

class BasePlugin():
    def __init__(self, bitHopper):
        self.bitHopper = bitHopper
        self.name = __file__

    def isStoppable(self):
        return False

    def start(self):
        pass

    def stop(self):
        pass

    def log_msg(self, msg):
        logging.info(msg, cat=self.name)

    def log_dbg(self, msg):
        logging.debug(msg, cat=self.name)

    def log_trace(self, msg):
        logging.warning(msg, cat=self.name)
