'''Sane, Makefile for humans.

Copyright 2023 Miguel Murça

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the 'Software'), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import os
import sys
import re
import inspect
import traceback
import builtins
import atexit
import textwrap
import concurrent.futures.thread
from concurrent.futures import ThreadPoolExecutor
from typing import Literal
from collections import namedtuple


class _Sane:

    VERSION = '7.0'
    ANSI = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    MANUAL = '''
        # Sane, Make for humans.

        (Hint: this manual is written in Markdown.
         Use your favourite terminal markdown renderer for optimal results.)

        ## What is sane?

        Sane is a command runner. It defines a simple interface to declare
        functions to run, and relationships between those functions. In
        particular, it lets you define certain functions as requiring other
        tasks to be completed first. This is not exactly the same as Make, which
        operates based on files (and not commands), but the principles and goals
        are very similar.
        
        ## How can I get quickly started?

        Place a copy of `sane.py` in a directory, and create a file to define
        your tasks (I usually go with `make.py`). Then, simply `import sane`.

        ```python
        # make.py
        import sane
        ```

        `make.py` now functions as an interactive script.
        Call `python make.py --help` for more information, or keep on reading.
        
        ## Can you give me an example?

        Sure! The author's favourite dessert, "camel slobber" ([really!][1]),
        is not just extremely sweet, but very easy to prepare: you only need
        6 eggs, and a can of cooked condensed milk (which you might know as
        dulce de leche). You'll want to beat the yolks together with the dulce
        de leche, and fold that together with the whites beaten to a stiff peak.
        Then, chill everything and serve.

        We can write some Python to do that:

        ```python
        # camel_slobber.py

        def crack_eggs():
            ...
        
        def beat_yolks():
            ...
        
        def mix_yolks_and_dulce():
            ...
        
        def beat_whites_to_stiff():
            ...
        
        def fold():
            ...
        
        def chill():
            ...
        
        def serve():
            ...
        ```
        
        Now, there are some clear dependencies between the functions above: you
        can't beat the yolks before cracking the eggs, and you definitely can't
        serve before folding the two mixes together. Sane allows you to express
        these relationships.

        We start by importing sane:

        ```python
        # camel_slobber.py
        import sane
        
        def crack_eggs():
            ...
        [...]
        ```
        
        This will automatically transform the `camel_slobber.py` file into an
        interactive script; try it out:

        ```terminal
        $ python cammel_slobber.py
        
        [error] No @cmd given, and no @default @cmd exists.
        (Add @default to a @cmd to run it when no @cmd is specified.)
        (If you need help getting started with sane, run 'man.py --verbose --help)'.
        ```
        
        Sane is telling us we need a @default @cmd. @cmds are tasks that we
        expect the user to want to execute directly, and that can (therefore)
        take some arguments. You declare a function to be a @cmd by decorating
        it accordingly:

        ```python
        # camel_slobber.py
        import sane

        [...]

        @sane.default
        @sane.cmd
        def serve():
            print("Oooh, ahhh!")
        ```
        
        Naturally, the @default @cmd is the one that's ran if no @cmd is
        specified by the user. If we now run the script again...

        ```terminal
        $ python camel_slobber.py

        Ooooh, ahhh!
        ```
        
        Sane executed our @default @cmd! Let's define an alternative @cmd:

        ```python
        [...]

        @sane.cmd
        def save_for_later():
            print("Self control really pays off sometimes!")
        ```
        
        To run `save_for_later`, we just...

        ```terminal
        $ python camel_slobber.py save_for_later

        Self control really pays off sometimes!
        ```
        
        As mentioned already, @cmds also admit arguments; let's introduce yet
        another @cmd, which takes a couple of arguments:

        ```python
        # camel_slobber.py
        [...]
        
        @sane.cmd
        def pay_compliments(first, second):
            print(f"This camel slobber isn't just {first}, it's also {second}!")
        ```
        
        Let's try to pay a compliment to the chef:

        ```terminal
        $ python camel_slobber.py pay_compliments "very sweet"

        Have you forgot a -- before the @cmd's arguments?

        Usage: man.py [--no-color | --color] [--verbose] --help
               man.py --version
               man.py [--no-color | --color] --list
               man.py [--no-color | --color] [--verbose] [--jobs=<n>] [cmd] [-- ...args]
        ```
        
        Ah, yes, I seem to be missing a "--" to separate the arguments meant for
        sane from the arguments meant for my @cmd. Let me try this again:

        ```terminal
        $ python camel_slobber.py pay_compliments -- "very sweet"

        [error] Wrong number of arguments for pay_compliments(first, second).

        [... a snippet of the pay_compliments code ...]
        ```
        
        Oh, now I'm missing a second argument, as I'd specified in the function
        definition. Third time's the charm:

        ```terminal
        $ python camel_slobber.py pay_compliments -- "very sweet" "extremely tasty"

        This camel slobber isn't just very sweet, it's also extremely tasty!
        ```
        
        That looks like correct output to me! Do note that arguments given from
        the command line will always be passed to the @cmds as strings.

        Now let's backtrack a little, and focus on the preparation of the camel
        slobber. We have a few @tasks to accomplish before being able to
        `serve()` the dessert; but, in principle, there's no reasons the user
        would want to invoke these @tasks directly. Therefore, we decorate these
        functions accordingly:

        ```python
        @sane.task
        def crack_eggs():
            ...
        
        @sane.task
        def beat_yolks():
            ...
        
        @sane.task
        def mix_yolks_and_dulce():
            ...
        
        @sane.task
        def beat_whites_to_stiff():
            ...
        
        [...]
        ```
        
        Note that @tasks don't take any arguments; sane won't let you decorate
        a function taking arguments with @task. @tasks aren't very interesting
        by themselves; their point is to be called upon as dependencies.
        
        The recipe we have states the following dependencies:

        ```plain
        [crack_eggs] ─┬───> [beat_yolks] ────────────>[mix_yolks_and_dulce]─┬─>[fold]─>(...)
                      │                                                     │ 
                      └─────────────> [beat_whites_to_stiff] ───────────────┘ 
        ```
        
        (Notice how, if you have help, you can take care of the yolks and whites
        at the same time; sane is aware of this, and can take advantage of it,
        as we'll see later.)
        
        We can express these dependencies by use of the @depends decorator:

        ```python
        @sane.task
        def crack_eggs():
            ...
        
        @sane.task
        @sane.depends(on_task=crack_eggs)
        def beat_yolks():
            ...
        
        @sane.task
        @sane.depends(on_task=beat_yolks)
        def mix_yolks_and_dulce():
            ...
        
        @sane.task
        @sane.depends(on_task=crack_eggs)
        def beat_whites_to_stiff():
            ...
        
        @sane.task
        @sane.depends(on_task=mix_yolks_and_dulce)
        @sane.depends(on_task=beat_whites_to_stiff)
        def fold():
            ...
        ```

        ## Dealing with corrupt magic
        
        TODO
        
        ## Why use sane?

        Sane is 1. extremely portable, and 2. low (mental) overhead. This is
        because (1.) sane is fully contained in a single Python file, so you can
        (and should!) distribute it alongside your codebase, and (2.) sane
        is vanilla Python. The second property makes sane extremely expressive
        -- in fact, sane can do anything Python can -- and prevents the
        introduction of more domain-specific languages.
        
        Of course, with great power comes great responsibility, and sane is
        trivially Turing complete; that is, after all, the point. Therefore,
        there are more ways to fail critically. But, as Python has shown over
        the years, this flexibility is not much of a problem in practice,
        especially when compared to the advantages it brings, and given that
        other, more structured, tools are still available to be used in tandem.
                      
        Regardless, sane thoroughly attempts to validate the input program, and
        will always try to guide you to write a correct program.
        
        ## TL;DR

        1. Import sane
        2. Use @sane.cmd for anything you'd want to run from the command line,
           and @sane.task for anything you need to get done.
        3. Decorate @cmds and @tasks with @depends, as appropriate.
        4. Use @tag if you want to depend on a family of @tasks
        5. run python your_script.py [sane args] -- [your args]
        
        ## References

        [1]: https://en.m.wikipedia.org/wiki/Baba_de_camelo
    '''

    Context = namedtuple(
        'Context', ('filename', 'lineno', 'code_context', 'index'))
    Depends = namedtuple('Depends', ('value', 'context'))
    Default = namedtuple('Default', ('func', 'context'))

    singleton = None

    @staticmethod
    def strip_ansi(text):
        return _Sane.ANSI.sub('', text)

    @staticmethod
    def get_context():
        stack = inspect.stack(context=4)
        for element in stack:
            if element.frame.f_globals['__name__'] != __name__:
                context = _Sane.Context(element.filename,
                                        element.lineno,
                                        element.code_context,
                                        element.index)
                stack.clear()
                return context

    @staticmethod
    def get():
        if _Sane.singleton is None:
            _Sane.singleton = _Sane()
        return _Sane.singleton

    def __init__(self):
        if _Sane.singleton is not None:
            raise Exception()
        self.initialize_properties()
        self.setup_logging()
        self.read_arguments()
        self.run_on_exit()

    def initialize_properties(self):
        self.finalized = False
        self.default = None
        self.cmds = {}
        self.tasks = {}
        self.tags = {}
        self.operation = {}
        self.incidence = {}
        self._thread_exe = None
        self.script_name = self.get_script_name()

    def setup_logging(self):
        self.verbose = False
        if os.environ.get('NO_COLOR', False) or not sys.stdout.isatty():
            self.color = False
        else:
            self.color = True

    def get_script_name(self):
        main = sys.modules['__main__']
        if hasattr(main, '__file__'):
            return os.path.basename(main.__file__)
        else:
            return 'script'

    def read_arguments(self):
        args = sys.argv[1:]
        if '--' in args:
            cmd_arg_limit = args.index('--')
            if cmd_arg_limit == len(args):
                self.usage_error()
            sane_args = list(args[:cmd_arg_limit])
            cmd_args = tuple(args[cmd_arg_limit + 1:])
        else:
            sane_args = list(args)
            cmd_args = None

        color = self.get_cmdline_flag(sane_args, '-nc', '--no-color')
        no_color = self.get_cmdline_flag(sane_args, '-c', '--color')
        verbose = self.get_cmdline_flag(sane_args, '-v', '--verbose')
        help_ = self.get_cmdline_flag(sane_args, '-h', '--help')

        if color and no_color:
            self.usage_error()
            sys.exit(1)

        if verbose:
            self.verbose = True
        if no_color:
            self.color = False
        if color:
            self.color = True

        if help_:
            if verbose:
                print(inspect.cleandoc(_Sane.MANUAL))
            else:
                print(self.get_long_usage())
            self.finalized = True
            sys.exit(0)

        if '--list' in sane_args:
            if cmd_args is not None or len(sane_args) != 1:
                self.usage_error()
            self.operation = {'mode': 'list'}
        else:
            self.setup_jobs(sane_args)

            if len(sane_args) > 0:
                if len(sane_args) > 1:
                    self.hint('Have you forgot a -- before the @cmd\'s arguments?\n')
                    self.usage_error()
                cmd = sane_args.pop()
                if cmd.startswith('-'):
                    self.usage_error()
            else:
                cmd = None

            if cmd_args is None:
                cmd_args = ()

            self.operation = {
                'mode': 'cmd',
                'cmd': cmd,
                'args': cmd_args,
            }
    
    def setup_jobs(self, args):
        jobs = self.get_cmdline_value(args, '--jobs', '-j')
        if jobs is not None:
            try:
                jobs = int(jobs)
                if jobs == 1:
                    self._thread_exe = None
                elif jobs == 0:
                    self._thread_exe = ThreadPoolExecutor(max_workers=None)
                else:
                    self._thread_exe = ThreadPoolExecutor(max_workers=jobs)
            except ValueError:
                self.error('--jobs must be a number.')
                self.usage_error()

    def get_cmdline_flag(self, args, short, long_):
        has_short = (short in args)
        has_long = (long_ in args)
        if has_short and has_long:
            self.usage_error()
        else:
            is_set = False
            if has_short:
                args.remove(short)
                is_set = True
            elif has_long:
                args.remove(long_)
                is_set = True
            return is_set

    def get_cmdline_value(self, args, long_, short):
        for i in range(len(args)):
            arg = args[i]
            has_long = arg.startswith(long_)
            has_short = arg.startswith(short)
            if has_long or has_short:
                if has_short:
                    remaining = arg.removeprefix(short)
                else:
                    remaining = arg.removeprefix(long_)
                if remaining.startswith('='):
                    args.remove(arg)
                    return remaining.removeprefix('=')
                elif len(remaining) == 0:
                    if i < len(args) - 1:
                        value = args[i+1]
                        args.remove(arg)
                        args.remove(value)
                        return value

    def usage_error(self):
        self.finalized = True
        print(self.get_short_usage(), file=sys.stderr)
        sys.exit(1)

    def get_short_usage(self):
        script = self.script_name
        return (f'Usage: {script} [--no-color | --color] [--verbose] --help\n'
                f'       {script} --version\n'
                f'       {script} [--no-color | --color] --list\n'
                f'       {script} [--no-color | --color] [--verbose] [--jobs=<n>] [cmd] [-- ...args]')

    def get_long_usage(self):
        return ('Sane, Make for humans.\n'
                f'{self.get_short_usage()}\n\n'
                'Options:\n'
                '  --help         Show this screen, or the manual if --verbose is set.\n'
                '  --version      Print the current sane version.\n'
                '  --verbose      Produce verbose output.\n'
                '  --color        Enable ANSI color codes even in non-console terminals.\n'
                '  --no-color     Disable ANSI color codes in the output.\n'
                '  --jobs=<n>     Perform (at most) \'n\' tasks concurrently.\n'
                '                 If suppressed, tasks are evaluated serially.\n'
                '                 Passing \'0\' runs any number of tasks concurrently.'
                '\n'
                'Arguments given after \'--\' are passed to the provided @cmd.\n'
                'If no command is given, the @default @cmd is ran, if it exists.')
    
    def get_manual(self):
        return ('# Sane, Makefile for humans.\n'
                '')

    def cmd_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        if self.finalized:
            self.error('@cmd cannot appear after sane().')
            self.show_context(context, 'error')
            self.hint('(Move sane() to the end of the file.)')

        if len(args) > 1 or len(kwargs) > 0:
            self.error('@cmd does not take arguments.')
            self.show_context(context, 'error')
            self.hint('(To specify other properties, use @tag or @depends.)')
            sys.exit(1)
        elif len(args) == 0:
            self.error('@cmd does not have parentheses.')
            self.show_context(context, 'error')
            self.hint('(Remove the parentheses.)')
            sys.exit(1)

        func = args[0]
        if not hasattr(func, '__call__'):
            self.error('@cmd must decorate a function.')
            self.show_context(context, 'error')
            sys.exit(1)

        self.ensure_positional_args_only(context, func)
        self.ensure_no_tags(func, context)
        
        if not hasattr(func, '__name__'):
            self.error('A @cmd must have a name.')
            self.show_context(context, 'error')
            self.hint('(Use a @task instead.)')
            sys.exit(1)

        if func.__name__ in self.cmds:
            other_, other_context = self.cmds[func.__name__]
            self.error('@cmd names must be unique.')
            self.show_context(context, 'error')
            self.show_context(other_context, 'hint')
            self.hint('(Use a @task instead.)')
            sys.exit(1)

        props = self.get_props(func)
        if self.is_task_or_cmd(func):
            self.error('More than one @cmd or @task.')
            self.show_context(context, 'error')
            self.hint(
                '(A function can only have a single @cmd or @task decorator.)')
            sys.exit(1)
        props['type'] = 'cmd'
        props['context'] = context

        def cmd(*args, **kwargs):
            if not self.finalized:
                context = _Sane.get_context()
                self.warn('Calling a @cmd from outside other '
                          '@cmds or @tasks ignores @depends.')
                self.show_context(context, 'warn')
                return func(*args)
            else:
                return self.run_tree(func, args)

        cmd.__dict__['__sane__'] = {'type': 'wrapper', 'inner': func}
        self.cmds[func.__name__] = func
        return cmd

    def task_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        if self.finalized:
            self.error('@task cannot appear after sane().')
            self.show_context(context)
            self.hint('(Move sane() to the end of the file.)')

        if len(args) > 1 or len(kwargs) > 0:
            self.error('@task does not take arguments.')
            self.show_context(context, 'error')
            self.hint('(To specify other properties, use @tag or @depends.)')
            sys.exit(1)
        elif len(args) == 0:
            self.error('@task does not have parentheses.')
            self.show_context(context, 'error')
            self.hint('(Remove the parentheses.)')
            sys.exit(1)

        func = args[0]
        if not hasattr(func, '__call__'):
            self.error('@task must decorate a function.')
            self.show_context(context, 'error')
            sys.exit(1)

        self.ensure_no_args(func, context)

        props = self.get_props(func)
        if self.is_task_or_cmd(func):
            self.error('More than one @cmd or @task.')
            self.show_context(context, 'error')
            self.hint(
                '(A function can only have a single @cmd or @task decorator.)')
            sys.exit(1)
        props['type'] = 'task'
        props['context'] = context

        def task():
            if not self.finalized:
                context = _Sane.get_context()
                self.warn('Calling a @task from outside other '
                          '@cmds or @tasks ignores @depends.')
                self.show_context(context, 'warn')
                return func()
            else:
                return self.run_tree(func, ())

        task.__dict__['__sane__'] = {'type': 'wrapper', 'inner': func}
        self.tasks.setdefault(func.__name__, []).append(func)
        return task

    def depends_decorator(self, *pargs, **args):
        context = _Sane.get_context()

        if len(pargs) > 0:
            self.error('@depends takes keyword arguments only.')
            self.show_context(context, 'error')
            self.hint('(Use on_tag=, on_cmd=, or on_task=.)')
            sys.exit(1)

        given = list(arg for arg in ('on_tag', 'on_cmd',
                     'on_task') if arg in args.keys())
        if len(given) != 1:
            self.error(
                '@depends must take a single on_tag=, on_cmd=, or on_task=.')
            self.show_context(context, 'error')
            self.hint('(If you wish to have multiple dependencies, '
                      'use multiple @depends decorators.)')
            sys.exit(1)
        given = given[0]

        def specific_decorator(func):
            if self.is_task_or_cmd(func):
                self.error('@depends cannot come before @cmd or @task.')
                self.show_context(context, 'error')
                sys.exit(1)

            if given == 'on_tag':
                return self.depends_on_tag(context, func, **args)
            elif given == 'on_cmd':
                return self.depends_on_cmd(context, func, **args)
            else:
                return self.depends_on_task(context, func, **args)

        return specific_decorator

    def depends_on_tag(self, context, func, **args):
        if len(args) != 1:
            self.error('@depends(on_tag=...) does not take other arguments.')
            self.show_context(context)
            sys.exit(1)

        tag = []
        arg = args['on_tag']
        if type(arg) is str:
            tag.append(_Sane.Depends(arg, context))
        elif hasattr(arg, '__iter__'):
            if type(arg) not in (tuple, list, set):
                if type(arg) is dict:
                    self.warn('on_tag= argument is a dictionary, which, although iterable, '
                              'is ambiguous, since only the values (and not the keys) will '
                              'be considered. The values will still be considered, but '
                              'this may be unexpected.')
                else:
                    self.warn('on_tag= argument is not a collection, although it is iterable. '
                              'The elements in this iterator will still be considered, '
                              'but exhaustion of the iterator may produce unexpected results.')
                self.show_context(context, 'warn')
                self.hint(
                    '(To silence this warning, convert the argument to a collection type.)')

            for element in arg:
                if type(element) is str:
                    tag.append(_Sane.Depends(element, context))
                else:
                    self.error('on_tag= argument must be iterable of string.')
                    self.show_context(context, 'error')
                    sys.exit(1)
        else:
            self.error(
                'on_tag= argument must be string or iterable of string.')
            self.show_context(context, 'error')
            sys.exit(1)

        props = self.get_props(func)
        props['depends']['tag'].extend(tag)

        return func

    def depends_on_cmd(self, context, func, **args):
        malformed_args = (
            len(args) != 2 or
            set(args.keys()) != set(('on_cmd', 'args')))

        if malformed_args:
            self.error(
                '@depends(on_cmd=..., args=...) takes exactly these two arguments.')
            self.show_context(context, 'error')
            self.hint('(Did you mean @depends(on_task=...)?)')
            sys.exit(1)

        cmd = args['on_cmd']
        args = args['args']

        if type(args) not in (tuple, list):
            if type(args) is str:
                self.error('The args= argument must be a tuple or list.')
                self.show_context(context, 'error')
                self.hint(f'Write args=["{args}"] instead.')
            elif hasattr(args, '__iter__'):
                if type(args) is dict:
                    self.warn('The args= argument is a dictionary, which, although iterable, '
                              'is ambiguous, since only the values (and not the keys) will '
                              'be considered. The values will still be considered, but '
                              'this may be unexpected.')
                else:
                    self.warn('The args= argument is not a collection, although it is iterable. '
                              'The elements in this iterator will still be considered, '
                              'but exhaustion of the iterator may produce unexpected results.')
                self.show_context(context, 'warn')
                self.hint(
                    '(To silence this warning, convert the argument to a collection type.)')
                args = list(args)
            else:
                self.error('The args= argument must be a tuple or list.')
                self.show_context(context, 'error')

        if type(cmd) is not str:
            if hasattr(cmd, '__call__'):
                if not hasattr(cmd, '__sane__'):
                    self.error('Given function is not a @cmd.')
                    self.show_context(context, 'error')
                    self.hint('(Is the referenced function missing a @cmd?)')
                    sys.exit(1)
                elif cmd.__sane__.get('type', None) != 'wrapper':
                    self.error('Given function is not decorated with @cmd.')
                    self.show_context(context, 'error')
                    self.hint('(Add a @cmd before the other decorators.)')
                    sys.exit(1)
                cmd = cmd.__sane__['inner']
                if cmd.__sane__['type'] != 'cmd':
                    self.error('Given function is not a @cmd.')
                    self.show_context(context, 'error')
                    self.hint('(Did you mean @depends(on_task=...)?)')
                    sys.exit(1)
            else:
                self.error(
                    'on_cmd= argument must be a cmd, or the name of a cmd.')
                self.show_context(context, 'error')
                sys.exit(1)

        props = self.get_props(func)
        props['depends']['cmd'].append(
            _Sane.Depends((cmd, args), context))

        # Resolution of `cmd` and validation of `args` happens at graph build stage.

        return func

    def depends_on_task(self, context, func, **args):
        if len(args) != 1:
            if len(args) == 2 and 'args' in args:
                self.error('@depends(on_task=...) takes no args= parameter.')
                self.show_context(context, 'error')
                self.hint('(Did you mean @depends(on_cmd=..., args=...)?)')
                sys.exit(1)
            else:
                self.error('@depends(on_task=...) takes no other parameters.')
                self.show_context(context, 'error')
                sys.exit(1)

        task = args['on_task']

        if type(task) is not str:
            if hasattr(task, '__call__'):
                if not hasattr(task, '__sane__'):
                    self.error('Given function is not a @task.')
                    self.show_context(context, 'error')
                    self.hint('(Is the referenced function missing a @task?)')
                    sys.exit(1)
                elif task.__sane__.get('type', None) != 'wrapper':
                    self.error('Given function is not decorated with @task.')
                    self.show_context(context, 'error')
                    self.hint('(Add a @task before the other decorators.)')
                    sys.exit(1)
                task = task.__sane__['inner']
                if task.__sane__['type'] != 'task':
                    self.error('Given function is not a @task.')
                    self.show_context(context, 'error')
                    self.hint('(Did you mean @depends(on_cmd=...)?)')
                    sys.exit(1)
            else:
                self.error(
                    'on_task= argument must be a task, or the name of a task.')
                self.show_context(context, 'error')
                sys.exit(1)

        props = self.get_props(func)
        props['depends']['task'].append(_Sane.Depends(task, context))

        # Resolution of task happens at graph build stage.

        return func

    def tag_decorator(self, *args, **kwargs):
        context = _Sane.get_context()

        invalid_args = (len(kwargs) > 0 or
                        len(args) > 1)
        if invalid_args:
            self.error('@tag takes a single positional argument.')
            self.show_context(context, 'error')
            self.hint('(For example, @tag(\'foo\').)')
            sys.exit(1)

        tag = args[0]
        if type(tag) is not str:
            self.error('@tag must be a string.')
            self.show_context(context, 'error')
            self.hint('(For example, @tag(\'foo\').)')
            sys.exit(1)

        def specific_decorator(func):
            if self.is_task_or_cmd(func):
                self.error('@tag cannot come before @cmd or @task.')
                self.show_context(context, 'error')
                sys.exit(1)
            props = self.get_props(func)
            props['tags'].append(tag)
            self.tags.setdefault(tag, []).append(func)
            return func

        return specific_decorator

    def default_decorator(self, *args, **kwargs):
        if len(args) > 1 or len(kwargs) > 0:
            self.error('@default does not take arguments.')
            self.show_context(context, 'error')
            self.hint('(To specify other properties, use @tag or @depends.)')
            sys.exit(1)
        elif len(args) == 0:
            self.error('@default does not have parentheses.')
            self.show_context(context, 'error')
            self.hint('(Remove the parentheses.)')
            sys.exit(1)

        context = _Sane.get_context()

        if self.default is not None:
            self.error('More than one @default.')
            self.show_context(context, 'error')
            self.hint('(Other @default found here:)')
            self.show_context(self.default.context, 'hint')
            sys.exit(1)

        func = args[0]

        if not hasattr(func, '__sane__'):
            self.error('@default must come before @cmd.')
            self.show_context(context, 'error')
            self.hint('(Add a @cmd decorator to this function, '
                      'or move @default to come before @cmd.)')
            sys.exit(1)

        type_ = func.__sane__['type']
        if type_ == 'cmd':
            self.error('@default must come before @cmd.')
            self.show_context(context, 'error')
            self.hint('(Move @default to be the first decorator.)')
            sys.exit(1)
        else:
            if type_ == 'wrapper':
                type_ = func.__sane__['inner'].__sane__['type']
            if type_ == 'task':
                self.error('@default cannot be used with @task.')
                self.show_context(context, 'error')
                self.hint('(Use a @cmd instead.)')
                sys.exit(1)
            elif type_ != 'cmd':
                raise ValueError(type_)

        self.default = _Sane.Default(func.__sane__['inner'], context)
        return func

    def run_on_exit(self):
        self.exit_code = 0
        def save_and_exit(wraps):
            def _exit(code=0):
                self.exit_code = code
                return wraps(code)
            return _exit
        _sys_exit = sys.exit
        _builtins_exit = builtins.exit
        sys.exit = save_and_exit(_sys_exit)
        builtins.exit = save_and_exit(_builtins_exit)
        atexit.register(self.atexit)

    def atexit(self):
        try:
            self.main()
        except SystemExit as sys_exit:
            if self._thread_exe is not None:
                self._thread_exe.shutdown()
            # TODO: Change exit code and exit cleanly.
            # This is currently apparently not possible.
            # See https://github.com/python/cpython/issues/103512
            # os._exit ignores other handlers and does not flush buffers.
            os._exit(sys_exit.code)

    def main(self):
        if self.exit_code or self.finalized:
            return
        self.finalized = True

        op_mode = self.operation['mode']
        if op_mode == 'list':
            self.list_cmds()
        elif op_mode == 'cmd':
            cmd = self.operation['cmd']
            args = self.operation['args']

            if cmd is None:
                if self.default is None:
                    self.error(
                        'No @cmd given, and no @default @cmd exists.')
                    self.hint(
                        '(Add @default to a @cmd to run it when no @cmd is specified.)')
                    self.hint(
                        '(If you need help getting started with sane, run '
                        f'\'{self.script_name} --verbose --help)\'.')
                    sys.exit(1)
                cmd = self.default.func
            else:
                if cmd not in self.cmds:
                    self.error(f'No @cmd named {cmd}.')
                    self.hint('(Use --list to see all available @cmds.)')
                    sys.exit(1)
                cmd = self.cmds[cmd]
                
                if not self.is_signature_compatible(cmd, args):
                    context = cmd.__sane__['context']
                    str_cmd = self.get_name(cmd)
                    str_args = self.get_str_args(cmd)
                    self.error(f'Wrong number of arguments for {str_cmd}({str_args}).')
                    self.show_context(context, 'error')
                    sys.exit(1)

            self.run_tree(cmd, args)

        if self._thread_exe is not None:
            self._thread_exe.shutdown()

    def list_cmds(self):
        for cmd_name, cmd in self.cmds.items():
            self.print(f'\x1b[1m{cmd_name}\x1b[0m', end='')

            if self.verbose:
                str_cmd_args = self.get_str_args(cmd)
                if str_cmd_args:
                    self.print(f'\x1b[2m({str_cmd_args})\x1b[0m')
                else:
                    self.print('\n  \x1b[2m(No arguments.)\x1b[0m')

                if hasattr(cmd, '__doc__') and cmd.__doc__:
                    doc = cmd.__doc__
                    for line in doc.splitlines():
                        self.print(f'\x1b[2m  {line}\x1b[0m')
                else:
                    self.print('  \x1b[2mNo information given.\x1b[0m')
            else:
                self.print('\n', end='')

    def run_tree(self, func, args):
        self.update_graph(func, args)
        toposort = self.get_toposort(func, args)
        for slice_ in toposort[:-1]:
            if self._thread_exe is None:
                for func, args in slice_:
                    if self.verbose:
                        str_func = self.get_name(func)
                        str_args = ', '.join(str(x) for x in args)
                        self.log(f'Running {str_func}({str_args})')

                    try:
                        func.__call__(*args)
                    except Exception as e:
                        self.report_func_failed(func, e)
            else:
                if self.verbose:
                    str_jobs = []
                    for func, args in slice_:
                        str_func = self.get_name(func)
                        str_args = ', '.join(str(x) for x in args)
                        str_jobs.append(f'{str_func}({str_args})')
                    if len(str_jobs) > 1:
                        str_jobs = ', '.join(
                            str_jobs[:-1]) + ', and ' + str_jobs[-1]
                        self.log(f'Simultaneously running {str_jobs}.')
                    else:
                        str_jobs = str_jobs[0]
                        self.log(f'Running {str_jobs}.')

                # TODO: Reconsider this.
                # This is due to https://github.com/python/cpython/issues/86813
                # However, given the behaviour in <3.8, it's hard to understand
                # the taken decision.
                def _submit(func, args):
                    with self._thread_exe._shutdown_lock, concurrent.futures.thread._global_shutdown_lock:
                        if self._thread_exe._broken:
                            raise BrokenThreadPool(self._broken)
                        f = concurrent.futures.thread._base.Future()
                        w = concurrent.futures.thread._WorkItem(f, func, args, {})
                        self._thread_exe._work_queue.put(w)
                        self._thread_exe._adjust_thread_count()
                        return f
                futures = (_submit(self.catch_thread_exception(func), args)
                           for func, args in slice_)
                for future in futures:
                    try:
                        future.result()
                    except Exception as e:
                        self.report_func_failed(func, e)

        if self.verbose:
            str_func = self.get_name(func)
            str_args = ', '.join(str(x) for x in args)
            self.log(f'Running {str_func}({str_args})')

        func, args = toposort[-1][0]
        return self.catch_thread_exception(func)(*args)
    
    def report_func_failed(self, func, exception):
        context = func.__sane__['context']
        name = self.get_name(func)
        type_ = func.__sane__['type']
        cmd_args = inspect.signature(cmd).parameters.keys()
        lines = [f'Failed running @{type_} {name}.',
                 *traceback.format_exception(exception),
                 'Aborting.']
        self.error('\n'.join(lines))
        sys.exit(1)

    def catch_thread_exception(self, inner):
        def fn(*args, **kwargs):
            try:
                return inner(*args, **kwargs)
            except RuntimeError as e:
                lines = textwrap.wrap(
                      'Due to limitations on the magic used to invoke sane, '
                      'the @tasks and @cmds are executed after the interpreter '
                      'has shut down, by use of the atexit module. Generally, '
                      'the difference should not be noticeable --- and, at the '
                      'time of writing, atexit defines no limitations as to '
                      'what can be done in this regime --- but, in practice, '
                      'some operations may be prevented. (In particular, '
                      'concurrency is disallowed, although this behaviour is '
                      'undocumented.)\n'
                      'If you are encountering these limitations (which can '
                      'easily happen if using external modules), consider '
                      'disabling the magic behaviour by calling sane.sane() '
                      'at the end of your program.',
                      subsequent_indent='       ')
                self.warn('\n'.join(lines))
                raise e
        return fn

    def update_graph(self, func, args):
        visiting = set()
        stack = [('visit', (func, args))]
        while len(stack) > 0:
            op, item = stack.pop()
            func, args = item
            if op == 'visit':
                if item in visiting:
                    trace = self.get_trace(stack)
                    self.report_loop(trace)

                visiting.add(item)
                stack.append(('seal', item))

                props = self.get_props(func)
                self.resolve_depends(props)
                for cmd_item, _context in props['depends']['cmd']:
                    if cmd_item in self.incidence:
                        self.incidence[cmd_item] += 1
                    else:
                        stack.append(('visit', cmd_item))
                        self.incidence[cmd_item] = 1
                for task, _context in props['depends']['task']:
                    task_item = (task, ())
                    if task_item in self.incidence:
                        self.incidence[task_item] += 1
                    else:
                        stack.append(('visit', task_item))
                        self.incidence[task_item] = 1
                for tag, _context in props['depends']['tag']:
                    for task in self.tags.get(tag, []):
                        task_item = (task, ())
                        if task_item in self.incidence:
                            self.incidence[task_item] += 1
                        else:
                            stack.append(('visit', task_item))
                            self.incidence[task_item] = 1
            elif op == 'seal':
                visiting.remove(item)
            else:
                raise ValueError(op)

    def get_toposort(self, func, args):
        toposort = []

        roots = [(func, args)]
        incidence = self.incidence.copy()

        while len(roots) > 0:
            toposort.append(roots)
            next_roots = []
            for func, args in roots:
                props = self.get_props(func)
                for cmd_item, _context in props['depends']['cmd']:
                    incidence[cmd_item] -= 1
                    if incidence[cmd_item] == 0:
                        next_roots.append(cmd_item)
                for task, _context in props['depends']['task']:
                    task_item = (task, ())
                    incidence[task_item] -= 1
                    if incidence[task_item] == 0:
                        next_roots.append(task_item)
                for tag, context_ in props['depends']['tag']:
                    for task in self.tags.get(tag, []):
                        task_item = (task, ())
                        incidence[task_item] -= 1
                        if incidence[task_item] == 0:
                            next_roots.append(task_item)
            roots = next_roots

        toposort.reverse()
        return toposort

    def resolve_depends(self, props):
        if props['depends']['resolved']:
            return

        for i in range(len(props['depends']['task'])):
            task_depends, context = props['depends']['task'][i]
            if type(task_depends) is str:
                resolved = self.resolve_str_task(task_depends, context)
                props['depends']['task'][i] = (resolved, context)

        for i in range(len(props['depends']['cmd'])):
            value, context = props['depends']['cmd'][i]
            cmd_depends, cmd_args = value
            if type(cmd_depends) is str:
                resolved = self.resolve_str_cmd(cmd_depends, context)
                if not self.is_signature_compatible(resolved, cmd_args):
                    self.error(
                        'Arguments given in @depends are incompatible with the function signature.')
                    self.show_context(context, 'error')
                    sys.exit(1)
                props['depends']['cmd'][i] = ((resolved, cmd_args), context)

        props['depends']['resolved'] = True
    
    def resolve_str_task(self, str_task, context):
        if str_task not in self.tasks:
            self.error(f'No @task named {str_task}.')
            self.show_context(context, 'error')
            self.hint(
                '(You can reference a function directly, instead of a string.)')
            self.hint(
                '(Are you missing a @task somewhere?)')
            sys.exit(1)
        elif len(self.tasks[str_task]) > 1:
            self.error(
                f'There\'s more than one @task named {str_task}.')
            self.show_context(context, 'error')
            self.hint(
                '(You can reference a function directly, instead of a string.)')
            self.hint(
                '(Alternatively, use @tag, and @depends(on_tag=...).)')
            sys.exit(1)
        return self.tasks[str_task][0]        

    def resolve_str_cmd(self, str_cmd, context):
        if str_cmd not in self.cmds:
            self.error(f'No @cmd named {str_cmd}.')
            self.show_context(context, 'error')
            self.hint(
                '(You can reference a function directly, instead of a string.)')
            self.hint(
                '(Are you missing a @cmd somewhere?)')
            sys.exit(1)
        return self.cmds[str_cmd]


    def is_signature_compatible(self, func, args):
        signature = inspect.signature(func)
        mandatory_arg_count = 0
        optional_arg_count = 0
        for arg in signature.parameters.values():
            if arg.default is inspect.Parameter.empty:
                mandatory_arg_count += 1
            else:
                optional_arg_count += 1
        wrong_number_of_args = (len(args) < mandatory_arg_count or
                                len(args) > mandatory_arg_count + optional_arg_count)
        return not wrong_number_of_args

    def get_trace(self, stack):
        trace = []
        while len(stack) > 0:
            op, item = stack.pop()
            if op != 'seal':
                continue
            trace.append(item)
        return trace

    def report_loop(self, trace):
        lines = ['Dependency loop.\n']
        for element in reversed(trace):
            func, args = element
            name = self.get_name(func)
            str_args = ', '.join(str(arg) for arg in args)
            context = func.__sane__['context']
            lines.append(f'* {name}({str_args})\n')
            for line in self.format_context(context).splitlines():
                lines.append(f'| {line}\n')
            lines.append('|\n')

        loop_func, loop_args = trace[-1]
        loop_str_args = ', '.join(str(arg) for arg in args)
        loop_name = self.get_name(loop_func)
        loop_context = func.__sane__['context']
        lines.append(f'* {loop_name}({loop_str_args})')

        self.error(''.join(lines))
        sys.exit(1)

    def get_name(self, func):
        if hasattr(func, '__name__'):
            return func.__name__
        else:
            assert func.__sane__['type'] == 'task'
            return f'(Anonymous Task @ {hex(id(func))})'
    
    def get_str_args(self, cmd):
        cmd_args = inspect.signature(cmd).parameters.keys()
        if len(cmd_args) > 0:
            return ', '.join(cmd_args)
        else:
            return ''

    def is_task_or_cmd(self, func):
        props = self.get_props(func)
        return props['type'] is not None
    
    def ensure_no_tags(self, func, context):
        props = self.get_props(func)
        if not hasattr(func, '__sane__') or not 'tags' in func.__sane__:
            return
        if len(func.__sane__['tags']) > 0:
            self.error('@cmds cannot have @tags.')
            self.show_context(context, 'error')
            self.hint('(Use a @task instead.)')
            sys.exit(1)

    def ensure_no_args(self, func, context):
        signature = inspect.signature(func)
        if len(signature.parameters.values()) > 0:
            self.error('@task cannot have arguments.')
            self.show_context(context, 'error')
            self.hint('(Use a @cmd instead.)')
            sys.exit(1)

    def ensure_positional_args_only(self, context: Context, func):
        signature = inspect.signature(func)
        any_non_positional = any(
            arg.kind not in (inspect.Parameter.POSITIONAL_ONLY,
                             inspect.Parameter.POSITIONAL_OR_KEYWORD)
            for arg in signature.parameters.values())
        if any_non_positional:
            self.error('@cmd cannot have non-positional arguments.')
            self.show_context(context, 'error')
            sys.exit(1)

    def get_props(self, func):
        if '__sane__' not in func.__dict__:
            func.__dict__['__sane__'] = {
                'type': None,
                'context': None,
                'tags': [],
                'depends': {
                    'resolved': False,
                    'tag': [],
                    'cmd': [],
                    'task': [],
                },
                'incidence': None,
            }

        return func.__dict__['__sane__']

    def print(self, *args, **kwargs):
        if self.color:
            print(*args, **kwargs)
        else:
            print(*map(_Sane.strip_ansi, args), **kwargs)

    def log(self, message):
        header = '\x1b[2m[log]\x1b[0m'
        if not self.color:
            header = _Sane.strip_ansi(header)
        print(header, message, file=sys.stderr)

    def warn(self, message):
        header = '\x1b[33m[warn]\x1b[0m'
        if not self.color:
            header = _Sane.strip_ansi(header)
        print(header, message, file=sys.stderr)

    def error(self, message):
        if self.color:
            message = '\x1b[35m[error] ' + message + '\x1b[0m'
        print(message, file=sys.stderr)

    def hint(self, message):
        if self.color:
            message = '\x1b[2m' + message + '\x1b[0m'
        print(message, file=sys.stderr)

    def format_context(self, context: Context):
        line_ctx = f'\n{context.filename}: l.{context.lineno}'
        info = []
        if context.index < context.lineno:
            info.append('...\n')
        for i, code_line in enumerate(context.code_context):
            if i == context.index:
                info_line = '>  ' + code_line
            else:
                info_line = '   ' + code_line
            info.append(info_line)
        info = ''.join(info)
        return f'{line_ctx}\n{info}'

    def show_context(self, context: Context, style: Literal['log', 'warn', 'error', 'debug']):
        info = self.format_context(context)
        if self.color:
            if style == 'log':
                print(f'\x1b[2m{info}\x1b[0m', file=sys.stderr)
            elif style == 'warn':
                print(f'\x1b[33m{info}\x1b[0m', file=sys.stderr)
            elif style == 'error':
                print(f'\x1b[35m{info}\x1b[0m', file=sys.stderr)
            elif style == 'hint':
                print(f'\x1b[2m{info}\x1b[0m', file=sys.stderr)
            else:
                raise ValueError(
                    f'Expected \'{style}\' to be one of log, warn, error, hint.')
        else:
            print(info, file=sys.stderr)


_sane = _Sane.get()
cmd = _sane.cmd_decorator
task = _sane.task_decorator
depends = _sane.depends_decorator
tag = _sane.tag_decorator
default = _sane.default_decorator
sane = _sane.main

if __name__ == '__main__':
    _stateful.log(f'Sane v{_Sane.VERSION}, by Miguel Murça.\n'
                  'Sane should be imported from other files, '
                  'not ran directly.\n'
                  'Refer to the [Github page] for more information.\n'
                  'https://github.com/mikeevmm/sane')
