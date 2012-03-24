from flaskext.wtf import Form, TextField, Required, HiddenField

class AddWorkerForm(Form):
    workername = TextField('Worker Name')
    workerpassword = TextField('Worker Password')
    server = HiddenField('Server Name')
    
class DeleteWorkerForm(Form):
    workername = HiddenField('Worker Name')
    workerpassword = HiddenField('Worker Password')
    server = Hiddenfield('Server Name')
    
