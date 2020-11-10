# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
import os
import re
from io import IOBase

import yaml
from tssc import TSSCFactory


def create_sh_side_effect(
        mock_stdout=None,
        mock_stderr=None,
        exception=None
):
    def sh_side_effect(*args, **kwargs):
        if mock_stdout:
            if callable(kwargs['_out']):
                kwargs['_out'](mock_stdout)
            elif isinstance(kwargs['_out'], IOBase):
                kwargs['_out'].write(mock_stdout)

        if mock_stderr:
            if callable(kwargs['_err']):
                kwargs['_err'](mock_stderr)
            elif isinstance(kwargs['_err'], IOBase):
                kwargs['_err'].write(mock_stderr)

        if exception:
            raise exception

    return sh_side_effect


def run_step_test_with_result_validation(
        temp_dir,
        step_name,
        config,
        expected_step_results,
        runtime_args=None,
        environment=None):
    results_dir_path = os.path.join(temp_dir.path, 'tssc-results')
    working_dir_path = os.path.join(temp_dir.path, 'tssc-working')

    factory = TSSCFactory(config, results_dir_path, work_dir_path=working_dir_path)
    if runtime_args:
        factory.config.set_step_config_overrides(step_name, runtime_args)

    factory.run_step(step_name, environment)

    results_file_name = "tssc-results.yml"
    with open(os.path.join(results_dir_path, results_file_name), 'r') as step_results_file:
        actual_step_results = yaml.safe_load(step_results_file.read())
        assert actual_step_results == expected_step_results


def create_git_commit_with_sample_file(temp_dir, git_repo,
                                       sample_file_name='sample-file',
                                       commit_message='test'):
    sample_file = os.path.join(temp_dir.path, sample_file_name)
    open(sample_file, 'wb').close()
    git_repo.index.add([sample_file])
    git_repo.index.commit(commit_message)


def Any(cls):
    """
    Source
    ------
    https://stackoverflow.com/questions/21611559/assert-that-a-method-was-called-with-one-argument-out-of-several
    """

    class Any(cls):
        def __eq__(self, other):
            return True

        def __hash__(self):
            return hash(tuple(self))

    return Any()


class StringRegexParam():
    def __init__(self, regex):
        self.__regex = regex

    def __eq__(self, other):
        if isinstance(other, str):
            return re.match(self.__regex, other)
        return False


def create_sops_side_effect(mock_stdout):
    def sops_side_effect(*args, **kwargs):
        kwargs['_out'].write(mock_stdout)

    return sops_side_effect
