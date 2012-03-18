import traceback
from payouts import Payouts

def main(bitHopper):
    try:
        me = Payouts(bitHopper)
    except Exception, e:
        traceback.print_exc()
