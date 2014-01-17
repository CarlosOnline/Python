import platform

if platform.system() == 'Windows':
    import os
    import glob
    import sys

    modules = []
    folder = os.path.dirname(os.path.realpath(__file__))
    fileMask = os.path.join(folder, r'*.py')
    for file in glob.glob(fileMask):
        if os.path.isfile(file):
            [fileName, ext] = os.path.splitext(os.path.basename(file))
            if fileName != '__init__':
                modules.append(fileName)
                pass

    __all__ = modules
    del modules
    del folder
    del fileMask
