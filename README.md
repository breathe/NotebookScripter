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

Suppose you have this notebook: [./Example.ipynb](./Example.ipynb). You can use the NotebookScripter.run_notebook method to execute it.

```pycon

>>> from NotebookScripter import run_notebook
>>> some_module = run_notebook("./Example.ipynb")
>>>
```

The call to `run_notebook()`:

1. creates an anonymous python module
1. execs all the code cell's within `Example.ipynb` sequentially in the context of that module
1. returns the module after all the cells have executed.

Values or functions defined in the module scope within the notebook can be subsequently accessed:

```pycon
>>> print(some_module.some_useful_value)
You can access this variable on the module object returned from run_notebook
>>> some_module.hello("world")
Hello world
>>>
```

The run_notebook execution model matches the mental model that a developer has when working within the notebook. Importantly - the notebook code is not being imported as a python module - rather, all the code within the notebook is re-run on each call to run_notebook() just as a developer would expect when working interactively in the notebook.

If desired, values can be injected into the namespace of the notebook during notebook execution. The notebook author can define the parameter by calling `receive_parameter(some_param=some_default_value)`. If not overriden by the caller, receive_parameter will just return the provided default value otherwise the method will returned the value provided by the caller

```pycon
>>> another_module = run_notebook('./Example.ipynb', a_useful_mode_switch="idiot_mode")
Hello Flat Earthers!
>>>
```

In this call -- `a_useful_mode_switch` is passed to run_notebook as a keyword parameter which causes receive_parameter(a_useful_mode_switch=None) to return `"idiot_mode"` rather than `None`.

## Dealing with matplotlib

`run_notebook` supports an argument `with_backend` which defaults to 'agg'. `run_notebook` intercepts any usage of `%matplotlib` ipython line magic within the notebook and replaces the argument with the value supplied by this parameter. For example -- suppose you had a jupyter cell with contents like the following:

```pycon
%matplotlib inline

import matplotlib.pyplot as plt
# ...<some script that also produces plots>...
```

When executed via run_notebook(..., with_backend='agg') - the line `%matplotlib inline` will instead be interpreted like `%matplotlib agg`.

This functionality allows 'interactive' plotting backend selection in the notebook environment and 'non-interactive' backend selection in the scripting context. 'agg' is a non-interactive backend built into most distributions of matplotlib. To disable this functionality provide `with_backend=None`.

## Execute a notebook in isolated subprocess

`run_notebook` executes notebook's within the same process as the caller. Sometimes more isolation between notebook executions is desired or required. NotebookScripter provides a run_notebook_in_process function for this case:

```pycon
>>> from NotebookScripter import run_notebook_in_process

# run notebook in subprocess -- note there is no output in doctest as output occurs in subprocess
>>> module = run_notebook_in_process("./Example.ipynb", mode={"a_useful_mode_switch": "idiot_mode"})
>>>
```

Unlike `run_notebook`, `run_notebook_in_process` cannot return the module as Python modules are not transferrable across process boundaries. It's still possible to retrieve serializable state from the notebook though. Return values can be retrieved by passing the 'return_values' parameter. After executing the notebook, variables from the module scope matching the names passed will be serialized, transferred from the subprocess back to the calling process, deserialized, and an anonymous module with those names/values will be returned to the caller. All requested values must be pickle serializable (otherwise, their repr() will be returned).

```pycon
>>> module = run_notebook_in_process("./Example.ipynb", mode={"a_useful_mode_switch": "non_idiot_mode"}, return_values=["some_useful_value"])
>>> print(module.some_useful_value)
You can access this variable on the module object returned from run_notebook
>>>
```

## Use run_notebook on notebooks imported into VSCode

