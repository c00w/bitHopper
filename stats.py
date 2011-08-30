#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import json

#NOT CURRENTLY USED AND NOT THREADSAFE

from twisted.internet.task import LoopingCall

class Statistics():
    def __init__(self,bitHopper):
        self.bitHopper = bitHopper
        self.pool = bitHopper.pool
        self.efficiencies = {}
        stats_call = LoopingCall(self.update_api_stats)
        stats_call.start(117*4)

    def update_db_shares(self,server,shares):
        db_shares = self.bitHopper.data_get_shares(server)
        if db_shares < shares:
            self.bitHopper.data_shares(server,shares-db_shares)

    def update_db_payout(self,server,payout):
        db_payout = self.bitHopper.data_get_payout(server)
        if db_payout < payout:
            self.bitHopper.data_payout(server,payout-db_payout)


    def parse_btcguild(self, response, bitHopper):
        info = json.loads(response)
        actual = 0.0
        for item in info['user']:
            actual += float(info['user'][item])
        actual -= float(info['user']['24hour_rewards'])

        self.update_db_payout('btcg',actual)

        shares = 0.0
        for item in info['workers']:
            shares += info['workers'][item]['total_shares']

        self.update_db_shares('btcg',actual)

        expected = shares/self.bitHopper.difficulty.get_difficulty() * 50

        percent = actual/(expected+1) * 100
        
        self.efficiencies['btcg'] = percent

    def parse_bitclockers(self, response,bitHopper):
        info = json.loads(response)
        actual = 0.0
        balances  = ['balance', 'estimatedearnings', 'payout']
        for item in balances:
            actual += float(info[item])

        shares = 0.0
        shares += info['totalshares']

        expected = shares/self.bitHopper.difficulty.get_difficulty() * 50

        percent = actual/(expected+1) * 100

        self.efficiencies['bitclockers'] = percent

    def parse_bitp(self,response, bitHopper):
        info = json.loads(response)
        actual = 0.0
        balances  = ['estimated_reward', 'unconfirmed_balance', 'confirmed_balance']
        for item in balances:
            actual += float(info[item])

        shares = 0.0
        shares += info['shares']

        expected = shares/self.bitHopper.difficulty.get_difficulty() * 50

        percent = 0
        if expected != 0.0:
            percent = actual/expected * 100

        self.bitHopper.log_msg('bitp.it efficiency: ' + str(percent) + "%")

    def parse_mtred(self,response, bitHopper):
        info = json.loads(response)
        actual = 0.0
        actual += info['balance']

    def selectsharesResponse(self, response, args):
        self.bitHopper.log_dbg('Calling api sharesResponse for '+ args)
        func_map= {
            'btcg':self.parse_btcguild,
            'bitclockers':self.parse_bitclockers,
            'bitp':self.parse_bitp,
            #'mtred':self.parse_mtred
            }
        func_map[args](response,self.bitHopper)

    def errsharesResponse(self, error, args): 
        self.bitHopper.log_msg('Error in user api for ' + str(args))
        self.bitHopper.log_dbg(str(error))

    def update_api_stats(self, ):
        return
        servers = self.bitHopper.pool.get_servers()
        for server in servers:
            if 'user_api_address' in servers[server]:
                role = servers[server]['role']
                if role[0:4] == 'mine' or role == 'info' or role == 'api_disable':
                    info = servers[server]
                    d = self.bitHopper.work.get(self.bitHopper.json_agent,info['user_api_address'])
                    d.addCallback(self.selectsharesResponse, (server))
                    d.addErrback(self.errsharesResponse, (server))
                    d.addErrback(self.bitHopper.log_msg)

    def get_efficiency(self,server):
        if server in self.efficiencies:
            return self.efficiencies[server]
        return "NA"

    def stats_dump(self, server, stats_file):
        if stats_file != None:
            stats_file.write(self.pool.get_entry(self.pool.get_current())['name'] + " " + str(self.pool.get_entry(self.pool.get_current())['user_shares']) + " " + str(self.bitHopper.difficulty.get_difficulty()) + "\n")
