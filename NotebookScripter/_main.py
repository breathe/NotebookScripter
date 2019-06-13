
import types
import io
import os
import sys
import traceback
import typing
import pickle
import codecs

from IPython import get_ipython
from IPython.core.interactiveshell import InteractiveShell
from IPython.core.magic import Magics, magics_class, line_magic

from traitlets.config import MultipleInstanceError

from nbformat import read as read_notebook


# Holds values to be injected into module execution context via receive_parameter/__receive_options
__notebookscripter_injected__ = [[{}, {}]]


def __add_parameter_frame(injected_parameters):
    global __notebookscripter_injected__
    __notebookscripter_injected__ += [[injected_parameters, {}]]


def __pop_parameter_frame():
    __notebookscripter_injected__.pop()


def set_notebook_option(
    **kwords
):
    """
    Customize run_notebook behavior.  Parameters:

    with_matplotlib_backend: Override behavior of ipython's matplotlib 'magic directive' -- by default reinterprets "%matplotlib inline" as "%matplotlib agg" -- set to None to disable

    """
    valid_parameters = ["with_matplotlib_backend"]
    for key, value in kwords.items():
        if key not in valid_parameters:
            raise ValueError(f"Unknown notebook configuration parameter: {key} -- valid parameters {','.join(valid_parameters)}")
        elif key == "with_matplotlib_backend":
            __notebookscripter_injected__[-1][1][key] = value


def __receive_option(**kwords):
    """Receive configuration options.

    Exactly 1 keyword argument is required -- the key gives the option a name and
    the value provides the the 'default' value for the parameter.

    The default value is returned if the parameter was not provided in a call to set_notebook_option
    """

    if len(kwords) != 1:
        raise ValueError("Exactly 1 kword argument must be passed to receive_option")

    namespaces_to_search = [i for _, i in __notebookscripter_injected__]
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

    namespaces_to_search = [i for i, _ in __notebookscripter_injected__]
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
        **hooks
) -> typing.Any:
    """Run a notebook within calling process

    Args:
        path_to_notebook: Path to .ipynb or .py file containing notebook code
    Returns:
        Returns newly created (anonymous) python module in which the target code was executed.
    """
    try:
        shell = NotebookScripterEmbeddedIpythonShell.instance()
    except MultipleInstanceError:
        # we are already embedded into an ipython shell -- just get that one.
        shell = get_ipython()

    unregister_magics = None

    with_backend = __receive_option(with_matplotlib_backend="agg")

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

    __add_parameter_frame(hooks)

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
        __pop_parameter_frame()

    return dynamic_module


class NotebookScripterWrappedException(Exception):
    def __init__(self):
        exc_type, exc_value, exc_tb = sys.exc_info()
        self.exception = exc_value
        self.formatted = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))

    def __str__(self):
        return '%s\nOriginal traceback:\n%s' % (Exception.__str__(self), self.formatted)


def worker(parent_to_child_queue, child_to_parent_queue, path_to_notebook, all_parent_parameters, **hooks):
    try:
        global __notebookscripter_injected__
        # at this point we are in a new spawned -- and __notebook_scripter_injected__ is equal to [{}, {}]
        # update it to hold the value passed in from the calling process
        __notebookscripter_injected__ = all_parent_parameters

        # then run the notebook
        dynamic_module = run_notebook(path_to_notebook, **hooks)

        # now get the return values requested by the caller from the module, serialize them, then pass them back to the calling process
        return_values = parent_to_child_queue.get()

        if return_values:
            ret = serialize_return_values(dynamic_module.__dict__, return_values)
            child_to_parent_queue.put((None, ret))
        else:
            child_to_parent_queue.put((None, {}))
    except Exception:
        # if an exception occurred -- wrap it up and pass it back to the calling process
        wrapped_exception = NotebookScripterWrappedException()
        child_to_parent_queue.put((wrapped_exception, None))
    # worker subprocess done -- if join() is called in parent process when this process's thread of execution has gotten here it will not block


def rehydrate(string_like):
    obj = str_to_obj(string_like)
    global __notebookscripter_injected__
    __notebookscripter_injected__ = obj


def dehydrate_return_values(namespace):
    names = __notebookscripter_injected__[-1][1].get("return_values", [])
    return obj_to_string_literal(serialize_return_values(namespace, names))


def obj_to_string_literal(obj):
    return codecs.encode(pickle.dumps(obj), "hex").strip()


def str_to_obj(str_value):
    return pickle.loads(codecs.decode(str_value, "hex"))


def serialize_return_values(namespace, names, to_string=False):
    obj = {k: simple_serialize(namespace[k]) for k in names if k in namespace}
    if to_string:
        obj = obj_to_string_literal(obj)
    return obj


def simple_serialize(obj):
    try:
        pickle.dumps(obj)
        # if we didn't raise, then (theoretically) obj should be serializable ...
        return obj
    except Exception:
        return repr(obj)


