from sane import *

# Test deprecated
@recipe(file_deps=['x.y'], target_files=['z.w'])
def deprecated():
    pass

sane_run(deprecated)

from sane import _Extra as Extra

@recipe(conditions=[Extra.file_condition(sources=['x.y'], targets=['z.w'])])
def correct():
    pass

sane_run(correct)
