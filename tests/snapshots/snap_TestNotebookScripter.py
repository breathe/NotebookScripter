# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestNotebookExecution::test_magics_are_unregistered 1'] = 'matplotlib'

snapshots['TestNotebookExecution::test_run_notebook 1'] = 'Hello default world'

snapshots['TestNotebookExecution::test_run_notebook_in_process 1'] = {
    '__doc__': None,
    '__loader__': None,
    '__name__': 'loaded_notebook_from_subprocess',
    '__package__': None,
    '__spec__': None,
    'french_mode': None,
    'parameterized_name': 'default world'
}

snapshots['TestNotebookExecution::test_run_notebook_in_process_with_hooks 1'] = {
    '__doc__': None,
    '__loader__': None,
    '__name__': 'loaded_notebook_from_subprocess',
    '__package__': None,
    '__spec__': None,
    'french_mode': None,
    'parameterized_name': 'external world'
}

snapshots['TestNotebookExecution::test_run_notebook_in_process_with_hooks 2'] = {
    '__doc__': None,
    '__loader__': None,
    '__name__': 'loaded_notebook_from_subprocess',
    '__package__': None,
    '__spec__': None,
    'french_mode': True,
    'parameterized_name': 'external world2'
}

snapshots['TestNotebookExecution::test_run_notebook_with_hooks1 1'] = 'Hello external world'

snapshots['TestNotebookExecution::test_run_notebook_with_hooks2 1'] = 'Salut external world2'