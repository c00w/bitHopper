import unittest, json, bitHopper, btcnet_info
#Logic Module Tests
import bitHopper.Logic
import bitHopper.Configuration.Workers
import gevent

class FakePool():
    """Class for faking pool information from btnet"""    
    def __init__(self):
        self.payout_scheme = 'prop'
        self.coin = 'btc'
        self.shares = "123"
        
    def __getitem__(self, key):
        return getattr(self, key, None)      
            
class ServerLogicTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.logic = bitHopper.Logic.ServerLogic
        gevent.sleep(0.1)

    def testdiff_cutoff(self):
        example = FakePool()
        self.assertEqual(self.logic.difficulty_cutoff(example), 
            float(btcnet_info.get_difficulty(example.coin)) * 0.435)
            
            
    def testvalid_scheme(self):
        a = [FakePool(), FakePool(), FakePool()]
        a[0].payout_scheme = 'pps'
        a[1].payout_scheme = 'smpps'
        a[2].payout_scheme = 'prop'
        a[2].shares = str(10**10)
        
        self.assertEqual(len(list(self.logic.valid_scheme(a))),
            2)
            
    def testfilter_hoppable(self):
        a = [FakePool(), FakePool(), FakePool()]
        a[0].payout_scheme = 'pps'
        a[1].payout_scheme = 'score'
        a[2].payout_scheme = 'prop'
        a[2].shares = str(10**10)
        
        self.assertEqual(len(list(self.logic.filter_hoppable(a))), 2)
        
    def testfilter_secure(self):
    
        a = [FakePool(), FakePool(), FakePool()]
        a[0].payout_scheme = 'pps'
        a[1].payout_scheme = 'score'
        a[2].payout_scheme = 'prop'
        a[2].shares = str(10**10)
        
        self.assertEqual(len(list(self.logic.filter_secure(a))), 1)
        
class UtilTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.util = bitHopper.util
        
    def valid_rpc(self, item, expect):
        #item = json.dumps(item)
        self.assertEqual(self.util.validate_rpc(item), expect)

    def testvalidate(self):
        self.valid_rpc({'hahaha':1}, False)
        self.valid_rpc({'params':[], 'method':'getwork', 'id':1}, True)
        
class MiningTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        import bitHopper
        bitHopper.setup_miner()
        
    def testImport(self):
        self.assertTrue(True)
        
    def testGetWorkers(self):
        import bitHopper.Logic
        self.assertTrue(bitHopper.Logic.get_server() != None)
                
class ControlTestCase(unittest.TestCase):
        
    @classmethod
    def setUpClass(self):
        import bitHopper
        bitHopper.setup_control()
        
    def testImport(self):
        self.assertTrue(True)
        
    def testStatic(self):
        import httplib2
        http = httplib2.Http()
        import os
        items = os.listdir('./bitHopper/static/')
        for item in items:
            headers, content = http.request('http://localhost:8339/static/' + item)
            self.assertTrue('Not Found' not in content)
            
    def testDynamic(self):
        import httplib2
        http = httplib2.Http()
        import os
        items = ['/worker']
        for item in items:
            headers, content = http.request('http://localhost:8339' + item)
            self.assertTrue('Not Found' not in content)
            
    def testWorkers(self):
        workers = bitHopper.Configuration.Workers
        before = workers.len_workers()
        import mechanize
        br = mechanize.Browser()
        br.open('http://localhost:8339/worker')
        br.select_form(name="add")
        br["username"] = 'test'
        br["password"] = 'test'
        response = br.submit()
        #self.assertTrue(workers.len_workers() > before)
        print workers.len_workers(), 'I'
        for a in workers.workers:
            print a
            pool, username, password = a
            if (username, password) == ('test','test'):
                workers.remove(pool, username, password)
                break
        print workers.len_workers()
        self.assertTrue(workers.len_workers() == before)
        
        #Commented out because it doesn't test correctly
        #And it deletes too many workers
        """
        br = mechanize.Browser()
        br.open('http://localhost:8339/worker')
        br.select_form(name="remove")
        response = br.submit()
        print '%s is before %s after remove ' % (before, workers.len_workers())
        
        """
        
class WorkersTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.workers = bitHopper.Configuration.Workers
        
    def testInsertandGet(self):
        
        before = len(self.workers.get_worker_from('test'))
        self.workers.add('test','test','test')
        self.assertTrue(len(self.workers.get_worker_from('test')) > 0)
        self.workers.remove('test','test','test')
        self.assertTrue(len(self.workers.get_worker_from('test')) == before)
        
if __name__ == '__main__':
    unittest.main()
