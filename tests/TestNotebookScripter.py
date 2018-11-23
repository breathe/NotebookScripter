import os
import snapshottest

import NotebookScripter


def filterKeys(aDict, filtered):
    return {k: v for (k, v) in aDict.items() if k not in filtered}


class TestNotebookExecution(snapshottest.TestCase):
    def setUp(self):
        self.notebook_file = os.path.join(os.path.dirname(__file__), "./Samples.ipynb")

    def test_run_notebook(self):
        mod = NotebookScripter.run_notebook(self.notebook_file)
        value = mod.hello()
        print(value)
        self.assertMatchSnapshot(value)

    def test_run_notebook_with_hooks1(self):
        mod = NotebookScripter.run_notebook(self.notebook_file, parameterized_name="external world")
        value = mod.hello()
        self.assertMatchSnapshot(value)

    def test_run_notebook_with_hooks2(self):
        mod = NotebookScripter.run_notebook(self.notebook_file, parameterized_name="external world2", french_mode=True)
        value = mod.hello()
        self.assertMatchSnapshot(value)

    def test_run_notebook_in_process(self):
        mod = NotebookScripter.run_notebook_in_process(self.notebook_file, return_values=["parameterized_name", "french_mode"])
        self.assertMatchSnapshot(filterKeys(mod.__dict__, ["__file__"]))

    def test_run_notebook_in_process_with_hooks(self):
        mod = NotebookScripter.run_notebook_in_process(self.notebook_file,
                                                       return_values=["parameterized_name", "french_mode"],
                                                       parameterized_name="external world")
        self.assertMatchSnapshot(filterKeys(mod.__dict__, ["__file__"]))

        mod = NotebookScripter.run_notebook_in_process(self.notebook_file,
                                                       return_values=["parameterized_name", "french_mode"],
                                                       parameterized_name="external world2", french_mode=True)
        self.assertMatchSnapshot(filterKeys(mod.__dict__, ["__file__"]))

    def test_run_with_backend_is_used(self):
        with self.assertRaises(Exception) as context:
            NotebookScripter.run_notebook(self.notebook_file, with_backend="somefake")
        self.assertTrue("Unrecognized backend string 'somefake'" in str(context.exception))

    def test_magics_are_unregistered(self):
        mod = NotebookScripter.run_notebook(self.notebook_file)
        shell = mod.get_ipython()
        self.assertMatchSnapshot(shell.magics_manager.magics.get("line").get("matplotlib").__name__)


class TestExecutePyFileAsNotebook(TestNotebookExecution):
    def setUp(self):
        self.notebook_file = os.path.join(os.path.dirname(__file__), "./Samples.pynotebook")
