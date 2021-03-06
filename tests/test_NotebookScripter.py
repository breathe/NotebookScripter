import os
import snapshottest

import NotebookScripter
from NotebookScripter._main import worker

from unittest.mock import patch


def filterKeys(aDict, filtered):
    return {k: v for (k, v) in aDict.items() if k not in filtered}


# pylint: disable=E1101


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
        mod = NotebookScripter.run_notebook_in_process(self.notebook_file)("parameterized_name", "french_mode")
        self.assertMatchSnapshot(filterKeys(mod.__dict__, ["__file__"]))

    def test_run_notebook_in_process_with_hooks(self):
        return_values = ["parameterized_name", "french_mode", "greeting_string"]
        mod = NotebookScripter.run_notebook_in_process(self.notebook_file, parameterized_name="external world")(*return_values)
        self.assertMatchSnapshot(filterKeys(mod.__dict__, ["__file__"]))

        mod = NotebookScripter.run_notebook_in_process(self.notebook_file, parameterized_name="external world2", french_mode=True)(*return_values)
        self.assertMatchSnapshot(filterKeys(mod.__dict__, ["__file__"]))

    def test_run_notebook_in_jupyter(self):
        mod = NotebookScripter.run_notebook_in_jupyter(self.notebook_file)("parameterized_name", "french_mode")
        self.assertMatchSnapshot(filterKeys(mod.__dict__, ["__file__", "__serialized_notebook__"]))

    def test_run_notebook_in_jupyter_with_hooks(self):
        return_values = ["parameterized_name", "french_mode", "greeting_string"]
        mod = NotebookScripter.run_notebook_in_jupyter(self.notebook_file, parameterized_name="external world")(*return_values)
        self.assertMatchSnapshot(filterKeys(mod.__dict__, ["__file__", "__serialized_notebook__"]))

        mod = NotebookScripter.run_notebook_in_jupyter(self.notebook_file, parameterized_name="external world2", french_mode=True)(*return_values)
        self.assertMatchSnapshot(filterKeys(mod.__dict__, ["__file__", "__serialized_notebook__"]))

    def test_run_with_backend_is_used(self):
        with self.assertRaises(Exception) as context:
            with patch('NotebookScripter._main.__notebookscripter_injected__', [[{}, {}]]):
                NotebookScripter.set_notebook_option(with_matplotlib_backend="somefake")
                NotebookScripter.run_notebook(self.notebook_file)
        print(str(context.exception))
        self.assertTrue("Unrecognized backend string 'somefake'" in str(context.exception))

    def test_magics_are_unregistered(self):
        mod = NotebookScripter.run_notebook(self.notebook_file)
        shell = mod.get_ipython()
        self.assertMatchSnapshot(shell.magics_manager.magics.get("line").get("matplotlib").__name__)


class TestWorkerExecution(snapshottest.TestCase):
    def setUp(self):
        self.notebook_file = os.path.join(os.path.dirname(__file__), "./Samples.ipynb")

    def test_worker(self):
        return_values = ["parameterized_name", "french_mode", "greeting_string", "hello"]

        class FakeQueue(object):
            def __init__(self):
                self._items = []

            def put(self, item):
                self._items.append(item)

            def get(self):
                return return_values

        parent_to_child_queue = FakeQueue()
        child_to_parent_queue = FakeQueue()
        notebook = self.notebook_file
        parent_parameters = [[{}, {}]]
        hooks = {"parameterized_name": "external world"}

        worker(parent_to_child_queue, child_to_parent_queue, notebook, parent_parameters, **hooks)
        _, mod = child_to_parent_queue._items[0]

        hello_repr = mod.pop("hello", None)
        self.assertTrue("function" in hello_repr)
        self.assertMatchSnapshot(mod)


class TestExecutePyFileAsNotebook(TestNotebookExecution):
    def setUp(self):
        self.notebook_file = os.path.join(os.path.dirname(__file__), "./Samples.pynotebook")


class TestNotebookRender(snapshottest.TestCase):
    def setUp(self):
        self.notebook_file = os.path.join(os.path.dirname(__file__), "./Samples.pynotebook")
        self.output_file = os.path.join(os.path.dirname(__file__), "./test.ipynb")

    def test_render_notebook_from_vscode_style_pyfile(self):
        NotebookScripter.run_notebook_in_jupyter(self.notebook_file)("parameterized_name", "french_mode", save_output_notebook=self.output_file)


class TestRecursiveNotebookExecution(snapshottest.TestCase):
    def setUp(self):
        self.notebook_file = os.path.join(os.path.dirname(__file__), "./RecursiveSamples.pynotebook")
        self.testcase1_file = os.path.join(os.path.dirname(__file__), "./RecursiveSamples_1.pynotebook")
        self.testcase2_file = os.path.join(os.path.dirname(__file__), "./RecursiveSamples_2.pynotebook")

    def test_run(self):

        for testcase in [self.testcase1_file, self.testcase2_file]:
            mod = NotebookScripter.run_notebook(self.notebook_file, parameter=testcase)
            value = mod.value
            self.assertMatchSnapshot(value)


class TestSearchParents(snapshottest.TestCase):
    """Test search_parents option"""

    def setUp(self):
        self.notebook_file = os.path.join(os.path.dirname(__file__), "./SearchParents_1.pynotebook")

    def test_run_recursive(self):
        NotebookScripter.run_notebook(self.notebook_file, a="grandparent_a")

    def test_run_in_subprocess_recursive(self):
        NotebookScripter.run_notebook_in_process(self.notebook_file, a="grandparent_a")()


class TestException(snapshottest.TestCase):
    """Test search_parents option"""

    def setUp(self):
        self.notebook_file = os.path.join(os.path.dirname(__file__), "./TestException.pynotebook")

    def test_run_with_exception(self):
        self.assertRaises(AssertionError, NotebookScripter.run_notebook, self.notebook_file)

    def test_run_in_subprocess_with_exception(self):
        run_in_process = NotebookScripter.run_notebook_in_process(self.notebook_file)
        self.assertRaises(NotebookScripter.NotebookScripterWrappedException, run_in_process)
