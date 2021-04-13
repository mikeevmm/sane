from sane import *

# Use a diamond tree structure
#
#        /---B --\
#       /         \
#  A ------- C ----\-- D --- A
#       \
#        \---E
#

@recipe(recipe_deps=['b','c','e'])
def a():
    raise Exception('Should never run')

@recipe(recipe_deps=['d'])
def b():
    raise Exception('Should never run')

@recipe(recipe_deps=['d'])
def c():
    raise Exception('Should never run')

@recipe(recipe_deps=['a'])
def d():
    raise Exception('Should never run')

@recipe()
def e():
    raise Exception('Should never run')

try:
    sane_run(a)
    raise SystemExit(0)
except SystemExit as err_code:
    if err_code.code != 1:
        exit(1)
