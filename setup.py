from setuptools import setup

setup(
    name='NotebookScripter',
    version='4.0.1',
    packages=('NotebookScripter',),
    url='https://github.com/breathe/NotebookScripter',
    license='MIT',
    author='N. Ben Cohen',
    author_email='breathevalue@icloud.com',
    install_requires=(
        "ipython",
        "nbformat"
    ),
    tests_require=(
        "nose",
        "coverage",
        "snapshottest",
        "matplotlib"
    ),
    description='Expose ipython jupyter notebooks as callable functions.  More info here https://github.com/breathe/NotebookScripter',
    long_description='Expose ipython jupyter notebooks as callable functions.  More info here https://github.com/breathe/NotebookScripter',
    classifiers=(
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython')
)
