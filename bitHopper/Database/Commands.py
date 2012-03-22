from . import execute

def Create_Table(name, columns):
    """
    Checks for the existance of a table and creates it if it does not exist
    """
    
    column_string = ", ".join(columns)
    sql = 'CREATE TABLE IF NOT EXISTS %s ( %s )' % (name, column_string)
    execute(sql)
