# Sane, Make for humans.

![Demo gif. Yes, I'm running this on powershell.](demo.gif)

## Index

* [What is sane?](#What-is-sane)
* [Quick start](#Quick-start)
* [Sane by example](#Sane-by-example)
* [The magic of sane, and what to do when it's corrupted](#The-magic-of-sane-and-what-to-do-when-its-corrupted)
* [Reference](#Reference)
    - [@cmd](#cmd)
    - [@task](#task)
    - [@depends](#depends)
    - [@tag](#tag)
* [Why use sane?](#Why-use-sane)
* [Hacking sane](#Hacking-sane)
* [Sane's license terms](#Sanes-license-terms)
* [TL;DR](#TLDR)

## What is sane?

Sane is a command runner. It defines a simple interface to declare
functions to run, and relationships between those functions. In
particular, it lets you define certain functions as requiring other
tasks to be completed first. This is not exactly the same as Make, which
operates based on files (and not commands), but the principles and goals
are very similar.

## Quick start

Place a copy of `sane.py` in a directory, and create a file to define
your tasks (I usually go with `make.py`). Then, simply `import sane`.

```python
# make.py
import sane
```

`make.py` now functions as an interactive script.
Call `python make.py --help` for more information, or keep on reading.

## Sane by example
              
(See also: [Reference](#Reference))

The author's favourite dessert, "camel slobber" ([really!][1]), is not
just extremely sweet, but very easy to prepare: you only need 6 eggs,
and a can of cooked condensed milk (which you might know as dulce de
leche). You'll want to beat the yolks together with the dulce de leche,
and fold that together with the whites beaten to a stiff peak. Then,
chill everything and serve.

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
[crack_eggs] ─┬───> [beat_yolks] ───>[mix_yolks_and_dulce]─┬──>[fold]───>[chill]───>[serve]
              │                                            │ 
              └─────> [beat_whites_to_stiff] ──────────────┘ 
```

(Notice how, if you have help, you can take care of the yolks and whites
at the same time; sane is aware of this, and can take advantage of it.
See the `--verbose --help` for the `--jobs` flag.)

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

@sane.task
@sane.depends(on_task=fold)
def chill():
    ...

@sane.cmd
@sane.depends(on_task=chill)
def serve():
    ...
```

Now, whenever we want to serve some camel slobber, sane will take care
of preparing everything else. We can ask sane to report on what it's
doing by passing the `--verbose` flag:

```terminal
$ python camel_slobber.py --verbose serve

[log] Running crack_eggs()
...
[log] Running beat_yolks()
...
[log] Running beat_whites_to_stiff()
...
[log] Running mix_yolks_and_dulce()
...
[log] Running fold()
...
[log] Running chill()
...
[log] Running serve()
```

In this case, sane decided to beat the yolks before beating the whites
to a stiff, but it could just as well have decided the other way round,
since there's no relationship between the two tasks.

Note also that, just like we can define dependencies on @tasks, we can
also define dependencies on @cmds, with the difference that we must also
specify the corresponding arguments, in that case. This means that two
dependencies on the same @cmd with different arguments are considered
two different dependencies. So, for example, we could add...

```python
@sane.cmd
@sane.depends(on_cmd=serve, args=())
def eat():
    ...
```

Finally, let's talk about @tag. Because sane is very flexible, you can
create multiple @tasks on the fly, which is often useful for real-world
uses. For example, and moving beyond the camel slobber example, if
you're writing a compilation/linking file, you might have something as
follows:

```python
def make_compile_task(file):
    @sane.task
    def compile_():
        ...

for file in source_files:
    make_compile_task(file)
```

(**NB:** Because of a quirk of for loops in Python, the use of a
 `make_compile_task` is **necessary**. Otherwise, all tasks will refer
 to the same `file` in `source_files`, namely, the last `file` in the
 collection. This is because `file` is, in some sense, always the same
 variable, just taking the different values in `source_files`. Whenever
 the different @tasks are finally ran, they will all compile this same
 `file`.)

Then, a `link` @task depends on every compilation @task. But how can we
define this dependency? If we try something like...

```python
# This won't work!

@sane.cmd
@sane.depends(on_task=compile_)
def link():
    ...
```

...then Python will complain about namespaces, because `compile_` is
defined in a different scope. This may also happen if you define recipes
out of order (relative to the dependencies relationships), so sane lets
you reference other functions by name:

```python
# This won't work either!

@sane.cmd
@sane.depends(on_task='compile_')
def link():
    ...
```

This produces a different error message, now coming from sane:

```terminal
[error] There's more than one @task named compile_.

...

   @sane.cmd
>  @sane.depends(on_task='compile_')
   def link():

(You can reference a function directly, instead of a string.)
(Alternatively, use @tag, and @depends(on_tag=...).)
```

Obviously, every compilation task we've defined (one for each source
file) has the same name, "compile_", and because sane can't tell whether
you mean to define a dependency on every such function or only a
particular one, it cannot proceed.

To deal with this situation, sane also has the concept of @tags. You can
tag any @task with one or more strings of your choosing, and define
dependencies on a @tag. If a @task depends on a @tag, it means it
depends on every @task with that @tag.

So, in the present example, we would define the linking-compilation
dependency as follows:

```python
# This will work!

def make_compile_task(file):
    @sane.task
    @sane.tag('compilation')
    def compile_():
        ...

for file in source_files:
    make_compile_task(file)

@sane.cmd
@sane.depends(on_tag='compilation')
def link():
    ...
```

## The magic of sane, and what to do when it's corrupted

> **TL;DR:** Getting weird results or unexpected behaviour from your
> sane code? Just call `if __name__ == '__main__': sane.sane()` at the
> end of your file.

Sane uses the `atexit` module to magically execute the @cmds and @tasks
after they've all been defined. At the time of writing, the official
Python documentation does not specify any limitation to the sort of code
that can (or even should!) be ran inside an `atexit` handler. But, this
doesn't mean that there's no difference between the `atexit` context,
and the usual script context: in fact, the sane code responsible for 
understanding dependencies and running the relevant tasks runs after the
Python interpreter has begun to shut down. This has several
consequences: for example, the definition of `__main__` will be
different by the time your functions run, and some things are simply
(undocumentedly) not allowed, like spawning new jobs with the
`concurrent.futures` module. This is not a problem if all you're doing
is reading and writing to some files and spawning external commands.
But -- especially when using external modules, which might make
assumptions about the sort of environment they're being used in -- it
*may* be a problem.

So, sane lets you opt out of this magic functionality, by letting you
run the relevant sane bootstrapping code yourself at the end of the
main file. You can do this with

```python
[... definitions of @tasks and @cmds, and other contents ...]

if __name__ == '__main__':
    sane.sane()
```

## Reference

### @cmd

Defines this function as a sane @cmd.

Example use:

```
@sane.cmd
def my_cmd():
    """Description of this command."""
    pass
```

A @cmd is a function that the user can invoke from the command line, and
generally corresponds to some end-goal. 

A @cmd is allowed to have arguments, but only positional arguments, and
not keyword arguments. The reasoning is that, since @cmds are allowed to
be invoked from the command line, keyword arguments cannot be reliably
specified.

For this same reason, when a @cmd is evoked from the command line, the
arguments given are passed as strings to the function.

Finally, for the same reason, two @cmds cannot have the same name.
Therefore, any two functions with @cmd decorators must have different
`__name__` attributes.

When a @cmd is evoked from within other @cmds or @tasks, the dependency
tree is first ran (see also @depends and @task).

The user can list all defined @cmds by calling the main script with the
`--list` flag. If the `--verbose` flag is also given, the `__doc__`
string of the function and arguments are also listed.

### @task

Defines this function as a sane @task.

Example use:

```
@sane.task
def my_task():
    pass
```

A @task is a function that sane can call as part of its execution, and
that may require the execution of other @tasks or @cmds. It generally
corresponds to a modular step in a process, but that is not expected to
be the final step.

A @task is not allowed to have arguments (see, instead, @cmd). Likewise,
@tasks cannot be called upon by the user, and are not listed when the
user executes the main script with `--list`.

@tasks may share the same `__name__` attributes (cf. with @cmd).
In this case, however, they may only serve as dependencies by means of
the @tag decorator.

### @depends

Defines a dependency between this sane @cmd or @task and another sane function.

Example use:

```
@sane.task
def a_task():
    pass

@sane.cmd
@sane.depends(on_task=a_task)
def a_cmd():
    pass
```

Uses:

    @depends(on_task=...)
    
    @depends(on_cmd=..., args=(...))
    
    @depends(on_tag=...)

A @depends decorator specifies that the decorated @cmd or @task requires
that another @cmd or @task is previously ran. The chain of dependencies
specified by each @cmd or @task's @depends decorators defines a
dependency tree which is sorted before execution (much like Make).

Depending on whether @depends is specifying a dependency on either a
@cmd, a @tag, or on a @task, the required arguments vary.

## Depending on a @cmd

If @depends is specifying a dependency on a @cmd, exactly two arguments
are required: `on_cmd=` and `args=`.

`on_cmd=` must be either the @cmd decorated function to depend on, or
its name in the form of a `str`. Since two @cmds cannot share the same
name (see @cmd), either form is always accepted.

`args=` must be a `tuple` or `list` of arguments to pass to the @cmd
decorated function to depend on. As such, it must be compatible with
the `on_cmd=` function's signature. This argument is mandatory, even if
the `on_cmd=` function takes no arguments; in this case, `args=()`
must be given.

## Depending on a @task

If @depends is specifying a dependency on a @task, exactly one argument
is required: `on_task=`.

`on_task=` must be either the @task decorated function to depend on, or
its name in the form of a `str`. If more than one @task shares the same
given name, specification by the form of a `str` is disallowed, and a
@tag should be used instead.

## Depending on a @tag

If @depends is specifying a dependency on a @tag, exactly one argument
is required: `on_tag=`. This argument may be either a `str`, or a `list`
or `tuple` of `str`. In the latter case, this is taken to be equivalent
to a `@depends(on_tag=...)` statement for each of the elements of the
collection.

@depends(on_tag=...) specifies a dependency on every @task with a
matching @tag. See @tag for more information.

### @tag

Adds a tag to a sane @cmd or @task.

Example use:

```
@sane.task
@sane.tag('compilation')
def compile_a():
    pass

@sane.task
@sane.tag('compilation')
def compile_b():
    pass

@sane.cmd
@sane.depends(on_tag='compilation')
def link():
    pass
```

A @tag is a way to specify dependencies on a group of functions, rather
than on a specific function (when used in conjunction with
`@depends(on_tag=...)`; see also @depends).

@tag takes exactly one positional argument, which is either a `str` or
a `list` or `tuple` of `str`. In the latter case, this is taken to be
equivalent to a `@tag(...)` statement for each of the elements of the
collection.

## Why use sane?

Sane is 1. extremely portable, and 2. low (mental) overhead. This is
because (1.) sane is fully contained in a single Python file, so you can
(and should!) distribute it alongside your codebase, and (2.) sane
is vanilla Python. The second property makes sane extremely expressive
-- in fact, sane can do anything Python can -- and prevents the
introduction of more domain-specific languages.

Of course, with great power comes great responsibility, and sane is
trivially Turing complete; that is, after all, the point. Therefore,
there are more (and more unpredictable) ways to fail critically. But,
as Python has shown over the years, this flexibility is not much of a
problem in practice, especially when compared to the advantages it
brings, and given that other, more structured, tools are still
available to be used in tandem.
              
Regardless, sane thoroughly attempts to validate the input program, and
will always try to guide you to write a correct program.

## Hacking sane

This section is written for those who either want to

* modify sane's internals,
* better understand how sane works, or
* are writing sufficiently non-standard Python that sane's inner
  workings become relevant.
  
Of course, this requires examining sane's source code, which is
available and was written to be as much self-documenting as possible;
the present text is only accompaniment. It's also expected that you
understand how Python decorators work, and relevant standard library
package documentation should also be considered, where applicable.

Sane operates on the basis of a singleton, defined in the module as
`sane._sane`. This singleton is an instantiation of the `sane._Sane`
class, where all the relevant sane code is defined.

All of the user-facing decorators (i.e., @cmd, @task, @depends, @tag)
are exposed to the user by reexporting these symbols from the singleton
(see also [Python's documentation regarding import rules][2]).

Given this, sane operates in, essentially, two stages: the first stage
concerns registration of user definitions and validation of user
arguments, as well as augmenting the given objects with the metadata
that sane will need in the second stage. In the second stage, sane
performs any necessary resolution (in particular, and for example,
matching `str` arguments to the functions they refer to; see @depends),
parses command-line arguments, and, if applicable, topologically sorts
dependencies and dispatches execution of the relevant @cmds and @tasks.

The first stage is a product of the normal execution of the script;
the singleton is instantiated by means of the `import sane` statement,
and the code inside each of decorators handles argument validation and
metadata registration as appropriate. This does imply some limitations,
as decorators are evaluated "as they appear". This means that, for
example, a @depends decorator cannot validate at its evaluation time
whether a dependency given by name (`str`) is valid or not, as it may
happen that the corresponding definition appears later in the file, and
so has not yet been recorded. Thus, the second stage.

The second stage corresponds to the `_sane.main` function, and is also
exposed to the user (cf. the
[magic section](#The-magic-of-sane-and-what-to-do-when-its-corrupted)).
By default, sane runs in "magic mode", wherein the second stage is
registered as an [atexit][3] callback. Ensuring that this code only runs
when the script has successfully terminated requires monkey patching the
possible exit functions (namely, `sys.exit` and `builtins.exit`). Cf.
the relevant code for details. In any case, the code guards against
running more than once (and so can be prevented from running at all by
manipulation of the singleton's state).

Finally, note that whenever an object is augmented with sane-relevant
metadata, this metadata is stored in a `dict` attribute named
`__sane__`. Inspection of this dictionary at different points of
execution may help with understanding sane's operation.

## Sane's license terms

Sane is distributed under a [CC-BY-NC-SA-4.0][4] license. *Informally*,
this means you are free to use sane in a non-commercial context (i.e.,
personally and academically), as well as modify sane, as long as you:

- Give proper credit and provide a link to the license (so, don't
  modify sane's __doc__ string at the top of the file),
- Indicate if and what changes were made,
- Share your modifications of sane under this same license.
 
For uses of sane under different terms, please contact the author.

If you use do use sane under the CC-BY-NC-SA-4.0 terms, the author adds
a (non-legally enforceable) clause that they would be very thankful if
you would [buy them a coffee][5].

## TL;DR

1. Import sane.
2. Use @sane.cmd for anything you'd want to run from the command line,
   and @sane.task for anything you need to get done.
3. Decorate @cmds and @tasks with @depends, as appropriate.
4. Use @tag if you want to depend on a family of @tasks.
5. run `python your_script.py [sane args] -- [your args]`.

## Links

[1]: https://en.m.wikipedia.org/wiki/Baba_de_camelo
[2]: https://docs.python.org/3/reference/simple_stmts.html#import
[3]: https://docs.python.org/3/library/atexit.html
[4]: http://creativecommons.org/licenses/by-nc-sa/4.0/.
[5]: https://www.paypal.me/miguelmurca/4.00