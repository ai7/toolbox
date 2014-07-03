import sys
import cx_Freeze

# run "python setup.py build" to produce the build package
cx_Freeze.setup(
    name = "qTag Utility",
    version = "1.0",
    description = "qTag Utility",
    executables = [cx_Freeze.Executable("../qtag.py")])
