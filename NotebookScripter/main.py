
import types
import io
import typing

from IPython import get_ipython
from IPython.core.interactiveshell import InteractiveShell
from IPython.terminal.embed import InteractiveShellEmbed
from IPython.core.magic import Magics, magics_class, line_magic

from traitlets import Bool, CBool, Unicode
from traitlets.config import MultipleInstanceError

from nbformat import read


class NotebookScripterEmbeddedIpythonShell(InteractiveShell):

    def init_sys_modules(self):
        """Override this to create an ipython shell appropriate for embedding similar to InteractiveShellEmbed.

        Needed to avoid creating new global namespace when running from command line console.
        """
        pass

    def init_prompts(self):
        """Override: don't mutate shell prompts.  Needed to avoid overtaking the interactive shell when this code is run from `python` command line console."""
        # Set system prompts, so that scripts can decide if they are running
        # interactively.
        # sys.ps1 = 'In : '
        # sys.ps2 = '...: '
        # sys.ps3 = 'Out: '


def register_magic(shell_instance, magic_cls):
    """
    Registers the provided shell_instance from IPython.

    Returns a function which undoes this.

    Rant: Why the f... does IPython not define it's own unregister function?

    :param magic_cls: The Magics class you wish to register.
    """

    # ugh I hate this code and I hate python so much ...
    undoes = {}
    original_magics = shell_instance.magics_manager.magics
    for magic_type, names in magic_cls.magics.items():
        if magic_type in original_magics:
            for magic_name, _ in names.items():
                if magic_name in original_magics[magic_type]:
                    undoesNamedMagics = undoes.setdefault(magic_type, {})
                    undoesNamedMagics[magic_name] = original_magics[magic_type][magic_name]

    shell_instance.register_magics(magic_cls)

    def unregister_magics():
        for magic_type, magic_names in undoes.items():
            for magic_name, magic_value in magic_names.items():
                shell_instance.magics_manager.magics[magic_type][magic_name] = magic_value

    return unregister_magics


def run_notebook(
        path_to_notebook: str,
        initial_values_for_ns: typing.Dict = None,
        with_backend='agg'
) -> typing.Any:
    """Run a notebook as a module within this processes namespace"""

    try:
        shell = NotebookScripterEmbeddedIpythonShell.instance()
    except MultipleInstanceError:
        # we are already embedded into an ipython shell -- just get that one.
        shell = get_ipython()

    unregister_magics = None

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

        unregister_magics = register_magic(shell, NotebookScripterMagics)

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
        # revert the magics changes ...
        if unregister_magics:
            unregister_magics()
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
