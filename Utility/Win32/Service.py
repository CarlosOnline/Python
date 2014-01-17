import pythoncom
import servicemanager
import socket
import sys
import win32api
import win32event
import win32service
import win32serviceutil
from   os.path import splitext, abspath

from   Utility.Utility import *
import Utility.Win32.Win32Utility as Win32Utility

#-------------------------------------------------------------------------------------
# Service base class
#-------------------------------------------------------------------------------------
class Service(win32serviceutil.ServiceFramework):
    _svc_name_ = 'PyWin32Service'
    _svc_display_name_ = 'Python Win32 Service Base class'

    def __init__(self, *args):
        try:
            SetLogFile(r'[Temp]\Service.[pid].log')

            self.log(r'Service:__init__() [LogFile]')
            _svc_name_ = Globals.ServiceName
            _svc_display_name_ = Globals.ServiceDescription
            Globals.ConsoleEcho = True
            self.LogExceptions = False
            win32serviceutil.ServiceFramework.__init__(self, *args)
            self.log('init: Initializing ServiceFramework for [ServiceName]')
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)

            Globals.Service = self
        except:
            ReportException()

    def log(self, msg):
        Log('Service: ' + msg)
        servicemanager.LogInfoMsg(str(Expand(msg)))

    def eventLog(self, msg):
        servicemanager.LogInfoMsg(msg)
        pass

    def sleep(self, sec):
        win32api.Sleep(sec * 1000, True)

    def LogError(self, msg):
        servicemanager.LogErrorMsg(str(Expand(msg)))

        if self.LogExceptions:
            exception_info = sys.exc_info()
            self.LogError(str(exception_info))
            traceback = exception_info[2]
            self.LogError(str(traceback.tb_frame.f_code))
            for tb in iterate_traceback(traceback):
                self.LogError(str(tb.tb_frame.f_code))

    def SvcDoRun(self):
        self.log(r'Service:SvcDoRun()')
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        try:
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            self.log('SvcDoRun::start [ServiceName]')
            self.start()
            self.log('SvcDoRun::wait [ServiceName]')
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
            self.log('SvcDoRun::done [ServiceName]')
            Win32Utility.SignalActionEvent('RestartService')
        except Exception as ExObj:
            self.LogError('SvcDoRun Exception [ServiceName] : %s' % ExObj)
            self.SvcStop()

    def SvcStop(self):
        try:
            self.log(r'Service:SvcStop')
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.log('Service:SvcStop - stopping [ServiceName]')
            self.stop()
            self.log('Service:SvcStop - stopped [ServiceName]')
            win32event.SetEvent(self.stop_event)
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            Win32Utility.SignalActionEvent('RestartService')
            self.log('Service:SvcStop - Completed [ServiceName]')
            self.log('------------------------------------------------')
        except Exception as ExObj:
            self.LogError('Service:SvcStop Exception [ServiceName] : %s' % ExObj)


    # to be overridden
    def start(self):
        self.log(r'Service:start()')
        pass

    # to be overridden
    def stop(self):
        self.log(r'Service:stop()')
        win32event.SetEvent(self.stop_event)
        pass

def Service_Install(cls, name, display_name=None, stay_alive=True):
    ''' Install a Service

        cls : the class (derived from Service) that implement the Service
        name : Service name
        display_name : the name displayed in the service manager
        stay_alive : Service will stop on logout if False
    '''
    Trace(lex(r'[name] [display_name]'))
    cls._svc_name_ = name
    cls._svc_display_name_ = display_name or name
    try:
        module_path=sys.modules[cls.__module__].__file__
    except AttributeError:
        # maybe py2exe went by
        from sys import executable
        module_path=executable
    module_file = splitext(abspath(module_path))[0]
    cls._svc_reg_class_ = '%s.%s' % (module_file, cls.__name__)
    if stay_alive: win32api.SetConsoleCtrlHandler(lambda x: True, True)
    try:
        args_install = [
            cls._svc_reg_class_,
            cls._svc_name_,
            cls._svc_display_name_,
        ]
        kwargs_install = {
            'startType' : win32service.SERVICE_AUTO_START,
        }

        if Globals.To:
            kwargs_install['userName'] = Globals.To
            kwargs_install['password'] = Utility.Utility.Password.decode(Globals.To, Prompt=True)
        win32serviceutil.InstallService(*args_install, **kwargs_install)
        Log('Install ok')
    except Exception as ExObj:
        LogError('InstallService Exception : %s' % ExObj)
        Log('If fails to login to service as user then need to grant the user "Logon As Service" right')
        Log('   Start+Run service.msc')
        Log('   goto installed service')
        Log('   log in')
        Log('   done')
        ReportException()
        raise

def Service_Start(cls, name, display_name=None, stay_alive=True):
    ''' Start (auto) a Service

        cls : the class (derived from Service) that implement the Service
        name : Service name
        display_name : the name displayed in the service manager
        stay_alive : Service will stop on logout if False
    '''
    Trace(name)
    try:
        cls._svc_name_ = name
        cls._svc_display_name_ = display_name or name
        try:
            module_path=sys.modules[cls.__module__].__file__
        except AttributeError:
            # maybe py2exe went by
            from sys import executable
            module_path=executable
        module_file = splitext(abspath(module_path))[0]
        cls._svc_reg_class_ = '%s.%s' % (module_file, cls.__name__)
        if stay_alive: win32api.SetConsoleCtrlHandler(lambda x: True, True)
        try:
            win32serviceutil.StartService(cls._svc_name_)
            Log('Service: [ServiceName] started: SUCCESS')
        except Exception as ExObj:
            LogError('StartService Exception : %s' % ExObj)
            Log('If fails to login to service as user then need to grant the user "Logon As Service" right')
            Log('   Start+Run service.msc')
            Log('   goto installed service')
            Log('   log in')
            Log('   done')
            #ReportException()
            #raise
    except:
        ReportException()

def Service_Stop(Name):
    Trace(Name)
    try:
        win32serviceutil.StopService(Name)
    except:
        Log('Service_Stop Failed to stop service [Name]')

def Service_Remove(Name):
    Trace(Name)
    try:
        win32serviceutil.RemoveService(Name)
    except:
        Log('Service_Remove Failed to stop service [Name]')

def StartService(ServiceClass):
    Trace(Globals.ServiceName)
    SaveEnvironment()
    Service_Install(ServiceClass, Globals.ServiceName, Globals.ServiceDescription)
    Service_Start(ServiceClass, Globals.ServiceName, Globals.ServiceDescription)

def StopService(DeleteService=True):
    Trace(Globals.ServiceName)
    Service_Stop(Globals.ServiceName)
    if DeleteService:
        Service_Remove(Globals.ServiceName)
    Trace('Complete')

def DeleteService(DeleteService=True):
    Trace(Globals.ServiceName)
    Service_Remove(Globals.ServiceName)

def ctrlHandler(ctrlType):
   return True

if __name__ == '__main__':
   win32api.SetConsoleCtrlHandler(ctrlHandler, True)
   win32serviceutil.HandleCommandLine(aservice)