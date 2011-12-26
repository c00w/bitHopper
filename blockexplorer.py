#License#
# poolblocks.py is created by echiu64 and licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
# http://creativecommons.org/licenses/by-nc-sa/3.0/
# Based on a work at github.com.

import time
import traceback
import urllib2
import re
import logging

def getBlockHashByNumber(bitHopper, blockNumber, max_attempts=5, timeout=30, urlfetch=None):
   logging.debug('getBlockHashByNumber: ' + str(blockNumber), cat='blockexplorer')
    be_url = 'http://blockexplorer.com/b/'+str(blockNumber)
    attempts = 0
    while attempts < max_attempts:
       logging.log(0, 'getBlockHashByNumber attempt: ' + str(attempts), cat='blockexplorer')
        try:
            data = None
            if urlfetch != None:
                data = urlfetch.retrieve(be_url)
            else:
                req = urllib2.Request(be_url)
                response = urllib2.urlopen(req, timeout=timeout)            
                data = response.read()
            re_hash = re.compile('/rawblock/([0-9a-z]+)">')
            match = re_hash.search(data)
           logging.log(0, 'match: ' + str(match))
            if match != None:
               logging.log(0, 'getBlockHashByNumber match found: ' + match.group(1) + ' for ' + str(blockNumber), cat='blockexplorer')
                return match.group(1)
            else:
               logging.info('getBlockHashByNumber: missing hash for ' + str(blockNumber), cat='blockexplorer')
                return None
        except urllib2.HTTPError, error:
            if error.code == 404:
               logging.debug('  404 for ' + str(be_url), cat='blockexplorer')
                attempts += 1
                if attempts < max_attempts:
                    # TODO
                    time.sleep(15)
            else:
               logging.info('  getBlockHashByNumber Error ' + str(error.code) + ' / ' + str(be_url) + ' for ' + str(blockNumber), cat='blockexplorer')
                attempts += 1
                if attempts < max_attempts:
                    # TODO
                    time.sleep(20)
        except Exception, e:
           logging.info('  getBlockHashByNumber Error for ' + str(blockNumber) + ' :: ' + str(e), cat='blockexplorer')
            attempts += 1
            # TODO
            time.sleep(20)
            traceback.print_exc()
        

def getBlockNumberByHash(bitHopper, blockHash, max_attempts=5, timeout=30, urlfetch=None):
   logging.debug('getBlockNumberByHash: ' + str(blockHash), cat='blockexplorer')
    be_url = 'http://blockexplorer.com/block/'+str(blockHash)
    attempts = 0
    while attempts < max_attempts:
        try:
            data = None
            if urlfetch != None:
                data = urlfetch.retrieve(be_url)
            else:
                req = urllib2.Request(be_url)
                response = urllib2.urlopen(req, timeout=timeout)
                data = response.read()
            re_hash = re.compile('blockexplorer.com/b/([0-9]+)')
            match = re_hash.search(data)
            if match != None:
               logging.log(0, 'getBlockNumberByHash match found: ' + match.group(1) + ' for ' + str(blockHash), cat='blockexplorer')
                return match.group(1)
            else:
               logging.info('getBlockNumberByHash: missing number for ' + str(blockHash), cat='blockexplorer')
                return None
        except urllib2.HTTPError, error:
            if error.code == 404:
               logging.debug('  getBlockNumberByHash 404 for ' + str(be_url), cat='blockexplorer')
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(15)
            else:
               logging.info('   getBlockNumberByHash Error ' + str(error.code) + ' / ' + str(be_url) + ' for ' + str(blockHash), cat='blockexplorer')
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(20)
        except Exception, e:
            attempts += 1
            time.sleep(20)
            traceback.print_exc()
            
def getBlockHashAndNumberByTxid(bitHopper, txid, max_attempts=5, timeout=30, urlfetch=None):
    #Appeared in <a href="/block/000000000000066aaeaeaefa00877b061a49dc843ee560f984ac762707d25288">block 144825</a>
   logging.debug('getBlockNumberByTxid ' + str(txid), cat='blockexplorer')
    be_url = 'http://blockexplorer.com/tx/'+str(txid)
    re_block = re.compile('<a href="/block/([\w]+)">block ([0-9]+)</a>')
    attempts = 0
    while attempts < max_attempts:
        try:
            data = None
            if urlfetch != None:
                data = urlfetch.retrieve(be_url)
            else:
                req = urllib2.Request(be_url)
                response = urllib2.urlopen(req, timeout=timeout)
                data = response.read()           
            match = re_block.search(data)
            if match != None:
               logging.log(0, 'getBlockNumberByTxid ' + str(txid) + ' match found: ' + match.group(1) + ' / ' + match.group(2), cat='blockexplorer')
                return match.group(1), match.group(2)
            else:
               logging.info('getBlockNumberByTxid: missing match for ' + str(txid), cat='blockexplorer')
                return None, None
        except urllib2.HTTPError, error:
            attempts += 1
            if error.code == 404:
               logging.debug('  ' + str(attempts) + ' getBlockNumberByTxid 404 for ' + str(txid) + ' / ' + str(be_url), cat='blockexplorer')
                if attempts < max_attempts:
                    time.sleep(15)
            else:
               logging.info('   ' + str(attempts) + ' getBlockNumberByTxid ' + str(txid) + ' Error ' + str(error.code) + ' / ' + str(be_url), cat='blockexplorer')
                if attempts < max_attempts:
                    time.sleep(20)
        except Exception, e:
            attempts += 1
            time.sleep(20)
            traceback.print_exc()
    return None,None
