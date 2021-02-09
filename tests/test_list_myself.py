import subprocess as sp
from sane import *
from random import randint

signature = "Come and see the violence inherent in the system. Help! Help! I’m being repressed!"

@recipe(info=signature)
def info_print():
    # The recipe is not supposed to be ran!
    exit(1)

@recipe()
def list_myself():
    list_process = sp.Popen(
           f"python {__file__} --list",
           stdout=sp.PIPE,
           encoding='utf8',
           shell=True)
    stdout, stderr = list_process.communicate()
    if stderr is not None:
        print(stderr)
        exit(1)
    if list_process.returncode != 0:
        print("Non zero exit code")
        print("Standard output:")
        print(stdout)
        print("Standard error:")
        print(stderr)
        exit(1)
    if stdout is None or not signature in stdout:
        print("Could not find signature... "
                "Is this thing working?")
        print("Signature:")
        print(str(signature))
        print("Standard output:")
        print(stdout)
        print("Standard error:")
        print(stderr)
        exit(1)

sane_run(list_myself)

