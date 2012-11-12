#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact:
# Colin Rice colin@daedrum.net

import gevent, time, logging

class Getwork_Store:
    """
    Class that stores getworks so we can figure out the server again
    """

    def __init__(self):
        self.data = {}
        gevent.spawn(self.prune)

    def add(self, merkle_root, data):
        """
        Adds a merkle_root and a data value
        """
        self.data[merkle_root] = (data, time.time())

    def get(self, merkle_root):
        ""
        if self.data.has_key(merkle_root):
            return self.data[merkle_root][0]
        logging.debug('Merkle Root Not Found %s', merkle_root)
        return None

    def drop_roots(self):
        """
        Resets the merkle_root database
        Very crude.
        Should probably have an invalidate block function instead
        """
        self.data = {}

    def prune(self):
        """
        Running greenlet that prunes old merkle_roots
        """
        while True:
            for key, work in self.data.items():
                if work[1] < (time.time() - (60*20)):
                    del self.data[key]
            gevent.sleep(60)
