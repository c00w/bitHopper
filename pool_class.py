#!/usr/bin/python
#License#
#bitHopper by Colin Rice is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#Based on a work at github.com.

import time

class Pool():
    def __init__(self, name, attribute_dict, bitHopper):
        self.bitHopper = bitHopper
        self.dict = {'index_name':name}
        self._parse(attribute_dict)

    def _parse(self, attribute_dict):
        self['shares'] = int(self.bitHopper.difficulty.btc_difficulty)
        self['ghash'] = -1
        self['duration'] = -2
        self['duration_temporal'] = 0
        self['isDurationEstimated'] = False
        self['last_pulled'] = time.time()
        self['lag'] = False
        self['api_lag'] = False
                
        refresh_limit = self.bitHopper.config.getint('main', 'pool_refreshlimit')
        self['refresh_time'] = int(attribute_dict.get('refresh_time', refresh_limit))
        self['refresh_limit'] = int(attribute_dict.get('refresh_limit', refresh_limit))

        self['rejects'] = self.bitHopper.db.get_rejects(self['index_name'])
        self['user_shares'] = self.bitHopper.db.get_shares(self['index_name'])
        self['payout'] = self.bitHopper.db.get_payout(self['index_name'])
        self['expected_payout'] = self.bitHopper.db.get_expected_payout(self['index_name'])
        self['name'] = attribute_dict.get('name', self[
'index_name'])
        self['wallet'] = attribute_dict.get('wallet', '')
        self['api_address'] = attribute_dict.get('api_address', self['index_name'])
        self['role'] = attribute_dict.get('role', 'disable')
        if self['role'] in ['mine_slush']:
            self['role'] = 'mine_c'
            self['c'] = 300
        self['lp_address'] = attribute_dict.get('lp_address', None)
        self['err_api_count'] = 0
        self['pool_index'] = self['index_name']
        self['default_role'] = self['role']
        if self['default_role'] in ['info','disable']:
            self['default_role'] = 'mine'

        #Pools are now grouped by priority
        self['priority'] = int(attribute_dict.get('priority', 0))

        #Coin Handling
        coin_roles = {'mine': 'btc', 'info': 'btc', 'backup': 'btc', 'backup_latehop': 'btc', 'mine_charity': 'btc', 'mine_c':'btc'}
        for title, coin in self.bitHopper.altercoins.iteritems():
            if coin['short_name'] != 'btc':
                coin_roles[coin['short_name']] = 'mine_' + coin['short_name']
        if 'coin' not in attribute_dict:
            try: coin_type = coin_roles[self['role']]
            except KeyError: coin_type = 'btc'
            self['coin'] = coin_type
        else:
            self['coin'] = attribute_dict['coin']

        #Everything not explicitly handled should be set
        for attr in attribute_dict:
            if attr not in self.dict:
                self.dict[attr] = attribute_dict[attr]

    def __lt__(self, other):
        #Ordering of backup roles
        role_order = {'backup_latehop':0,'backup':1}

        #If the roles are different use the role_order if it exists
        if self['role'] != other['role']:
            if self['role'] in role_order and other['role'] in role_order:
                return role_order[self['role']] < role_order[other['role']]
            
        #backup sorts by reject rate
        if self['role'] in ['backup']:
            rr_self = float(self['rejects'])/(self['user_shares']+1)
            rr_self += self.get('penalty', 0.0)
            rr_other = float(other['rejects'])/(other['user_shares']+1)
            rr_other += other.get('penalty', 0.0)
            return rr_self < rr_other

        #backup latehop sorts purely by shares
        if self['role'] in ['backup_latehop']:
            return self['shares'] < other['shares']


        #disabled pools should never end up in a list
        elif other['role'] in ['disable']:
            return True

        elif self['role'] in ['disable']:
            return False

        else:
            if self['coin'] == other['coin']:
                return self['shares'] < other['shares']
            else:
                self_proff = self.bitHopper.exchange.profitability.get(self['coin'],0)
                other_proff = self.bitHopper.exchange.profitability.get(other['coin'],0)
                return self_proff < other_proff

    def btc_shares(self):
        coin_diffs = {}
        for title, attr_coin in self.bitHopper.altercoins.iteritems():
            coin_diffs[attr_coin['short_name']] = self.bitHopper.difficulty.__dict__[attr_coin['short_name'] + '_difficulty']
        
        if self['coin'] in ['btc']:
            shares = self['shares']
        try: shares = self['shares'] * coin_diffs['btc'] / coin_diffs[self['coin']]
        except KeyError: shares = coin_diffs['btc']

        if self['role'] == 'mine_c':
            #Checks if shares are to high and if so sends it through the roof
            #So we don't mine it.
            try:
                c = float(self['c'])
            except:
                c = 300
            hashrate = float(self['ghash'])
            hopoff = coin_diffs['btc'] * (0.435 - 503131./(1173666 + c*hashrate))
            if shares > hopoff:
                shares = 2*coin_diffs['btc']

        if self['role'] in ['mine_force', 'mine_lp_force']:
            shares = 0
        # apply penalty
        shares = shares * float(self.get('penalty', 1))
        return shares, self

    def is_valid(self):
        if self['lag']:
            return False
        if self['role'] not in ['backup', 'backup_latehop'] and self['api_lag']:
            return False

        try:
            coin_proff = float(self.config.getboolean('main', 'min_coin_proff'))
        except:
            coin_proff = 1.0
        if self.bitHopper.exchange.profitability.get(self['coin'],0) < coin_proff and self['coin'] != 'btc':
            return False
        return True

    def __getitem__(self, key):
        return self.dict[key]

    def get(self, key, default=None):
        if default != None:
            return self.dict.get(key, default)
        else:
            return self.dict.get(key)

    def __setitem__(self, key, value):
        self.dict[key] = value

    def __contains__(self, item):
        return item in self.dict
