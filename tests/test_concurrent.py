import sys
from sane import _stateful
from sane import *

# Use 4 threads
_stateful.set_threads(4)

visited = []

def make_push(i):
    @recipe(name=str(i), hooks=['push'])
    def push():
        visited.append(i)

for i in range(10):
    make_push(i)

@recipe(hook_deps=['push'])
def push_all():
    assert all(i in visited for i in range(10))
    print(visited)

sane_run(push_all)
