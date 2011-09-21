import traceback

import poolblocks
from poolblocks import PoolBlocks

def main(bitHopper):
    try:
        obj = PoolBlocks(bitHopper)
        return obj
    except:
        traceback.print_exc()
