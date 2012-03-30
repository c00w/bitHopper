import bitHopper
import gevent
import argparse
import logging

def parse_config():
    parser = argparse.ArgumentParser(description='Process bitHopper CommandLine Arguments')
    parser.add_argument('--mine_port', metavar='mp', type=int, 
                    default=8337, help='Mining Port Number')
                   
    parser.add_argument('--config_port', metavar='cp', type=int, 
                    default=8339, help='Configuration Port Number')
                    
    parser.add_argument('--mine_localname', metavar='cp', type=str, 
                    default='', help='Dns name to bind to')
                    
    parser.add_argument('--config_localname', metavar='cp', type=str, 
                    default='', help='Dns name to bind to')
                    
    parser.add_argument('--debug', action="store_true", default=False)
                    
    args = parser.parse_args()
    return args
    

if __name__ == "__main__":

    args = parse_config()
    if args.debug:
        bitHopper.setup_logging(logging.DEBUG)
    else:
        bitHopper.setup_logging()
    bitHopper.setup_miner(port = args.mine_port, host=args.mine_localname)
    bitHopper.setup_control(port = args.config_port, host=args.config_localname)

    while True:
        gevent.sleep(100)

