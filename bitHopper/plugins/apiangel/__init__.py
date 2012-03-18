import traceback
from apiangel import APIAngel

def main(bitHopper):
    try:
        me = APIAngel(bitHopper)
    except Exception, e:
        traceback.print_exc()