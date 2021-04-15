from sane import *

visited = []

@recipe()
def a():
    visited.append('a')

@recipe()
def b():
    sane_run(a, cli=False)
    visited.append('b')

sane_run(b)

assert visited == ['a', 'b']
