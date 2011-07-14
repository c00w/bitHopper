#License#
#bitHopper by Colin Rice is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import diff
import pool
import bitHopper
import work
import json

def parse_btcguild(response):
    info = json.loads(response)
    actual = 0.0
    for item in info['user']:
        actual += float(info['user'][item])
    actual -= float(info['user']['24hour_rewards'])

    shares = 0.0
    for item in info['workers']:
        shares += info['workers'][item]['total_shares']
    expected = shares/diff.difficulty * 50

    percent = 0
    if expected != 0.0:
        percent = actual/expected * 100
    
    bitHopper.log_msg('btcguild efficiency: ' + str(percent) + "%")

def parse_bitclockers(response):
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

    bitHopper.log_msg('bitclockers efficiency: ' + str(percent) + "%")

def parse_bitp(response):
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

    bitHopper.log_msg('bitp.it efficiency: ' + str(percent) + "%")

def selectsharesResponse(response, args):
    #bitHopper.log_dbg('Calling sharesResponse for '+ args)
    func_map= {
        'btcg':parse_btcguild,
        'bitclockers':parse_bitclockers,
        'bitp':parse_bitp}
    func_map[args](response)
    bitHopper.server_update()

def errsharesResponse(error, args):
    bitHopper.log_msg('Error in user api for ' + str(args))
    bitHopper.log_dbg(str(error))

def update_api_stats():
    servers = pool.get_servers()
    for server in servers:
        if 'user_api_address' in servers[server]:
            info = servers[server]
            d = work.get(bitHopper.json_agent,info['user_api_address'])
            d.addCallback(selectsharesResponse, (server))
            d.addErrback(errsharesResponse, (server))
            d.addErrback(bitHopper.log_msg)

def stats_dump(server, stats_file):
    if stats_file != None:
        stats_file.write(pool.get_entry(pool.get_current())['name'] + " " + str(pool.get_entry(pool.get_current())['user_shares']) + " " + str(diff.difficulty) + "\n")
