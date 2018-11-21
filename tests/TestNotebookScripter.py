import os
import snapshottest

import NotebookScripter


class TestNotebookExecution(snapshottest.TestCase):
    def setUp(self):
        pass

    def test_run_notebook(self):
        notebook_file = os.path.join(os.path.dirname(__file__), "./Test.ipynb")
        mod = NotebookScripter.run_notebook(notebook_file, with_backend='agg')
        value = mod.hello()
        print(value)
        self.assertMatchSnapshot(value)

    def test_run_notebook_in_process(self):
        notebook_file = os.path.join(os.path.dirname(__file__), "./Test.ipynb")
        values = NotebookScripter.run_notebook_in_process(notebook_file, marshal_values=["stateful_name", "asdf"], with_backend='agg')
        print(values)
        self.assertMatchSnapshot(values)

    def test_run_with_backend_is_used(self):
        notebook_file = os.path.join(os.path.dirname(__file__), "./Test.ipynb")

        with self.assertRaises(Exception) as context:
            NotebookScripter.run_notebook(notebook_file, with_backend="somefake")
        self.assertTrue("Unrecognized backend string 'somefake'" in str(context.exception))

    def test_magics_are_unregistered(self):
        notebook_file = os.path.join(os.path.dirname(__file__), "./Test.ipynb")
        mod = NotebookScripter.run_notebook(notebook_file, with_backend="agg")
        shell = mod.get_ipython()
        self.assertMatchSnapshot(shell.magics_manager.magics.get("line").get("matplotlib").__name__)
