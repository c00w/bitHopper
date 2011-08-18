echo Going to %~dp0
cd %~dp0
python bitHopper.py --debug --scheduler OldDefaultScheduler --auth username,password 1> logfile.txt > 2> logfile-errors.txt
