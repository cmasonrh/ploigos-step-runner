import os
import re
from io import IOBase

from unittest.mock import Mock, patch
from tests.helpers.base_step_implementer_test_case import \
    BaseStepImplementerTestCase
from tests.helpers.test_utils import Any, create_sh_side_effect
from ploigos_step_runner.step_implementers.deploy.helm import Helm


@patch("ploigos_step_runner.step_implementers.deploy.Helm.__init__")
class TestStepImplementerMavenTest___init__(BaseStepImplementerTestCase):
    def test_defaults(self, mock_super_init):
        workflow_result = WorkflowResult()
        parent_work_dir_path = '/fake/path'
        config = {}

        Helm(
            workflow_result=workflow_result,
            parent_work_dir_path=parent_work_dir_path,
            config=config,
            environment=None,
            helm_chart=None,
            helm_release=None
        )

        mock_super_init.assert_called_once_with(
            workflow_result,
            parent_work_dir_path,
            config,
            environment=None
        )

class TestStepImplementerDeployHelmBase(BaseStepImplementerTestCase):
    def create_step_implementer(
            self,
            step_config={},
            parent_work_dir_path='',
            environment=None
    ):
        return self.create_given_step_implementer(
            step_implementer=Helm,
            step_config=step_config,
            step_name='deploy',
            implementer='Helm',
            parent_work_dir_path=parent_work_dir_path,
            environment=environment
        )

class TestStepImplementerMavenTest_step_implementer_config_defaults(
    BaseStepImplementerTestCase
):
    def test_result(self):
        self.assertEqual(
            Helm.step_implementer_config_defaults(),
            {
                'helm-flags': []
            }
        )

class TestStepImplementerMavenTest__required_config_or_result_keys(
    BaseStepImplementerTestCase
):
    def test_result(self):
        self.assertEqual(
            Helm._required_config_or_result_keys(),
            [
                'helm-chart',
                'helm-release'
            ]
        )