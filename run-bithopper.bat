echo Going to %~dp0
cd %~dp0
rem With 2>> the program (errors) output is saved at the end of file without
rem  overwrite it each time you open the program
python bitHopper.py --debug 1> logfile.txt 2>> logfile-errors.txt
