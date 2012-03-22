import gevent.monkey
#Not patching thread so we can spin of db file ops.
gevent.monkey.patch_all(thread=False, time=False)

#Monkey Patch httplib2
#import geventhttpclient.httplib
#geventhttpclient.httplib.patch()
import httplib2

import Logic
import Network
import Website
