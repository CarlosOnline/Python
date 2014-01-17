import servicemanager
import os

ConsoleMode = os.environ.get('ConsoleMode', False)
TraceIndent = 0
TraceStack = [True]

TracePID = os.getpid()
class Trace():
    def __init__(self, Module, Message=''):
        if ConsoleMode:
            return
        self.Module = Module
        servicemanager.LogInfoMsg(r'{0}: Enter {1}'.format(Module, Message))
        indented = str(TracePID) + ' ' * (len(TraceStack) * 3) + Module
        fp = open(r'c:\temp\service.log', 'a')
        fp.write(r'{0:<70}: Enter {1}'.format(indented, Message) + '\n')
        fp.close()
        TraceStack.append(Module)

class TraceEnd():
    def __init__(self, Module, Message=''):
        if ConsoleMode:
            return
        TraceStack.pop()
        self.Module = Module
        servicemanager.LogInfoMsg(r'{0}: Exit {1}'.format(Module, Message))
        indented = str(TracePID) + ' ' * (len(TraceStack) * 3) + Module
        fp = open(r'c:\temp\service.log', 'a')
        fp.write(r'{0:<70}: Exit  {1}'.format(indented, Message) + '\n')
        fp.close()

class Msg():
    def __init__(self, Module, Message=''):
        if ConsoleMode:
            return
        servicemanager.LogInfoMsg(r'{0}: {1}'.format(Module, Message))
        indented = str(TracePID) + ' ' * (len(TraceStack) * 3) + Module
        fp = open(r'c:\temp\service.log', 'a')
        fp.write(r'{0:<70}:       {1}'.format(indented, Message) + '\n')
        fp.close()
