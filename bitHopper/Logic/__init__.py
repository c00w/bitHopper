"""
This module contains all of the business logic.
It supplies two functions:
get_server() which returns the name of a server to mine.
lag_server(name) tells the logic module that the server lagged.

It has two external dependencies.
1) btcnet_info via btcnet_wrapper
2) a way to pull getworks for checking if we should delag pools


"""

import LaggingLogic
LLogic = LaggingLogic.Logic()

import ServerLogic
SLogic = ServerLogic.Logic()

import Logic
CLogic = Logic.Logic()

def get_server():
    return CLogic.get_server()
    
def lag(server, user, password):
    return LLogic.lag(server, user, password)
