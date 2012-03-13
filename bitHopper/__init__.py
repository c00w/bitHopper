import gevent.monkey
#Not patching thread so we can spin of db file ops.
gevent.monkey.patch_all(thread=False, time=False)

import Logic
