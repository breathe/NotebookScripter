# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestNotebookExecution::test_run_notebook 1'] = 'Hello state1'

snapshots['TestNotebookExecution::test_run_notebook_in_process 1'] = {
    'stateful_name': 'state1'
}

snapshots['TestNotebookExecution::test_magics_are_unregistered 1'] = 'matplotlib'