def run_notebook_in_process(
    path_to_notebook: str,
    **hooks
) -> None:
    """Asynchronously Run a notebook in a new subprocess.

    Returns a closure which when called will block until the execution has completed.

    Arguments passed to the closure will retrieve values from the subprocess and package them in an (anonymous) python module with the requested values retrieved from the exrecuted subprocess

    Args:
        path_to_notebook: Path to .ipynb or .py file containing notebook code
    Returns:
        Returns a closure which will block until the notebook execution completes then return a newly created (anonymous) python module
        populated with requested values retrieved from the subprocess
    """

    import multiprocessing as mp
    import atexit

    context = mp.get_context("spawn")
    child_to_parent_queue = context.Queue()
    parent_to_child_queue = context.Queue()

    p = context.Process(target=worker, args=(parent_to_child_queue, child_to_parent_queue, path_to_notebook, __notebookscripter_injected__), kwargs=hooks)
    p.start()

    def _terminate_when_parent_process_ends():
        p.terminate()
        p.join()

    atexit.register(_terminate_when_parent_process_ends)

    def _block_and_receive_results(*return_values):
        """
        Block until the notebook execution has completed.  Then retrieve return_values from the subprocess's module scope and return
        the newly created (anonymous) python module populated with the requested values retrieved from the subprocess


        Args:
            return_values: Optional list of strings to pass back from subprocess -- values matching these names in the module created by invoking the notebook in a subprocess will be serialized passed across process boundaries back to this process, deserialized and made part of the returned module
        """

        atexit.unregister(_terminate_when_parent_process_ends)

        parent_to_child_queue.put(return_values)

        module_identity = "loaded_notebook_from_subprocess"
        dynamic_module = types.ModuleType(module_identity)
        dynamic_module.__file__ = path_to_notebook

        err, final_namespace = child_to_parent_queue.get()
        p.join()

        if err:
            raise err

        # inject retrieved return values into the returned module namespace
        dynamic_module.__dict__.update(final_namespace)

        return dynamic_module

    return _block_and_receive_results


def run_notebook_in_jupyter(path_to_notebook: str,
                            **hooks
                            ) -> None:
    """Run a notebook via a jupyter ipython kernel 

    Returns a closure which when called will block until the execution has completed.

    *args Arguments passed to the closure will retrieve values from the executed kernel and package them in an (anonymous) python module with the requested values retrieved from the exrecuted subprocess.  
    The closure also accepts a save_output_notebook parameter which is none by default -- if provided it should be a file path where the executed notebook with computed output cells will be written.

    Args:
        path_to_notebook: Path to .ipynb or .py file containing notebook code
    Returns:
        Returns a closure which will block until the notebook execution completes then return a newly created (anonymous) python module
        populated with requested values retrieved from the subprocess
    """
    from nbconvert.preprocessors.execute import executenb
    from nbformat import write as write_notebook
    from nbformat.notebooknode import from_dict as notebook_node_from_dict

    from jupyter_client import KernelManager
    from .NotebookPyFileReader import read_pyfile_as_notebook

    _, extension = os.path.splitext(path_to_notebook)
    if extension == ".ipynb":
        is_ipynb = True
    else:
        is_ipynb = False

    with open(path_to_notebook, 'r') as f:
        if is_ipynb:
            notebook = read_notebook(f, 4)
        else:
            notebook = read_pyfile_as_notebook(path_to_notebook)

    def _block_and_receive_results(*return_values, save_output_notebook=None):

        # add an extra cell to beginning of notebook to populate parameters
        notebook_parameters = __notebookscripter_injected__ + [[hooks, {"return_values": return_values}]]
        base64_parameters = obj_to_string_literal(notebook_parameters)

        initialization_source = """from NotebookScripter import (rehydrate as __rehydrate__, dehydrate_return_values as __dehydrate_return_values__)
__rehydrate__({})""".format(base64_parameters)

        initialization_cell = notebook_node_from_dict({
            "cell_type": "code",
            "execution_count": 0,
            "metadata": {},
            "outputs": [],
            "source": initialization_source
        })

        finalization_source = """__dehydrate_return_values__(locals())"""

        finalization_cell = notebook_node_from_dict({
            "cell_type": "code",
            "execution_count": 0,
            "metadata": {},
            "outputs": [],
            "source": finalization_source})

        notebook['cells'].insert(0, initialization_cell)
        notebook['cells'].append(finalization_cell)

        km = KernelManager()
        # hack -- needed because the code within ExecutePreprocessor.start_kernel to start
        # the kernel when km hasn't started a kernel already can't possibly work
        km.start_kernel()
        executed_notebook = executenb(notebook, timeout=None, km=km)
        km.shutdown_kernel()

        if save_output_notebook:
            if isinstance(save_output_notebook, str):
                with open(save_output_notebook, 'w') as f:
                    write_notebook(executed_notebook, f)
            else:
                write_notebook(executed_notebook, save_output_notebook)

        encoded_return_values = eval(executed_notebook["cells"][-1]["outputs"][0]["data"]["text/plain"])
        final_namespace = str_to_obj(encoded_return_values)

        module_identity = "loaded_notebook_from_subprocess"
        dynamic_module = types.ModuleType(module_identity)
        dynamic_module.__file__ = path_to_notebook

        # inject retrieved return values into the returned module namespace
        dynamic_module.__dict__.update(final_namespace)
        return dynamic_module
    return _block_and_receive_results
