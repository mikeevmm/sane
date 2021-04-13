from sane import *

# Use a diamond tree structure
#
#        /-- B --\
#       /         \
#  A ------- C ----\-- D
#       \
#        \-- E
#
# B and E satisfy conditions

visited = []

@recipe(recipe_deps=['b','c','e'])
def a():
    visited.append('a')

@recipe(
        recipe_deps=['d'],
        conditions=[lambda: True])
def b():
    visited.append('b')

@recipe(recipe_deps=['d'])
def c():
    visited.append('c')

@recipe(conditions=[lambda: False])
def d():
    visited.append('d')

@recipe(conditions=[lambda: True])
def e():
    visited.append('e')

sane_run(a)

try:
    assert(visited == ['b', 'e', 'a'])
except AssertionError as e:
    print('Got', visited)
    raise e
