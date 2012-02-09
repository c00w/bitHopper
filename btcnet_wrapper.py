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

try:
    import btcnet_info
except:
    print 'Install pythongit! See the readme for detailed instructions'
    import os
    os._exit(2)
