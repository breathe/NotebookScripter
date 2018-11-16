
import types
import io
import typing

from IPython import get_ipython
from IPython.core.interactiveshell import InteractiveShell
from IPython.core.magic import Magics, magics_class, line_magic

from nbformat import read


def run_notebook(
        path_to_notebook: str,
        initial_values_for_ns: typing.Dict = None,
        with_backend='agg'
) -> typing.Any:
    """Run a notebook as a module within this processes namespace"""

    shell = InteractiveShell.instance()

    if with_backend:
        try:
            # try to initialize the matplotlib backend as early as possible
            # (cuts down on potential for complex bugs)
            import matplotlib
            matplotlib.use(with_backend, force=True)
        except ModuleNotFoundError:
            # don't error out here when matplotlib is missing -- instead there will be
            # a failure within the notebook if notebook actually tries to use
            # matplotlib ...
            pass

        @magics_class
        class NotebookScripterMagics(Magics):
            @line_magic
            def matplotlib(self, _line):
                "Override matplotlib magic to use non-interactive backend regardless of user supplied argument ..."
                import matplotlib
                matplotlib.use(with_backend, force=True)

        shell.register_magics(NotebookScripterMagics)

    # load the notebook object
    with io.open(path_to_notebook, 'r', encoding='utf-8') as f:
        notebook = read(f, 4)

    # create new module scope for notebook execution
    module_identity = "loaded_notebook"
    dynamic_module = types.ModuleType(module_identity)
    dynamic_module.__file__ = path_to_notebook
    dynamic_module.__dict__['get_ipython'] = get_ipython

    # do some extra work to ensure that magics that would affect the user_ns
    # actually affect the notebook module's ns
    save_user_ns = shell.user_ns
    shell.user_ns = dynamic_module.__dict__

    # inject provided values into the module namespace prior to running any cells
    dynamic_module.__dict__.update(initial_values_for_ns or {})

    try:
        for cell in notebook.cells:
            # loop over the code cells
            if cell.cell_type == 'code':
                # skip cells which contain 'skip_cell_when_run_as_script' metadata
                if 'metadata' in cell and 'NotebookScripter' in cell.metadata and cell.metadata['NotebookScripter'] == "skip_cell":
                    # print("Skipping cell {0}!".format(i))
                    continue
                else:
                    # transform the input to executable Python
                    code = shell.input_transformer_manager.transform_cell(
                        cell.source)
                    # run the code in the module
                    exec(code, dynamic_module.__dict__)
    except Exception as err:
        raise err
    finally:
        shell.user_ns = save_user_ns
    return dynamic_module


def worker(queue, path_to_notebook, initial_values_for_ns, with_backend, return_values):
    dynamic_module = run_notebook(path_to_notebook, initial_values_for_ns=initial_values_for_ns, with_backend=with_backend)

    if return_values:
        ret = {k: simple_serialize(dynamic_module.__dict__[k]) for k in return_values if k in dynamic_module.__dict__}
        queue.put(ret)


def simple_serialize(obj):
    import pickle
    try:
        pickle.dumps(obj)
        # if we didn't raise, then (theoretically) obj should be serializable ...
        return obj
    except Exception:
        return repr(obj)


def run_notebook_in_process(
        path_to_notebook: str,
        initial_values_for_ns: typing.Dict = None,
        marshal_values=None,
        with_backend='agg'
) -> None:
    import multiprocessing as mp

    queue = mp.Queue()

    p = mp.Process(target=worker, args=(queue, path_to_notebook, initial_values_for_ns, with_backend, marshal_values))
    p.start()

    if not marshal_values:
        p.join()
        return {}

    final_namespace = queue.get()
    p.join()
    return final_namespace
