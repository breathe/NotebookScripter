# Notebookscripter [![Version](https://img.shields.io/pypi/v/NotebookScripter.svg)](https://pypi.python.org/pypi/NotebookScripter) [![Build](https://travis-ci.org/breathe/NotebookScripter.svg?branch=master)](https://travis-ci.org/breathe/NotebookScripter) [![Coverage](https://img.shields.io/coveralls/breathe/NotebookScripter.svg)](https://coveralls.io/r/breathe/NotebookScripter) [![Health](https://codeclimate.com/github/breathe/NotebookScripter/badges/gpa.svg)](https://codeclimate.com/github/breathe/NotebookScripter)

[![Compatibility](https://img.shields.io/pypi/pyversions/NotebookScripter.svg)](https://pypi.python.org/pypi/NotebookScripter)
[![Implementations](https://img.shields.io/pypi/implementation/NotebookScripter.svg)](https://pypi.python.org/pypi/NotebookScripter)
[![Format](https://img.shields.io/pypi/format/NotebookScripter.svg)](https://pypi.python.org/pypi/NotebookScripter)
[![Downloads](https://img.shields.io/pypi/dm/NotebookScripter.svg)](https://pypi.python.org/pypi/NotebookScripter)

This package exposes ipython jupyter notebooks as callable functions which can be used in python programs or scripts and parameterized externally.

The goal is to provide a simple way to reuse code developed/maintained in a notebook environment.

## Installation

```bash
> pip install NotebookScripter
```

## How to use

Suppose you have this notebook: [./Example.ipynb](./Example.ipynb). You can use the `NotebookScripter.run_notebook` method to execute it.

```pycon
>>> from NotebookScripter import run_notebook
>>> some_module = run_notebook("./Example.ipynb")
>>>
```

The call to `run_notebook()`:

1. creates an anonymous python module
1. execs all the code cell's within `Example.ipynb` sequentially in the context of that module
1. returns the module after all the cells have executed

Values or functions defined in the module scope within the notebook can be subsequently accessed:

```pycon
>>> print(some_module.some_useful_value)
You can access this variable on the module object returned
>>> some_module.hello("world")
Hello world
>>>
```

The `run_notebook()` execution model matches the mental model that a developer has when working within the notebook. Importantly - the notebook code is _not_ imported as a python module - rather, all the code within the notebook is re-run on each call to run_notebook(). The execution is similar to what a developer would expect when working interactively in the notebook and dispatching code to a jupyter kernel.

If desired, values can be injected into the notebook for use during notebook execution by passing keyword arguments to `run_notebook`.

```pycon
>>> another_module = run_notebook('./Example.ipynb', a_useful_mode_switch="idiot_mode")
Hello Flat Earthers!
>>>
```

Within the notebook, use the `NotebookScripter.receive_parameter()` method to receive parameters from the outside world.

```python
a_useful_mode_switch = receive_parameter(a_useful_mode_switch=None)
```

In this call -- `a_useful_mode_switch="idiot_mode"` is passed to run_notebook as a keyword parameter which causes the call to receive_parameter(a_useful_mode_switch=None) within the notebook to return `"idiot_mode"` rather than `None`.

`receive_parameter()` requires a single keyword argument. If a matching keyword argument was supplied to the call to `run_notebook()` then the externally provided value is returned from `receive_parameter()` otherwise the notebook defined default value is returned. This api ensures all parameters have default values defined appropriate for interactive notebook use while also identifying those parameters that make sense to provide externally.

## Dealing with matplotlib

`run_notebook` supports an configuration option `with_matplotlib_backend` which defaults to 'agg'. `run_notebook` registers its own handler based on this option for `%matplotlib` ipython line magic -- this handler replaces the argument supplied in the cell with the value configured by NotebookScripter. For example -- suppose you had a jupyter cell with contents like the following:

```pycon
%matplotlib inline

import matplotlib.pyplot as plt
# ...<some script that also produces plots>...
```

When executed via run_notebook(...) - the line `%matplotlib inline` will instead be interpreted like `%matplotlib agg`.

This functionality supports 'interactive' plotting backend selection in the notebook environment and 'non-interactive' backend selection in the scripting context. 'agg' is a non-interactive backend built into most distributions of matplotlib.

You can change the backend selection used by NotebookScripter by calling `NotebookScripter.set_notebook_option(with_matplotlib_backend="somebackend")` To disable this functionality entirely provide `with_matplotlib_backend=None`.

## Recursive run_notebook execution

When run_notebook is invoked recursively, receive_parameter() will locate parameters by searching up the logical stack parameters passed to run_notebook invocations until it finds a match.

Example:

```python
from NotebookScripter import run_notebook
run_notebook("./parent.py", grandparent="grandparent")
```

parent.py

```python
from NotebookScripter import run_notebook
run_notebook("child.py")
```

child.py

```python
from NotebookScripter import receive_parameter
param = receive_parameter(grandparent=None)

print("Printed value will be "grandparent" rather than None: {0}".format(grandparent))
```

receive_parameter found the value for 'grandparent' that was passed to the ancestor call to run_notebook despite the fact that the `run_notebook` call in parent.py passed no parameters.

## Execute a notebook in isolated subprocess

`run_notebook` executes notebook's within the same process as the caller. Sometimes more isolation between notebook executions is desired or required. NotebookScripter provides a run_notebook_in_process function for this case:

```pycon
>>> from NotebookScripter import run_notebook_in_process

# run notebook in subprocess -- note there is no output in doctest as output occurs in subprocess
>>> module = run_notebook_in_process("./Example.ipynb", a_useful_mode_switch="idiot_mode")()
>>>
```

`run_notebook_in_process` executes the notebook asynchronously in another process and returns a callable function. When called the returned function will block until the notebook execution completes and a similar anonymous module will be returned to the caller as with `run_notebook`. Unlike `run_notebook` however, `run_notebook_in_process` cannot return the entire underlying module as Python modules are not transferrable across process boundaries. It's still possible to retrieve serializable state from the child process though. Return values can be retrieved by passing the string's to the callable method returned from run_notebook_in_process. Variables from the module scope matching the names passed will be serialized, transferred from the subprocess back to the calling process, deserialized, and included in the anonymous module. All requested values must be pickle serializable (otherwise, their repr() will be returned).

```pycon
>>> module = run_notebook_in_process("./Example.ipynb", a_useful_mode_switch="non_idiot_mode")("some_useful_value")
>>> print(module.some_useful_value)
You can access this variable on the module object returned
>>>
```

## Use run_notebook on notebooks imported into VSCode

VSCode supports an integrated [jupyter workflow](https://blogs.msdn.microsoft.com/pythonengineering/2018/11/08/python-in-visual-studio-code-october-2018-release/).

1. Install the Microsoft Python VSCode extension -- https://code.visualstudio.com/docs/languages/python
1. Open a .ipynb file in vscode and choose to 'Import Jupyter Notebook'. This will convert the .ipynb file into a .py file by extracting the text contents of the cells.

You now have your notebook represented as a text file which is editable in vscode. VSCode represents the division between cells with special comment:
`# %%`
Cells can be executed within VSCode via 'Run Cell' code lens or keybindings. With your code encoded this way you can dispatch your code to a jupyter kernel for interactive inspection or execute the notebook in the vscode debugger.

Since your code is now in a regular python file, you can import it from other python modules -- but its very likely not to be usable without changes. You very probably designed this code to run well inside notebook's with code executing at module scope that will now be run as a side effect of import. With python's import behavior, you will have no way to re-invoke this code or pass parameters to it. Rather than importing your .py encoded notebook, what you probably want is a way to _invoke_ it -- which you can use `run_notebook()` to do.

`run_notebook` supports .py files and executes them with the same (nearly the same) semantics as would have been used to run the equivalent code in a .ipynb file. `run_notebook()` takes care to support the debugger -- so you should be able to set breakpoints normally within files executed via calls to `run_notebook()`.

## Why

A friend of mine was working on a complex analysis for her PhD thesis in an ipython jupyter notebook. She was reasonably familiar with the jupyter workflow which, by design, tends to force you into defining parameters/state as module globals where they can be easily accessed from subsequent cells. She organized her notebook nicely, with plots and various tools for sanity checking intermediate states of her complicated and hairy chain of computations -- with some of those steps also taking a somewhat long time to run. Sometime near the end of designing this analysis, she realized she would need to run this notebook processing chain a few hundred times with different values for some parameters which she had discovered controlled the important dynamics of her problem. I'm fond of typed languages and expected this would be relatively easy to refactor so I leaned in to help when I heard her groan. I quickly realized -- in fact -- no, this refactor would not be so simple.

- Python is extremely difficult to refactor - even relatively simple mechanical transformations are essentially rewrites in terms of required debugging time - and even simple changes are frustrating to make when reorganizing code that takes a long time to run
- Code written in the workflow of jupyter notebooks tends to be even harder still to reorganize. The notebook workflow encourages you to define variables and parameters on the module scope so that you have easy access to these values in subsequent cells. The code in the notebook tends to be linear with things defined in later cells able to depend on _anything_ defined before which can make extracting arbitrary parameters from portions of the notebook into normal code reuse units require significant changes to the logic of the notebook. Furthermore -- one of the _reasons_ notebook's are convenient to share is precisely the combination of linear readability plus interactive access to intermediate computation states.
- Using normal code reuse abstractions can often make it _harder_ to read, reason about, and deal with your notebooks interactively. In notebooks, its typical to write your process linearly as a sequence of transformations of the module scope. You end up with the controlling parameters for your problem defined on module scope with your process taking the form of some sequence of transformations to the module scope. You often will have useful intermediate computation states stashed in module scope so that you can inspect and experiment interactively from relevant points in the process. When you try to restructure your code so that parameters are passed into function calls, you can end up hiding useful intermediate state within function bodies where they cannot be so readily inspected/modified interactively.
- Extracting the code from the notebook and turning it into a form that allows normal parameterization _loses_ some of the utility of the original process description. If she discovers, after refactoring her code, an unexpected issue that occurs when processing one of the hundreds of variations of parameters -- its not going to be possible to dive in and investigate the specifics of that parameter set with the same easy access to all the intermediate computation states that she had when developing the process originally. To make her process parameterizable, she will have been forced to rewrite her code in a way that makes it hard or impossible to continue taking advantage of the interactive computing model.

Refactoring her code to run all the problem instances for her analysis within the notebook would be error prone, make the notebook harder to interact with, make the notebook harder to read, and would impose lengthy debugging time to validate the reorganized code in the presence of long-running computations. The refactor loses the simple linear read-ability of the original code and the ability to efficiently interact with intermediate computation states. `run_notebook` provides an easy way to convert a notebook into a re-useable unit of computation - a function (perhaps the easiest and most powerful form of code re-use) - without having to make these sacrifices.

## Comparison to other methods

_nbconvert_ - allows one to do a one-time conversion from .ipynb format to a .py file. It does the work of extracting code from the .ipynb format. This is useful but doesn't directly extract re-runnable 'work flows' from the typical sequences of instructions one would interactively define on the notebook module scope. Typically one would have to change the code output by nbconvert to make use of it in a script or program -- and those chnages would turn that code into a form that was less useable for interactive development.

_vscode's vscode-python_ - performs a conversion to a .py file (similar to nbconvert) and also provides a jupyter notebook like development flow on top of the raw .py files with various advantages over the .ipynb format (editors, revision control). The VSCode plugin _also_ allows you to re-export your .py output back to .ipynb files for convenient sharing/publishing. The functionality provided by vscode-python is great -- but similar to _nbconvert_ code imported from a notebook is likely to need a lot of change before it can be re-used -- and the changes required are very likely to make the code _no longer_ work well with a notebook development mindset.

_NotebookScripter_ allows one to directly invoke notebook code from scripts and applications without having to extensively change the way the code is written. You can keep code in a form that is tailored for interactive use within a notebook, continue to develop and interact with that code with a notebook workflow and easily invoke that notebook from python programs or scripting contexts with externally provided parameters when needed. Notebook files themselves can be encoded as either jupyter .ipynb files or as vscode-python/nbconvert style .py files.

## How to Develop

See [DEVELOPMENT_README.md](DEVELOPMENT_README.md)

## Changelog

### 5.0.0

- API Change: Remove search_parents option -- the new behavior (corresponding to search_parents=True) is now the only behavior
- API Change: remove `with_backend` parameter from run_notebook and replace with `set_notebook_option()` api

  ```
  NotebookScripter.set_notebook_option(with_matplotlib_backend="some_backend")
  ```

- Use `spawn` when creating a subprocess within `run_notebook_in_process` rather than the default which is to fork on unix and spawn on windows. This provides better cross-platform compatibility, improves isolation between subprocess executions, and allows for better debugger behavior.

- API Change: new api for `run_notebook_in_process`:

  - run_notebook_in_process now runs the notebook in a subprocess asynchronously and returns a closure which when called will block until the notebook execution completes
  - the `return_values` parameter is removed from run_notebook_in_process and moved onto the callable
  - to convert from old api to new:

    old

    ```python
    run_notebook_in_process(some_file, return_values=['some_param1', 'some_param2'], some_argument='foo')
    ```

    can be directly rewritten as

    ```python
    run_notebook_in_process(some_file, some_argument='foo')('some_param1', 'some_param2')
    ```

    or like this with argument splatting

    ```python
    run_notebook_in_process(some_file, some_argument='foo')(*['some_param1', 'some_param2'])
    ```

### 4.0.1

- Fix error in setup.py's notion of package version.

### 4.0.0

- Change error handling of run_notebook_in_process -- exception's raised in subprocess will be reraised in caller (wrapped inside a NotebookScripterWrappedException)

### 3.2.0

- Add search_parents option to run_notebook and run_notebook_in_process (defaults to False)

### 3.1.3

- Minor changes to boost test coverage %

### 3.1.0

- Support debugger when invoking .py files via run_notebook()

### 3.0.0

- Api changes to allow NotebookScripter to work well with vscode's
  [jupyter features](https://blogs.msdn.microsoft.com/pythonengineering/2018/11/08/data-science-with-python-in-visual-studio-code/)

### 2.0.0

- Update Cell Metadata api and documentation
- Add doctests and integrate with tests
- Fix code coverage and code health CI integration

### 1.0.5

- Fix buggy behavior that occured when running from python interactive shell associated with ipython embedding api behavior

### 1.0.1

- Added documentation and initial implementation.
- Added package build/release automation.
- Added simple tests.

### 1.0.0

- Initial build
