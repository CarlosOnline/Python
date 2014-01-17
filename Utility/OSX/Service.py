from Utility.Utility import *

#-------------------------------------------------------------------------------------
# Service base class
#-------------------------------------------------------------------------------------
class Service():
    pass

def Service_Install(cls, name, display_name=None, stay_alive=True):
    raise Exception(__name__)
    pass

def Service_Start(cls, name, display_name=None, stay_alive=True):
    raise Exception(__name__)
    pass

def Service_Stop(Name):
    #raise Exception(__name__)
    pass

def Service_Remove(Name):
    raise Exception(__name__)

def StartService(ServiceClass):
    raise Exception(__name__)

def StopService(DeleteService=True):
    #raise Exception(__name__)
    pass

def DeleteService(DeleteService=True):
    raise Exception(__name__)
