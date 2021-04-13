from sane import *

# Use a diamond tree structure
#
#        /---B --\
#       /         \
#  A ------- C ----\--D
#       \
#        \---E
#
# Every recipe is expected to be ran, in
# order D, B, C, E, A

visited = []

@recipe(recipe_deps=['b','c','e'])
def a():
    visited.append('a')

@recipe(recipe_deps=['d'])
def b():
    visited.append('b')

@recipe(recipe_deps=['d'])
def c():
    visited.append('c')

@recipe()
def d():
    visited.append('d')

@recipe()
def e():
    visited.append('e')

sane_run(a)

try:
    assert(visited == ['d', 'b', 'c', 'e', 'a'])
except AssertionError as e:
    print('Got', visited)
    raise e
