from sane import *

order = []

@recipe()
def recipe_a():
    order.append(0)
    print("I should run first")

@recipe(recipe_deps=[recipe_a])
def recipe_b():
    order.append(1)
    print("I should run after")

sane_run(recipe_b)

assert(order == [0,1])
