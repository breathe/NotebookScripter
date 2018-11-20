# Notebookscripter [![Version](https://img.shields.io/pypi/v/NotebookScripter.svg)](https://pypi.python.org/pypi/NotebookScripter) [![Build](https://travis-ci.org/breathe/NotebookScripter.svg?branch=master)](https://travis-ci.org/breathe/NotebookScripter) [![Coverage](https://img.shields.io/coveralls/breathe/NotebookScripter.svg)](https://coveralls.io/r/breathe/NotebookScripter) [![Health](https://codeclimate.com/github/breathe/NotebookScripter/badges/gpa.svg)](https://codeclimate.com/github/breathe/NotebookScripter)

[![Compatibility](https://img.shields.io/pypi/pyversions/NotebookScripter.svg)](https://pypi.python.org/pypi/NotebookScripter)
[![Implementations](https://img.shields.io/pypi/implementation/NotebookScripter.svg)](https://pypi.python.org/pypi/NotebookScripter)
[![Format](https://img.shields.io/pypi/format/NotebookScripter.svg)](https://pypi.python.org/pypi/NotebookScripter)
[![Downloads](https://img.shields.io/pypi/dm/NotebookScripter.svg)](https://pypi.python.org/pypi/NotebookScripter)

This package exposes ipython jupyter notebooks as callable functions.

The goal is to provide a simple way to reuse code developed/maintained in a notebook environment by turning notebooks into callable python functions with parameters optionally supplied as arguments to the function call.

Unlike a tool like nbconvert, this module allows one to continue using the notebook as an interactive development environment. With nbconvert one does a one-time conversion of a notebook into a .py file, afterwards any changes you make to that .py file are no longer usable in a notebook context. Additionally with nbconvert there is no reasonable way to directly re-use 'work flows' defined as sequences of instructions on the module scope as one would typically do in a notebook when developing a complicated process.

With this module, you can keep code in unmodified notebooks, continue to develop/interact with that code within notebooks, and easily trigger that notebook code from external python programs or scripting contexts.

Usage:

## Execute a notebook as a function call

Suppose you have this notebook: [./Example.ipynb](./Example.ipynb)

```python
from NotebookScripter import run_notebook

some_module = run_notebook("./Example.ipynb")
```

The call to `run_notebook()`:

1. creates an anonymous python module
1. execs all the code cell's within `Example.ipynb` sequentially in the context of that module
1. returns the module after all the cells have executed.

Any values or functions defined in the module scope within the notebook can be subsequently accessed:

```python
print(some_module.some_useful_value)
some_module.hello()
```

This execution model matches the mental model that a developer has when working within the notebook. Importantly - the notebook code is not being imported as a python module - rather, all the code within the notebook is re-run on each call to run_notebook() just as a developer would expect when working interactively in the notebook.

If desired, initial values can be injected into the namespace of the module. These values are injected into the created module namespace prior to executing any of the notebook cell's.

```python
another_module = run_notebook("./Example.ipynb", {
  "a_useful_mode_switch": "idiot_mode"
})
```

In this case -- the value of `a_useful_mode_switch` selects idiot mode and the notebook prints: `Hello Flat Earthers`. But how -- if the notebook is still useable interactively, then it must mean that `a_useful_mode_switch` needs to be defined prior to being used and this would make our externally supplied value useless since they would be re-defined within the notebook prior to having any useful effect. `run_notebook` defines a simple convention to allow identifying which parameters of the notebook are intended to be supplied by an external caller. The convention is that `run_notebook` will only execute cells that _DO_NOT_ contain a cell metadata value like the following:

```json
    "NotebookScripter": "skip_cell"
```

In `Example.ipynb` This annotation is present in the cell metadata for the cell defining the `a_useful_mode_switch` variable.

This annotation can be added to any cell's which you do _NOT_ want to run when the notebook is executed by NotebookScripter. The pattern for turning notebook's into parameterizable workflows thus goes as follows:

1. create a cell and define default values for any parameters you want the caller to supply
2. annotate that cell with 'skip_cell' metadata.

When run interactively in the notebook, the values defined in that cell will be used for those parameters. When called externally, the caller should supply all the required values via the second argument to run_notebook.

## Dealing with matplotlib

`run_notebook` supports a third argument `with_backend` which defaults to 'agg'. `run_notebook` intercepts any usage of `%matplotlib` ipython line magic within the notebook and replaces the argument with the value supplied by this parameter. For example:

```python
%matplotlib inline

import matplotlib.pyplot as plt
# ...<some script that also produces plots>...
```

When executed via run_notebook(..., with_backend='agg') - the line `%matplotlib inline` will instead be interpreted like `%matplotlib agg`.

This functionality allows 'interactive' plotting backend selection in the notebook environment and 'non-interactive' backend selection in the scripting context. 'agg' is a non-interactive backend built into most distributions of matplotlib. To disable this functionality provide `with_backend=None`.

## Execute a notebook in isolated subprocess

`run_notebook` executes notebook's within the same process as the caller. Sometimes more isolation between notebook executions is desired or requeried. NotebookScripter provides a run_notebook_in_process function for this case:

```python
from NotebookScripter import run_notebook_in_process

# run notebook in subprocess
run_notebook_in_process("./example.ipynb", {"some_useful_paramer": "any_json_serializable_value"
})
```

Unlike `run_notebook`, `run_notebook_in_process` cannot return the module as Python modules are not transferrable across process boundaries. It's still possible to retrieve serializable state from the notebook though. Return values can be retrieved by passing the 'marshal_values' parameter. After executing the notebook, any variables on the module scope with these names will be serialized, transferred from the subprocess back to the calling process, deserialized and then returned as a python dictionary. All requested values must be pickle serializable (otherwise, their repr() will be returned).

```python
serialized_module_namespace = run_notebook_in_process("./example.ipynb",
  {'some_parameter': "any_json_serializable_value"},
  marshal_values: ["some_key_into_module_namespace_with_serializable_value"]
)
```

Installation:

```bash
> pip install NotebookScripter
```

## Changelog

### 1.0.1

- Added documentation and initial implementation.
- Added package build/release automation.
- Added simple tests.

### 1.0.0

- Initial build
