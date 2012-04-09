"""
Main command line interface for bitHopper
Parses arguments and start bitHopper up
"""

import bitHopper
import gevent
import argparse
import logging

def parse_config():
    """
    Parses the low level bitHopper configuration
    """
    parser = argparse.ArgumentParser(
                    description='Process bitHopper CommandLine Arguments')
    parser.add_argument('--mine_port', metavar='mp', type=int, 
                    default=8337, help='Mining Port Number')
                   
    parser.add_argument('--config_port', metavar='cp', type=int, 
                    default=8339, help='Configuration Port Number')
                    
    parser.add_argument('--mine_localname', metavar='cp', type=str, 
                    default='', help='Mining IP address to bind to')
                    
    parser.add_argument('--config_localname', metavar='cp', type=str, 
                    default='', help='Configuration IP address to bind to')
                    
    parser.add_argument('--debug', action="store_true", default=False)
                    
    return parser.parse_args()

if __name__ == "__main__":

    args = parse_config()
    
    #Setup debugging output
    bitHopper.setup_logging(logging.DEBUG if args.debug else logging.INFO)
        
    #Setup mining port
    bitHopper.setup_miner(port = args.mine_port, host=args.mine_localname)
    
    #Set up the control website
    bitHopper.setup_control(port = args.config_port, host=args.config_localname)
    
    #Setup Custom Pools
    bitHopper.custom_pools()

    while True:
        gevent.sleep(100)

