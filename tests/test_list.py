from sane import *

# Create recipes that should always be enumerated
list_keywords = ('astonishing', 'confront', 'dominate', 'destruction', 'frozen')
info_keywords = ('incredible', 'society', 'dry', 'rent', 'loop') 
for word, info in zip(list_keywords, info_keywords):
    @recipe(name=word, info=info)
    def dummy():
        raise Exception('Should never run')

# Create recipes that should only be enumerated with --list-all
all_keywords = ('brown', 'agile', 'trend', 'thumb', 'vessel',
                    'abortion', 'electronics')

for word in all_keywords:
    @recipe(name=word)
    def dummy():
        raise Exception('Should never run')

# To catch stdout
import io
from contextlib import redirect_stdout

# Check --list
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

# Ensure that only the recipes with info are found in out
from itertools import chain
for word in chain(list_keywords, info_keywords):
    if word not in out:
        raise Exception(f'Word \'{word}\' not found in --list output')
for word in all_keywords:
    if word in out:
        raise Exception(f'Word \'{word}\' found in --list output, even though '
                'it should only appear for --list-all')

# Now check --list-all
# Fake --list-all in argv
import sys
sys.argv.append('--list-all')

f = io.StringIO()
with redirect_stdout(f):
    try:
        sane_run()
    except SystemExit as exit_code:
        if exit_code.code != 0:
            raise Exception(f'Exited with non zero exit code {exit_code}!')
out = f.getvalue()

for word in chain(list_keywords, info_keywords, all_keywords):
    if word not in out:
        raise Exception(f'Word \'{word}\' not found in --list-all output')
