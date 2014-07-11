import glob
import os


@given('the destination directory is empty')
def step_impl(context):
    assert os.listdir(os.path.join(context.testdest, "test_host")) == []

@when('I invoke backup without parameters')
def step_impl(context):
    context.call_app("-vv")
    print(context.output)

@then('the program should exit {returncode:d}')
def step_impl(context, returncode):
    assert context.returncode == returncode, context.returncode

@then('the destination directory should contain {n:d} {interval} snapshot')
def step_impl(context, n, interval):
    os.chdir(context.testdest)
    os.chdir("test_host")
    dirs = glob.glob("{}.*".format(interval))
    assert len(dirs) == n, os.listdir()
