from Queue import Queue
import logging, traceback, gevent, threading, os

try:
    # determine if application is a script file or frozen exe
    if hasattr(sys, 'frozen'):
        DB_DIR = os.path.dirname(sys.executable)
    else:
        DB_DIR = os.path.dirname(os.path.abspath(__file__))
except:
    DB_DIR = os.curdir

DB_FN = os.path.join(DB_DIR, 'bitHopper.db')

__patch = False
def __patch():
    """
    Patch db function
    """
    global __patch
    if not __patch:
        __patch = True
        __setup()

_db_queue = Queue(maxsize = -1)

def __setup():
    """
    Makes a new thread and calls it
    """
    thread = threading.Thread(target=self.__thread)
    thread.daemon = True
    thread.start()
    
def __thread():
    """
    The actual thread that does the writing
    """
    try:
        database = sqlite3.connect(DB_FN, check_same_thread = False)
        curs = database.cursor()
        curs.execute("VACUUM")
        
        while True:
            query, response = _db_queue.get()
            curs.execute(query)
            response.put(curs.fetchall())
            database.commit()
    except:
        logging.error(traceback.format_exc())
    finally:
        curs.close()
        database.commit()
        
def execute(statement):
    """
    Executes a statement without causing file i/o blocking issues
    """
    __patch()
    
    queue = Queue(maxsize = 1)
    _db_queue.put((statement, queue))
    while queue.empty():
        gevent.sleep(0)
    return queue.get()
    
    
