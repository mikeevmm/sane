from sane import *
import subprocess as sp

@recipe(file_deps=["another_test_file"])
def other():
    sp.run("touch another_test_file", shell=True)
    print("Ran other")

@recipe(recipe_deps=[other], file_deps=["a_test_file"])
def default():
    sp.run("touch a_test_file", shell=True)
    print("Hello sane!")

sane_run(default)
