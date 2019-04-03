
import types
import io
import os
import sys
import traceback
import typing

from IPython import get_ipython
from IPython.core.interactiveshell import InteractiveShell
from IPython.core.magic import Magics, magics_class, line_magic

from traitlets.config import MultipleInstanceError

from nbformat import read as read_notebook


# Holds values to be injected into module execution context via receive_parameter
__notebookscripter_injected__ = []


def init_injected_parameters(injected_parameters, run_settings):
    __notebookscripter_injected__.append([injected_parameters, run_settings])


def deinit_injected_parameters():
    __notebookscripter_injected__.pop()


def receive_parameter(**kwords):
    """Receive parameters from the outside world.

    Exactly 1 keyword argument is required -- the key gives the parameter a name and
    the value provides the the 'default' value for the parameter.

    The default value is returned if the parameter was not provided in the
    call to run_notebook.
    """

    # can't do this because kword argument order is not preserved in some python versions ...
    if len(kwords) != 1:
        raise ValueError("Exactly 1 kword argument must be passed to receive_parameter")

    last_parameter_namespace, options_namespace = __notebookscripter_injected__[-1] if __notebookscripter_injected__ else [{}, {}]

    if options_namespace.get("search_parents", None):
        namespaces_to_search = [i for i, _ in __notebookscripter_injected__]
    else:
        namespaces_to_search = [last_parameter_namespace]

    ret = []

    # search the namespaces in reverse order
    param_name, default_value = next(iter(kwords.items()))
    for module_namespace in reversed(namespaces_to_search):
        if param_name in module_namespace:
            ret.append(module_namespace[param_name])

    # search space did not contain item -- use default value
    if not ret:
        ret.append(default_value)

    # return the found item
    return ret[0]


class NotebookScripterEmbeddedIpythonShell(InteractiveShell):

    def enable_gui(self, gui=None):
        pass

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
        with_backend='agg',
        search_parents: bool = False,
        **hooks
) -> typing.Any:
    """Run a notebook within calling process

    Args:
        path_to_notebook: Path to .ipynb or .py file containing notebook code
        with_backend: Override behavior of ipython's matplotlib 'magic directive' -- "% matplotlib inline"
        search_parents: receive_parameter() calls within the called notebook will search for parameters pass to any 'parent' invocations of run_notebook on the call stack, not just for parameters passed to this call
    Returns:
        Returns newly created (anonymous) python module in which the target code was executed.
    """
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

    # create new module scope for notebook execution
    module_identity = "loaded_notebook"
    dynamic_module = types.ModuleType(module_identity)
    dynamic_module.__file__ = path_to_notebook
    dynamic_module.__dict__['get_ipython'] = get_ipython

    # do some extra work to ensure that magics that would affect the user_ns
    # actually affect the notebook module's ns
    save_user_ns = shell.user_ns
    shell.user_ns = dynamic_module.__dict__

    init_injected_parameters(hooks, {
        "search_parents": search_parents
    })

    _, extension = os.path.splitext(path_to_notebook)
    if extension == ".ipynb":
        is_ipynb = True
    else:
        is_ipynb = False

    with io.open(path_to_notebook, 'r', encoding='utf-8') as f:
        if is_ipynb:
            notebook = read_notebook(f, 4)
        else:
            file_source = f.read()

    try:
        if is_ipynb:
            # execute ipynb notebook files
            for cell in notebook.cells:
                # loop over the code cells
                if cell.cell_type == 'code':
                    # transform the input to executable Python
                    code = shell.input_transformer_manager.transform_cell(
                        cell.source)

                    # run the code in the module
                    exec(code, dynamic_module.__dict__)

                    # # inject caller provided values into the module namespace after execution of any hook cells
                    # if 'metadata' in cell and 'NotebookScripterHookName' in cell.metadata:
                    #     hook_name = cell.metadata["NotebookScripterHookName"]
                    #     dynamic_module.__dict__.update(hooks.get(hook_name, {}))
        else:
            # execute .py files as notebooks
            code = shell.input_transformer_manager.transform_cell(file_source)

            # run the code in the module, compile first to provide source mapping support
            code_block = compile(code, path_to_notebook, 'exec')
            exec(code_block, dynamic_module.__dict__)
    finally:
        shell.user_ns = save_user_ns

        # revert the magics changes ...
        if unregister_magics:
            unregister_magics()

        # pop parameters stack
        deinit_injected_parameters()

    return dynamic_module


class NotebookScripterWrappedException(Exception):
    def __init__(self):
        exc_type, exc_value, exc_tb = sys.exc_info()
        self.exception = exc_value
        self.formatted = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))

    def __str__(self):
        return '%s\nOriginal traceback:\n%s' % (Exception.__str__(self), self.formatted)


def worker(queue, path_to_notebook, with_backend, search_parents, return_values, **hooks):
    try:
        dynamic_module = run_notebook(path_to_notebook, with_backend=with_backend, search_parents=search_parents, **hooks)

        if return_values:
            ret = {k: simple_serialize(dynamic_module.__dict__[k]) for k in return_values if k in dynamic_module.__dict__}
            queue.put((None, ret))
        else:
            queue.put((None, {}))
    except Exception:
        wrapped_exception = NotebookScripterWrappedException()
        queue.put((wrapped_exception, None))


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
    with_backend='agg',
    search_parents=False,
    return_values=None,
    **hooks
) -> None:
    """Run a notebook in a new subprocess

    Args:
        path_to_notebook: Path to .ipynb or .py file containing notebook code
        with_backend: Override behavior of ipython's matplotlib 'magic directive' -- "% matplotlib inline"
        search_parents: receive_parameter() calls within the called notebook will search for parameters pass to any 'parent' invocations of run_notebook on the call stack, not just for parameters passed to this call
        return_values: Optional array of strings to pass back from subprocess -- values matching these names in the module created by invoking the notebook in a subprocess will be serialized passed across process boundaries back to this process, deserialized and made part of the returned module
    Returns:
        Returns newly created (anonymous) python module
        populated with requested values retrieved from the subprocess
    """
    import multiprocessing as mp

    queue = mp.Queue()

    p = mp.Process(target=worker, args=(queue, path_to_notebook, with_backend, search_parents, return_values), kwargs=hooks)
    p.start()

    module_identity = "loaded_notebook_from_subprocess"
    dynamic_module = types.ModuleType(module_identity)
    dynamic_module.__file__ = path_to_notebook

    err, final_namespace = queue.get()
    p.join()

    if err:
        raise err

    # inject retrieved return values into the returned module namespace
    dynamic_module.__dict__.update(final_namespace)

    return dynamic_module
