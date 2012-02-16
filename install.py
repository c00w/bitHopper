import os
if 'nt' in os.name:
    string = "C:\python27\python.exe setup.py install"
else: 
    string = "python setup.py install"
os.system(string)
