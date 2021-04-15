from sane import *

# Random keywords
name_keywords = ('astonishing', 'confront', 'dominate', 'destruction', 'frozen')
info_keywords = ('incredible', 'society', 'dry', 'rent', 'loop')

for name, info in zip(name_keywords, info_keywords):
    @recipe(name=name, info=info)
    def dummy():
        raise Exception('Should never run')

# To catch stdout
import io
from contextlib import redirect_stdout

# Fake --list in argv
import sys
sys.argv.append('--list')

f = io.StringIO()
with redirect_stdout(f):
    try:
        sane_run()
    except SystemExit as exit_code:
        if exit_code.code != 0:
            raise Exception(f'Exited with non zero exit code {exit_code}!')
out = f.getvalue()

# Ensure that all keywords are found in out
from itertools import chain
for word in chain(name_keywords, info_keywords):
    if word not in out:
        raise Exception(f'Word \'{word}\' not found in --list output')
