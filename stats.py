#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import diff
import json

class Statistics():
    def __init__(self,bitHopper):
        self.bitHopper = bitHopper
        self.pool = bitHopper.pool
    def parse_btcguild(self, response, bitHopper):
        info = json.loads(response)
        actual = 0.0
        for item in info['user']:
            actual += float(info['user'][item])
        actual -= float(info['user']['24hour_rewards'])

        db_payout = self.bitHopper.data_get_payout('btcg')
        if db_payout < actual:
            self.bitHopper.data_payout('btcg',actual-db_payout)

        shares = 0.0
        for item in info['workers']:
            shares += info['workers'][item]['total_shares']

        db_shares = self.bitHopper.data_get_shares('btcg')
        if db_shares < shares:
            self.bitHopper.data_shares('btcg',shares-db_shares)

        expected = shares/diff.difficulty * 50

        percent = 0
        if expected != 0.0:
            percent = actual/expected * 100
        
        self.bitHopper.log_msg('btcguild efficiency: ' + str(percent) + "%")

    def parse_bitclockers(self, response):
        info = json.loads(response)
        actual = 0.0
        balances  = ['balance', 'estimatedearnings', 'payout']
        for item in balances:
            actual += float(info[item])

        shares = 0.0
        shares += info['totalshares']

        expected = shares/diff.difficulty * 50

        percent = 0
        if expected != 0.0:
            percent = actual/expected * 100

        self.bitHopper.log_msg('bitclockers efficiency: ' + str(percent) + "%")

    def parse_bitp(response, bitHopper):
        info = json.loads(response)
        actual = 0.0
        balances  = ['estimated_reward', 'unconfirmed_balance', 'confirmed_balance']
        for item in balances:
            actual += float(info[item])

        shares = 0.0
        shares += info['shares']

        expected = shares/diff.difficulty * 50

        percent = 0
        if expected != 0.0:
            percent = actual/expected * 100

        self.bitHopper.log_msg('bitp.it efficiency: ' + str(percent) + "%")

    def selectsharesResponse(self, response, args):
        self.bitHopper.log_dbg('Calling api sharesResponse for '+ args)
        func_map= {
            'btcg':self.parse_btcguild,
            'bitclockers':self.parse_bitclockers,
            'bitp':self.parse_bitp}
        func_map[args[0]](response,bitHopper)
        self.bitHopper.server_update()

    def errsharesResponse(self, error, args): 
        
        self.bitHopper.log_msg('Error in user api for ' + str(args))
        self.bitHopper.log_dbg(str(error))

    def update_api_stats(self, ):
        servers = self.bitHopper.pool.get_servers()
        for server in servers:
            if 'user_api_address' in servers[server]:
                if servers[server]['role'] != 'mine':
                    return
                info = servers[server]
                d = work.get(self.bitHopper.json_agent,info['user_api_address'])
                d.addCallback(selectsharesResponse, (server))
                d.addErrback(errsharesResponse, (server))
                d.addErrback(self.bitHopper.log_msg)

    def stats_dump(self, server, stats_file):
        if stats_file != None:
            stats_file.write(self.pool.get_entry(self.pool.get_current())['name'] + " " + str(self.pool.get_entry(self.pool.get_current())['user_shares']) + " " + str(diff.difficulty) + "\n")
