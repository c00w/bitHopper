import traceback
from rpcworklog import RPCWorkLog

def main(bitHopper):
    try:
        me = RPCWorkLog(bitHopper)
    except Exception, e:
        traceback.print_exc()