from git import Repo
import git.exc
try:
    print 'Trying to initialize btcnet_info repo'
    repo = Repo("btcnet_info")
    try:
        print 'Checking if it has been cloned properly'
        repo = repo.clone_from("git://github.com/c00w/btcnet_info.git", 'btcnet_info')
    except git.exc.GitCommandError:
        print 'It has been cloned properly'
        
except git.exc.GitCommandError:
    print 'Making new btcnet_info repo'
    repo = Repo.init("btcnet_info")
    print 'Cloning into it'
    repo = repo.clone_from("git://github.com/c00w/btcnet_info.git", 'btcnet_info')
    try:
        print 'Checking if we need to add the origin'
        origin = repo.create_remote('origin', 'git://github.com/c00w/btcnet_info.git')
    except git.exc.GitCommandError:
        print 'We do not need to add the origin'
    
print 'Updating btcnet_info'
origin = repo.remotes.origin
origin.fetch()
origin.pull('master')

try:
    import btcnet_info
except ImportError:
    print 'Could not install btcnet_info, please report logs online plus python version'
    print 'manual zipmode not initialized'
    print 'quiting'
    import sys
    sys.exit(2)
    btcnet_info = None
