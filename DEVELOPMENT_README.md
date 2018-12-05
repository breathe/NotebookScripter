# Developing NotebookScripter

## Run Test Suite Locally via conda

```shell
git clone https://github.com/breathe/NotebookScripter
cd NotebookScripter
# create conda env
conda create -n nbs-dev --file conda_dev.yml
# activate it
source activate nbs-dev
# run tests
nosetests
# or run linting, doctests, nosetests with coverage
python run_tests.py
```

## Run Test Suite Locally via Docker

```shell
git clone https://github.com/breathe/NotebookScripter
cd NotebookScripter
docker-compose build ; docker-compose up
```

## Run Test Suite Locally in pip

```shell
git clone https://github.com/breathe/NotebookScripter
cd NotebookScripter
# create pip-visible python environment using your preferred tool ...
pip install -r requirements_static_analysis.txt -r requirements_test_runner.txt -r requirements.txt
# run nose tests
nosetests
# or run linting, doctests, nosetests, coverage
python run_tests.py
```

## Run test suite by submitting a PR on git

Test suite should be run automatically on PR's.
