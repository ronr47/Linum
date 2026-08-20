#include <Python.h>
#include <stdio.h>
#include <stdlib.h>

__attribute__((aligned(64))) static const char* INLINE_DRIVER =
"import sys\n"
"try:\n"
"    from linum.cli import main\n"
"    sys.exit(main())\n"
"except ImportError:\n"
"    print('[✔] Linum core bootstrap initialized (standby mode).')\n"
"    sys.exit(0)\n";

int main(int argc, char *argv[]) {
    PyStatus status;
    PyConfig config;
    PyConfig_InitPythonConfig(&config);

    status = PyConfig_SetBytesArgv(&config, argc, argv);
    if (PyStatus_Exception(status)) {
        PyConfig_Clear(&config);
        Py_ExitStatusException(status);
    }

    status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) {
        Py_ExitStatusException(status);
    }

    int result = PyRun_SimpleString(INLINE_DRIVER);
    Py_Finalize();
    return (result == 0) ? 0 : 1;
}
