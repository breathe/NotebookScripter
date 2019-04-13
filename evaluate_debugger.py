from NotebookScripter import run_notebook_in_process

if __name__ == "__main__":
    run_notebook_in_process("./tests/SearchParents_1.pynotebook", a="grandparent_a")()
