import sys
from sane import *

@recipe()
def dummy():
    pass

sys.argv.extend(('--no-ansi', '--list'))

# To catch stdout
import io
from contextlib import redirect_stdout

# Fake --list in argv
import sys
sys.argv.append('--list')

f = io.StringIO()
with redirect_stdout(f):
    try:
        sane_run(dummy)
    except SystemExit as exit_code:
        if exit_code.code != 0:
            raise Exception(f'Exited with non zero exit code {exit_code}!')
out = f.getvalue()

assert '-- dummy' in out
