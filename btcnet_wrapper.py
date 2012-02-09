from git import Repo
import git.exc
try:
    repo = Repo("btcnet_info")
    try:
        repo = repo.clone_from("git://github.com/c00w/btcnet_info.git", 'btcnet_info')
    except git.exc.GitCommandError:
        pass
except:
    repo = Repo.init("btcnet_info")
    repo = repo.clone_from("git://github.com/c00w/btcnet_info.git", 'btcnet_info')
    try:
        origin = repo.create_remote('origin', 'git://github.com/c00w/btcnet_info.git')
    except git.exc.GitCommandError:
        pass
    
origin = repo.remotes.origin
origin.fetch()
origin.pull('master')

try:
    import btcnet_info
except ImportError:
    print 'Install gitpython! See the readme for detailed instructions'
    import sys
    sys.exit(2)
    btcnet_info = None
