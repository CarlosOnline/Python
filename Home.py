import os
import sys

os.environ['ConsoleMode'] = '1'
from Utility.Utility import *
import HomeActions
import InterviewQuestions
import Utility.Actions
import TestActions

#-------------------------------------------------------------------------------------
# Globals
#-------------------------------------------------------------------------------------

Globals.ProgramName = r'Home'
Globals.ProgramDescription = r'Home Program'
Globals.ScriptFolder = os.path.dirname(os.path.realpath(__file__))
Globals.SDXROOT = os.environ.get('SDXROOT', os.path.dirname(os.path.realpath(r'%s\..\\' % (Globals.ScriptFolder))))
Globals.UseMP3 = True
print(Globals.ScriptFolder)
EnsurePath(Path(r'[Temp]'))
SetLogFile(Path(r'[Temp]\[Action].[pid].log'))

#-------------------------------------------------------------------------------------
# Setup
#-------------------------------------------------------------------------------------
def Setup(argv):
    if argv is None:
        argv = sys.argv

    ArgParser.add_arg('Action'         , help='action to take'             , default='', nargs='?')
    ArgParser.add_arg('optionals'      , help='optional arg(s)'            , default=[], nargs='*')
    ArgParser.add_arg('-cls'           , help='clear screen : True/False'  , default=True , required=False, action='store_true', dest='cls')
    ArgParser.add_arg('-SkipCls'       , help='skip clear screen : True/False' , default=False , required=False, action='store_true', dest='SkipCls')
    ArgParser.add_arg('-RunAsService'  , help='run as service : True/False', default=False , required=False, action='store_true', dest='RunAsService')
    ArgParser.add_arg('-Verbose'       , help='Verbose output: True/False' , default=False , required=False, action='store_true', dest='Verbose')
    ArgParser.add_arg('-Terse'         , help='Terse output only: True/False' , default=False , required=False, action='store_true', dest='Terse')
    ArgParser.add_arg('-SkipAutoOpen'  , help='Skips auto open of log files: True/False', default=False , required=False, action='store_true', dest='SkipAutoOpen')
    ArgParser.add_arg('-RepeatInterval', help='Repeat interval b/w re-launching action (Minutes)', default=0 , required=False)
    ArgParser.add_arg('-MediaInfo'     , help='MediaInfo.json file to load', default='MediaInfo.json', nargs='?')
    ArgParser.add_arg('-MediaPrefix'   , help='Prefix for picture & video folders', default='Kai', nargs='?')
    ArgParser.parse()

#-------------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------------
def main(argv=None):
    try:
        Setup(argv)
        Utility.Actions.Actions().Run()

        Log()
        Log(r'LogFile: [LogFile]')
    except:
        ReportException()

    return Globals.ExitCode

if __name__ == "__main__":
    sys.exit(main())