VSCode supports an integrated [jupyter workflow](https://blogs.msdn.microsoft.com/pythonengineering/2018/11/08/python-in-visual-studio-code-october-2018-release/).

1. Install the Microsoft Python VSCode extension -- https://code.visualstudio.com/docs/languages/python
1. Open a .ipynb file in vscode and choose to 'Import Jupyter Notebook'. This will convert the .ipynb file into a .py file by extracting the text contents of the cells.

You now have your notebook represented as a text file and editable in vscode. VSCode represents the division between cells with special comment:
`# %%`
and can execute cells with 'Run Cell' or keybindings. You can also launch the notebook in the vscode debugger.

What you can't do is reasonably reuse this imported code from another python module. You very probably designed your code to run well inside notebook's with code executing in module scope and running as a side effect of import. Rather than importing your .py module from other code what you want is a way to _invoke_ it -- which you can use `run_notebook()` to do.

`run_notebook` supports .py files and executes them with the same (nearly the same) semantics as would have been used to run the equivalent code in a .ipynb file. You should also be able to use the debugger within files executed via `run_notebook`.

## Why

A friend of mine was working on a complex analysis for her PhD thesis in an ipython jupyter notebook. She was reasonably familiar with the jupyter workflow -- which by design, tends to force you into defining parameters/state as module globals where they can be easily accessed from subsequent cells. She organized her notebook nicely, with plots and various forms of sanity checking for a complicated, hairy, and time-consuming chain of computations. Sometime near when she was finished designing the analysis, she realized she would need to run this notebook a few hundred times with different values for the parameters which she had discovered controlled the dynamics for her problem. I'm fond of typed languages and expected this would be relatively easy to refactor so I leaned in to help when I heard her groan. I quickly realized -- in fact -- no, this refactor would not be so simple.

- Python is extremely difficult to refactor - even relatively simple mechanical transformations are essentially rewrites in terms of required debugging time
- Code written in the workflow of jupyter notebooks tends to be even harder still to reorganize. The notebook workflow encourages you to define variables and parameters on the module scope so that you have easy access to these values from other cells. In fact -- one of the _reasons_ notebook's are convenient to use is precisely this implicit sequential chaining. The code in the notebook is linear -- things defined in later cells depend on _anything_ defined before which often makes extracting arbitrary parameters into normal code reuse units like functions a pretty major change to the logic of the notebook.
- Normal code reuse abstractions like functions often make it _harder_ to read, reason about, and deal with your notebooks interactively. In many cases, its much simpler to write as much of your process linearly as you can -- with all the parameters in scope given values describing a single instance of the problem so that you can inspect and edit interactively at any relevant point in the process rather than hiding code inside function scopes which cannot be so readily inspected/modified interactively
- Extracting the code from the notebook and turning it into a form that can be parameterized _loses_ the simplicity of the process description -- if she discovers when running this process with the hundreds of variations required, that some specific case needs more analysis -- its not possible to go back from the refactored code back to the simpler version that she can work with interactively to delve into the complex problem specific details.

Refactoring her code to run all the problem instances for her analysis within the notebook would be error prone, make the notebook harder to interact with, and make the notebook harder to read (for a reader trying to understand the process). The benefits and conveniences of notebooks (shareability, ease of interacting with intermediate computation states) are lessened after the restructuring needed to extract a parameterizable function from a notebook intended to describe a single complicated process.

## Comparison to other methods

Compared to a tool like nbconvert, this module allows one to continue using the notebook as an interactive development environment without change. With nbconvert one does a one-time conversion of a notebook into a .py file, afterwards any changes you make to that .py file are no longer usable in a notebook context. Additionally with nbconvert there is no reasonable way to directly extract re-runnable 'work flows' from the typical sequences of instructions one would interactively define on the notebook module scope.

With this module, you can keep code in unmodified notebooks tailored for interactive use on specific instances of problems, continue to develop and interact with that code within notebooks, and easily trigger that notebook code from external python programs or scripting contexts with differerent parameters if needed.

## How to Develop

See [DEVELOPMENT_README.md](./DEVELOPMENT_README.MD)

## Changelog

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
