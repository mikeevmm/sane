from sane import *

@recipe()
def test():
    print('Hello world')

sane_run(test)
