import traceback

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
        self.bitHopper.log_msg(msg, cat=self.name)

    def log_dbg(self, msg):
        self.bitHopper.log_dbg(msg, cat=self.name)

    def log_trace(self, msg):
        self.bitHopper.log_trace(msg, cat=self.name)
