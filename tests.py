import unittest, json, bitHopper, btcnet_info, httplib2, json

import bitHopper
import bitHopper.Logic
import bitHopper.Configuration.Workers
import bitHopper.Configuration.Pools
import bitHopper.Tracking.speed

import gevent

import bitHopper
bitHopper.setup_logging()

class FakePool():
    """Class for faking pool information from btnet"""    
    def __init__(self):
        self.payout_scheme = 'prop'
        self.coin = 'btc'
        self.shares = "123"
        
    def __getitem__(self, key):
        return getattr(self, key, None)   
        
import btcnet_info

class CustomPools(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        import fake_pool
        #fake_pool.initialize()
        gevent.sleep(0)
        import bitHopper.Configuration.Workers
        bitHopper.Configuration.Workers.add('test_pool', 'test', 'test')
        import bitHopper.Configuration.Pools
        #bitHopper.Configuration.Pools.set_priority('test_pool', 1)
        gevent.sleep(0)
        bitHopper.custom_pools()
        gevent.sleep(0)
        bitHopper.Logic.ServerLogic.rebuild_servers()
        gevent.sleep(0)
        
    def testName(self):
        found = False
        for item in btcnet_info.get_pools():
            if item.name == 'test_pool':
                found = True
        
        self.assertTrue(found)
        
    def testCredentials(Self):
        import bitHopper.Configuration.Workers as Workers
        workers = Workers.get_worker_from('test_pool')
        if not workers:
            assert False
        assert True
        
    
    def testValid(self):
        def test_in_list(list_s, k):
            for item in list_s:
                if item.name == 'test_pool':
                    return True
            return False
    
        from bitHopper.Logic.ServerLogic import filters
        import btcnet_info
        servers = list(btcnet_info.get_pools())
        assert test_in_list(servers, 'origin')
        for filter_f in bitHopper.Logic.ServerLogic.filters:
            servers = list(filter_f(servers))
            assert test_in_list(servers, filter_f)
            
        
    def testAdded(self):
        import bitHopper.Logic.ServerLogic
          
class ServerLogicTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.logic = bitHopper.Logic.ServerLogic
        gevent.sleep(0)

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
        gevent.sleep(0)
        import fake_pool
        fake_pool.initialize()
        gevent.sleep(0)
        import bitHopper.Configuration.Workers
        bitHopper.Configuration.Workers.add('test_pool', 'test', 'test')
        import bitHopper.Configuration.Pools
        bitHopper.Configuration.Pools.set_priority('test_pool', 1)
        gevent.sleep(0)
        bitHopper.custom_pools()
        gevent.sleep(0)
        bitHopper.Logic.ServerLogic.rebuild_servers()
        gevent.sleep(0)
        
        
    def testImport(self):
        self.assertTrue(True)
        
    def testGetWorkers(self):
        self.assertTrue(bitHopper.Logic.get_server() != None)
        
    def testMining(self):
        
        http = httplib2.Http()
        headers = {'Authorization':'Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=='}
        body = json.dumps({'params':[], 'id':1, 'method':'getwork'})
        headers, content = http.request('http://localhost:8337/','POST', body=body, headers=headers)
        try:
            response = json.loads(content) 
        except:
            self.assertFalse(content)
        self.assertTrue('result' in response)
        self.assertTrue('id' in response)
        self.assertTrue('error' in response)
        self.assertTrue(response['error'] == None)
        
    def testSubmit(self):
        http = httplib2.Http()
        headers = {'Authorization':'Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=='}
        body = json.dumps({'params':['0000000141eb2ea2dff39b792c3c4112408b930de8fb7e3aef8a75f400000709000000001d716842411d0488da0d1ccd34e8f3e7d5f0682632efec00b80c7e3f84e175854fb7bead1a09ae0200000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000'], 'id':1, 'method':'getwork'})
        headers, content = http.request('http://localhost:8337/','POST', body=body, headers=headers)
        try:
            response = json.loads(content)
            #print response 
        except:
            self.assertFalse(content)
        self.assertTrue('result' in response)
        self.assertTrue('id' in response)
        self.assertTrue('error' in response)
        self.assertTrue(response['error'] == None)
        self.assertTrue(response['result'] == 'true')
        
    
        
class LongPollingTestCase(unittest.TestCase):
    def testBlocking(self):
        import bitHopper.LongPoll as lp
        import gevent
        def trigger():
            lp.wait()
        gevent.spawn(trigger)
        lp.trigger('Not used right now')
        gevent.sleep(0)
        self.assertTrue(True)
         
                
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
        items = ['/worker', '/', '/miners']
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
        br["username"] = 'test_worker'
        br["password"] = 'test'
        response = br.submit()
        #self.assertTrue(workers.len_workers() > before)
        for pool in workers.workers.keys():
            for username, password in workers.workers[pool]:
                if (username, password) == ('test_worker','test'):
                    workers.remove(pool, username, password)
                    break
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


class MinersTestCase(unittest.TestCase):

    def testnormal(self):
        import bitHopper.Configuration.Miners
        miners = bitHopper.Configuration.Miners
        miners.remove('Test', 'Test')
        a = miners.len_miners()
        miners.add('Test','Test')
        assert miners.len_miners() == a+1
        miners.remove('Test', 'Test')
        assert miners.len_miners() == a   
        
    def testWeb(self):
        miners = bitHopper.Configuration.Miners
        before = miners.len_miners()
        import mechanize
        br = mechanize.Browser()
        br.open('http://localhost:8339/miners')
        br.select_form(name="add")
        br["username"] = 'test'
        br["password"] = 'test'
        response = br.submit()
        #self.assertTrue(workers.len_workers() > before)
        miners.remove('test', 'test')
        self.assertTrue(miners.len_miners() == before)

        
class PoolsTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.pools = bitHopper.Configuration.Pools
        
    def testSetandGet(self):
        
        self.pools.set_priority('test',0)
        self.pools.set_percentage('test', 1)
        per = self.pools.get_percentage('test')
        self.assertEqual(per, 1)
        self.assertTrue(len(list(self.pools.percentage_server()))>0)
        prio = self.pools.get_priority('test')
        self.assertEqual(prio, 0)
        self.pools.set_priority('test',1)
        prio = self.pools.get_priority('test')
        self.assertEqual(prio, 1)
        self.assertTrue(self.pools.len_pools() > 0)
        self.pools.set_priority('test',0)
        self.pools.set_percentage('test', 0)
        prio = self.pools.get_priority('test')
        per = self.pools.get_percentage('test')
        self.assertTrue(prio == per == 0)
        
class TestSpeed(unittest.TestCase):

    def setUp(self):
        self.speed = bitHopper.Tracking.speed.Speed()

    def test_shares_add(self):
        self.speed.add_shares(100)
        self.speed.update_rate(loop=False)
        self.assertTrue(self.speed.get_rate() > 0)
   
    def test_shares_zero(self):
        self.speed.update_rate(loop=False)
        self.assertTrue(self.speed.get_rate() == 0)
        
if __name__ == '__main__':
    unittest.main()
