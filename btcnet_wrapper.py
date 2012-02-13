#Copyright (C) 2011,2012 Colin Rice
#This software is licensed under an included MIT license.
#See the file entitled LICENSE
#If you were not provided with a copy of the license please contact: 
# Colin Rice colin@daedrum.net

from git import Repo
import git.exc
import logging, httplib2, traceback, os.path

def Pull_git():
    try:
        logging.info( 'Trying to initialize btcnet_info repo')
        repo = Repo("btcnet_info")
        try:
            logging.info('Checking if it has been cloned properly')
            repo = repo.clone_from("git://github.com/c00w/btcnet_info.git", 'btcnet_info')
        except git.exc.GitCommandError:
            logging.info('It has been cloned properly')
            
    except git.exc.GitCommandError:
        logging.info( 'Making new btcnet_info repo')
        repo = Repo.init("btcnet_info")
        logging.info('Cloning into it')
        repo = repo.clone_from("git://github.com/c00w/btcnet_info.git", 'btcnet_info')
        try:
            logging.info('Checking if we need to add the origin')
            origin = repo.create_remote('origin', 'git://github.com/c00w/btcnet_info.git')
        except git.exc.GitCommandError:
            logging.info('We do not need to add the origin')
        
    logging.info( 'Updating btcnet_info')
    origin = repo.remotes.origin
    origin.fetch()
    origin.pull('master')
    logging.info( 'Done')
    
def Pull_zip():
    logging.info('Downloading zip archive')
    headers, content = httplib2.Http(disable_ssl_certificate_validation=True).request('https://github.com/c00w/btcnet_info/zipball/master')
    from StringIO import StringIO
    from zipfile import ZipFile
    zipfile = ZipFile(StringIO(content))
    
    logging.info('Extracting zip archive')
    for name in zipfile.namelist():
    
        #Put it in btcnet_info
        dest = name.split('/',1)[1]
        dest = os.path.join('btcnet_info',dest)
        destdir = os.path.dirname(dest)
        if not os.path.isdir(destdir):
          os.makedirs(destdir)
        data = zipfile.read(name)
        if data:
            with open(dest, 'w') as f:
                f.write(data)
            
    with open('.zip', 'w') as f:
        f.write('true')
    
    logging.info('Done')
        
         
    
def Install_btcnet():
    
    if os.path.exists('.zip'):
        try:
            Pull_zip()
        except Exception as error:
            logging.error(traceback.format_exc())
    else:
        try:
            Pull_git()
            import btcnet_info
        except Exception as e:
            logging.error(traceback.format_exc())
            try:
                Pull_zip()
            except Exception as error:
                logging.error(traceback.format_exc())

Install_btcnet()
try:
    import btcnet_info
except ImportError,e :
    logging.error( str(e))
    logging.error( 'Could not install btcnet_info, please report logs online plus python version' )
    import sys
    sys.exit(2)
    btcnet_info = None
