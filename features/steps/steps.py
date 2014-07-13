import datetime
import glob
import os


@given('the {dir} directory is empty')
def step_impl(context, dir):
    assert os.listdir(os.path.join(context.testdest, dir)) == []

@when('I invoke backup without parameters')
def step_impl(context):
    context.call_app("-vv")
    print(context.output)

@when("I invoke backup with the arguments \"{args}\"")
def step_impl(context, args):
    context.call_app(*args.split(" "))
    print(context.output)

@then('the program should exit {returncode:d}')
def step_impl(context, returncode):
    assert context.returncode == returncode, context.returncode

@then("I should see \"{text}\"")
def step_impl(context, text):
    assert text in context.output

@then('the {dir} directory should contain {n:d} {interval} snapshots')
def step_impl(context, dir, n, interval):
    cwd = os.getcwd()
    os.chdir(context.testdest)
    os.chdir(dir)
    dirs = glob.glob("{}.*".format(interval))
    assert len(dirs) == n, os.listdir()
    os.chdir(cwd)  # behave is confused if we don't go back.

@then("the {dir} directory should contain no hidden files")
def step_impl(context, dir):
    cwd = os.getcwd()
    os.chdir(context.testdest)
    os.chdir(dir)
    hidden_files = glob.glob(".*")
    assert len(hidden_files) == 0, os.listdir()
    os.chdir(cwd)

@when("the snapshots in {dir} age {n:d} hours")
def step_impl(context, dir, n):
    cwd = os.getcwd()
    os.chdir(context.testdest)
    os.chdir(dir)
    hours = datetime.timedelta(hours=n)
    fmt = "%Y-%m-%dT%H:%M"
    for snapshot in glob.glob("*.*"):
        # Parse the time part, do arithmetic with the time, rename the file.
        interval, timepart = snapshot.split(".")
        try:
            timestamp = datetime.datetime.strptime(timepart, fmt)
        except Exception:
            continue
        timestamp = timestamp - hours
        timepart = timestamp.strftime(fmt)
        os.rename(snapshot, interval+"."+timepart)
    os.chdir(cwd)  # behave is confused if we don't go back.

@then("{host}'s {n:d}{th} {interval} snapshot should contain \"{file}\"")
def step_impl(context, host, n, th, interval, file):
    cwd = os.getcwd()
    os.chdir(context.testdest)
    os.chdir(host)
    dirs = sorted(glob.glob("{}.*".format(interval)), reverse=True)
    assert file in os.listdir(dirs[n-1]), os.listdir(dirs[n-1])
    os.chdir(cwd)
