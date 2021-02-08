from sane import *

@recipe()
def empty():
    print("Hello sane!")

sane_run(empty)
