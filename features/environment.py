import os
import os.path
import shutil
import string
import tempfile
import subprocess

def before_all(context):
    def call_app(*args):
        try:
            context.args = ["backup"] + list(args)
            context.output = subprocess.check_output(
                context.args,
                stderr = subprocess.STDOUT,
                universal_newlines=True,
                )
            context.returncode = 0
        except subprocess.CalledProcessError as e:
            context.returncode = e.returncode
            context.output = e.output
    context.call_app = call_app

def before_scenario(context, scenario):
    if "notempfile" in scenario.tags:
        return
    # Generate test data and a config file.
    context.testsource = tempfile.mkdtemp(prefix="backup_testsource_")
    context.testdest = tempfile.mkdtemp(prefix="backup_testdest_")
    n = 5  # Number of files to create.
    for i in range(1, n+1):
        testfilepath = os.path.join(
            context.testsource,
            "testfile_{}_of_{}".format(i, n)
            )
        with open(testfilepath, "w") as testfile:
            testfile.write("content {} of {}".format(i, n))
    configfile = tempfile.mkstemp(prefix="testconfig_", text=True)[1]
    with open(configfile, "w") as fh:
        fh.write(
            "[default]\n"
            "sourcedirs=" + context.testsource + "\n"
            "dest=" + context.testdest + "\n"
            "excludefile=/dev/null\n"
            "filterfile=/dev/null\n"
            "[test_host]\n"
            "hourlies = 2\n"
            "dailies = 2\n"
            "[test_host_2]\n"
             )
    context.configfile = configfile
    os.environ['BACKUP_CONFIGFILE'] = configfile
    os.mkdir(os.path.join(context.testdest, "test_host"))
    os.mkdir(os.path.join(context.testdest, "test_host_2"))
    os.mkdir(os.path.join(context.testdest, "nullhost"))

def after_scenario(context, scenario):
    if "notempfile" in scenario.tags:
        return
    if os.access(context.testsource, os.F_OK):
        shutil.rmtree(context.testsource)
    if os.access(context.testdest, os.F_OK):
        shutil.rmtree(context.testdest)
    os.remove(context.configfile)

def after_step(context, step):
    pass
    #if step.status == "failed":
    #    import pdb
    #    pdb.post_mortem(step.exc_traceback)
