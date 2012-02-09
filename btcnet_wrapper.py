from git import Repo

try:
    repo = Repo("btcnet_info")
except:
    repo = Repo.init("btcnet_info")
    repo = repo.clone("git://github.com/c00w/btcnet_info.git")
    origin = repo.create_remote('origin', 'git://github.com/c00w/btcnet_info.git')
    
origin = repo.remotes.origin
origin.fetch()
origin.pull('master')

import btcnet_info
