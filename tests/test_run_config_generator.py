# Copyright (c) 2022, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from model_analyzer.config.generate.model_run_config_generator import ModelRunConfigGenerator
from model_analyzer.config.generate.run_config_generator import RunConfigGenerator
from model_analyzer.config.input.config_command_profile \
     import ConfigCommandProfile
from model_analyzer.cli.cli import CLI
from model_analyzer.config.run.run_config import RunConfig
from model_analyzer.model_analyzer_exceptions import TritonModelAnalyzerException
from model_analyzer.record.types.perf_throughput import PerfThroughput
from .common import test_result_collector as trc
from .common.test_utils import convert_to_bytes
from .common.test_utils import construct_run_config_measurement
from .mocks.mock_config import MockConfig
from .mocks.mock_model_config import MockModelConfig
from .mocks.mock_os import MockOSMethods
from unittest.mock import MagicMock, patch

from model_analyzer.config.generate.generator_utils import GeneratorUtils as utils

from model_analyzer.config.input.config_defaults import \
    DEFAULT_BATCH_SIZES, DEFAULT_TRITON_LAUNCH_MODE, \
    DEFAULT_CLIENT_PROTOCOL, DEFAULT_TRITON_INSTALL_PATH, DEFAULT_OUTPUT_MODEL_REPOSITORY, \
    DEFAULT_TRITON_INSTALL_PATH, DEFAULT_OUTPUT_MODEL_REPOSITORY, \
    DEFAULT_TRITON_HTTP_ENDPOINT, DEFAULT_TRITON_GRPC_ENDPOINT, DEFAULT_MEASUREMENT_MODE, \
    DEFAULT_RUN_CONFIG_MAX_CONCURRENCY, DEFAULT_RUN_CONFIG_MAX_INSTANCE_COUNT, DEFAULT_RUN_CONFIG_MAX_MODEL_BATCH_SIZE


class TestRunConfigGenerator(trc.TestResultCollector):

    def __init__(self, methodname):
        super().__init__(methodname)
        self._fake_throughput = 1

    def test_default_config_single_model(self):
        """
        Test Default Single Model:  
        
        num_PAC = log2(DEFAULT_RUN_CONFIG_MAX_CONCURRENCY) + 1
        num_MC = (  DEFAULT_RUN_CONFIG_MAX_INSTANCE_COUNT 
                  x log2(DEFAULT_RUN_CONFIG_MAX_MODEL_BATCH_SIZE)
                 ) + 1
        total = (num_PAC * num_MC) will be generated by the auto-search
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            profile_models:
                - my-model
            """)
        # yapf: enable

        expected_pa_configs = len(
            utils.generate_doubled_list(1, DEFAULT_RUN_CONFIG_MAX_CONCURRENCY))

        expected_model_configs = DEFAULT_RUN_CONFIG_MAX_INSTANCE_COUNT \
                               * len(utils.generate_doubled_list(1,DEFAULT_RUN_CONFIG_MAX_MODEL_BATCH_SIZE)) \
                               + 1
        expected_num_of_configs = expected_pa_configs * expected_model_configs

        self._run_and_test_run_config_generator(
            yaml_content, expected_config_count=expected_num_of_configs)

    def test_two_models(self):
        """
        Test Two Models that have the same automatic configuration:
        
        num_PAC = 2
        num_MC = 2 * 2 = 4
        model_total = (2 * 4) = 8 will be generated by the auto-search for each model

        default_step = (2 * 2) = 4 will be generated by combining the default configs (2 for each PAC)

        total = default_step + model_total * model_total = 68
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            run_config_search_max_model_batch_size: 2
            run_config_search_max_instance_count: 2
            run_config_search_max_concurrency: 2
            profile_models:
                - my-model
                - my-modelB

            """)
        # yapf: enable

        expected_num_of_configs = 68

        # Expect 78 calls to ModelRunConfigGenerator.set_last_results
        # All 68 experiments will be passed to the leaf generator
        # All 2 times that the leaf generator is done with default config will also pass results to root generator
        # All 8 times that the leaf generator is done with non-default config will also pass results to root generator

        expected_num_calls_to_set_last_results = 78

        with patch.object(ModelRunConfigGenerator,
                          "set_last_results") as mock_method:
            self._run_and_test_run_config_generator(
                yaml_content, expected_config_count=expected_num_of_configs)

            self.assertEqual(mock_method.call_count,
                             expected_num_calls_to_set_last_results)

    def test_two_uneven_models(self):
        """
        Test Two Uneven Models:
        
        Model A is auto search:
            num_PAC = 3
            num_MC = 2 * 2 = 4
            modelA_total = (3 * 4) = 12

        Model B is manual search:
            num_PAC = 2
            num_MC = 2 * 3 = 6
            modelB_total = 2 * 6 = 12

        default_step = num_PAC_A * num_PAC_B = 6
        total = default_step + modelA_total * modelB_total = 150
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            run_config_search_max_model_batch_size: 2
            run_config_search_max_instance_count: 2
            run_config_search_max_concurrency: 2
            profile_models:
                my-model:
                    parameters:
                        concurrency: [1,2,3]  
                my-modelB:
                    model_config_parameters:
                        max_batch_size: [1,4,16]
                        instance_group:
                        -
                            kind: KIND_GPU
                            count: [1,2]
            """)
        # yapf: enable

        expected_num_of_configs = 150

        self._run_and_test_run_config_generator(
            yaml_content, expected_config_count=expected_num_of_configs)

    def test_three_uneven_models(self):
        """
        Test Three Uneven Models:
        
        Model A is auto search:
            num_PAC = 2
            num_MC = 2 * 2 = 4
            modelA_total = 2 * 4 = 8

        Model B is auto search with fixed concurrency:
            num_PAC = 3
            num_MC = 2 * 2 = 4
            modelB_total = 3 *4 = 12

        Model C is manual search:
            num_PAC = 2
            num_MC = 3 * 2 = 6
            modelC_total = 2 * 6 = 12

        default_step = num_PAC_A * num_PAC_B * num_PAC_C = 2*3*2 = 12

        total = default_step + modelA_total * modelB_total * modelC_total = 1164
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            run_config_search_max_model_batch_size: 2
            run_config_search_max_instance_count: 2
            run_config_search_max_concurrency: 2
            profile_models:
                - my-model
                - 
                  my-modelB:
                    parameters:
                        concurrency: [1,5,9]  
                -
                  my-model3:
                    parameters:
                        concurrency: [10, 20]
                    model_config_parameters:
                        max_batch_size: [1,64]
                        instance_group:
                        -
                            kind: KIND_GPU
                            count: [1,2,3]
            """)
        # yapf: enable

        expected_num_of_configs = 1164
        # All 2 times that the leaf generator is done with default config will also pass results to root generator
        # All 8 times that the leaf generator is done with non-default config will also pass results to root generator

        # Expect 1268 calls to ModelRunConfigGenerator.set_last_results
        # All 1164 experiments will be passed to the leaf generator
        # All 96 times that the leaf generator is done with non-default config will pass results to the middle generator
        # All 6 times that the leaf generator is done with default config will pass results to the middle generator
        # All 8 times that the middle generator is done with non-default config will pass results to the root generator
        # All 2 times that the middle generator is done with default config will pass results to the root generator
        expected_num_calls_to_set_last_results = 1276

        with patch.object(ModelRunConfigGenerator,
                          "set_last_results") as mock_method:
            self._run_and_test_run_config_generator(
                yaml_content, expected_config_count=expected_num_of_configs)

            self.assertEqual(mock_method.call_count,
                             expected_num_calls_to_set_last_results)

    def test_early_backoff_leaf_model(self):
        """
        Test the case where there are two models, and the 'leaf' model (the last generator called
        in the recursive generator stack) has early backoff
        
        Both models are auto search:
            num_PAC = 2
            num_MC = 4 * 2 = 8
            model_total = 2 * 8 = 16

        default_step = num_PAC_A * num_PAC_B = 4
        total = default_step + modelA_total * modelA_total = 260

        However, the test will set up the throughput values such that ModelB will see a lack 
        of throughput the first time that it is walking max_batch_size. 
        Normally it would walk values 1,2,4,8, but for this ONE case it will only walk 1,2.
        This will reduce the total count by 4, as there are two concurrencies that would be 
        tried for ModelB for each of the two removed max_batch_sizes

        Thus, actual expected_count = 256


        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            run_config_search_max_model_batch_size: 8
            run_config_search_max_instance_count: 2
            run_config_search_max_concurrency: 2
            profile_models:
                - my-model
                - my-modelB
            """)
        # yapf: enable

        expected_num_of_configs = 256

        perf_throughput_values = [2**i for i in range(expected_num_of_configs)]
        perf_throughput_values[6] = perf_throughput_values[5]
        perf_throughput_values[7] = perf_throughput_values[5]

        with patch.object(TestRunConfigGenerator,
                          "_get_next_perf_throughput_value") as mock_method:
            mock_method.side_effect = perf_throughput_values
            self._run_and_test_run_config_generator(
                yaml_content, expected_config_count=expected_num_of_configs)

    def test_early_backoff_root_model(self):
        """
        Test the case where there are two models, and the 'root' model (the first one
        called in the recursive generator stack) has early backoff
        
        Both models are auto search:
            num_PAC = 2
            num_MC = 4 * 2 = 8
            model_total = 2 * 8 = 16

        default_step = num_PAC_A * num_PAC_B = 4
        total = default_step + modelA_total * modelA_total = 260

        However, the test will set up the throughput values such that ModelA will see a lack 
        of throughput the first time that it is walking max_batch_size. 
        Normally it would walk values 1,2,4,8, but for this case it will only walk 1,2.
        This will reduce the total count by 64: (2 max_batch_sizes * 2 concurrencies * 16 modelB cases)

        Thus, actual expected_count = 196


        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            run_config_search_max_model_batch_size: 8
            run_config_search_max_instance_count: 2
            run_config_search_max_concurrency: 2
            profile_models:
                - my-model
                - my-modelB
            """)
        # yapf: enable

        expected_num_of_configs = 196

        perf_throughput_values = [2**i for i in range(expected_num_of_configs)]
        # First 4 is modelA=default, modelB=default
        # Next 32 is modelA max_batch_size=1, modelB=all 16 cases
        # Next 32 is modelA max_batch_size=2, modelB=all 16 cases. We want to change these to show no increase
        for i in range(36, 68):
            perf_throughput_values[i] = perf_throughput_values[i - 36]

        with patch.object(TestRunConfigGenerator,
                          "_get_next_perf_throughput_value") as mock_method:
            mock_method.side_effect = perf_throughput_values
            self._run_and_test_run_config_generator(
                yaml_content, expected_config_count=expected_num_of_configs)

    def test_measurement_list(self):
        """
        Test that the root model (the first one called in the recursive generator stack) gets a list
        of all measurements since the last time it took a step, and makes a decision based on the 
        maximum throughput observed, not just the last measurement
        
        Both models are auto search:
            num_PAC = 2
            num_MC = 4 * 2 = 8
            model_total = 2 * 8 = 16

        default_total = num_PAC_A * num_PAC_B = 2*2 = 4
        total = default_total + modelA_total * modelB_total = 324

        The test will set up the throughput values such that there is an increase to the maximum throughput
        between each step of the root model, but that those results aren't strictly increasing every time.

        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            run_config_search_max_model_batch_size: 8
            run_config_search_max_instance_count: 2
            run_config_search_max_concurrency: 2
            profile_models:
                - my-model
                - my-modelB
            """)
        # yapf: enable

        expected_num_of_configs = 260

        # The first 4 results (0-3) are modelA=default, modelB=default
        # The next 32 results (4-35) are modelA= max_batch_size=1 concurrency 1 and 2, modelB all 16 combinations
        # The next 32 results (36-67) are modelA= max_batch_size=2 concurrency 1 and 2, modelB all 16 combinations
        #
        # Result 67 is the one to change to a smaller result for this test to work. If modelA was incorrectly
        # only looking at 67 instead of all results 36-67, then it would incorrectly cut off the max_batch_size
        # search and would not end up returning a full 260 configs
        perf_throughput_values = list(range(260))
        perf_throughput_values[67] = 1

        with patch.object(TestRunConfigGenerator,
                          "_get_next_perf_throughput_value") as mock_method:
            mock_method.side_effect = perf_throughput_values
            self._run_and_test_run_config_generator(
                yaml_content, expected_config_count=expected_num_of_configs)

    def test_matching_triton_server_env(self):
        """
        Test that we don't assert if triton server environments match:
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            run_config_search_max_model_batch_size: 2
            run_config_search_max_instance_count: 2
            run_config_search_max_concurrency: 2
            profile_models:
                - 
                  my-model:
                    triton_server_environment:
                        'LD_PRELOAD': fake_preload_1,
                        'LD_LIBRARY_PATH': fake_library_path_1
                -
                  my-modelB:
                    triton_server_environment:
                        'LD_PRELOAD': fake_preload_1,
                        'LD_LIBRARY_PATH': fake_library_path_1
            """)
        # yapf: enable

        expected_num_of_configs = 68
        self._run_and_test_run_config_generator(
            yaml_content, expected_config_count=expected_num_of_configs)

    def test_mismatching_triton_server_env(self):
        """
        Test that we assert if triton server environments don't match:
        """

        # yapf: disable
        yaml_content = convert_to_bytes("""
            run_config_search_max_model_batch_size: 2
            run_config_search_max_instance_count: 2
            run_config_search_max_concurrency: 2
            profile_models:
                - 
                  my-model:
                    triton_server_environment:
                        'LD_PRELOAD': fake_preload_1,
                        'LD_LIBRARY_PATH': fake_library_path_1
                -
                  my-modelB:
                    triton_server_environment:
                        'LD_PRELOAD': fake_preload_2,
                        'LD_LIBRARY_PATH': fake_library_path_2
            """)
        # yapf: enable

        with self.assertRaises(TritonModelAnalyzerException):
            expected_num_of_configs = 100
            self._run_and_test_run_config_generator(
                yaml_content, expected_config_count=expected_num_of_configs)

    def _run_and_test_run_config_generator(self, yaml_content,
                                           expected_config_count):
        args = [
            'model-analyzer', 'profile', '--model-repository', 'cli_repository',
            '-f', 'path-to-config-file'
        ]

        protobuf = """
            max_batch_size: 8
            instance_group [
            {
                kind: KIND_CPU
                count: 1
            }
            ]
            """

        self.mock_model_config = MockModelConfig(protobuf)
        self.mock_model_config.start()
        config = self._evaluate_config(args, yaml_content)

        rcg = RunConfigGenerator(config, config.profile_models, MagicMock())

        run_configs = []
        rcg_config_generator = rcg.next_config()
        while not rcg.is_done():
            run_configs.append(next(rcg_config_generator))
            rcg.set_last_results(self._get_next_fake_results())

        self.assertEqual(expected_config_count, len(set(run_configs)))

        # Checks that each ModelRunConfig contains the expected number of model_configs
        for run_config in run_configs:
            self.assertEqual(len(run_config.model_run_configs()),
                             len(config.profile_models))

        self.mock_model_config.stop()

    def _evaluate_config(self, args, yaml_content):
        mock_config = MockConfig(args, yaml_content)
        mock_config.start()
        config = ConfigCommandProfile()
        cli = CLI()
        cli.add_subcommand(
            cmd='profile',
            help=
            'Run model inference profiling based on specified CLI or config options.',
            config=config)
        cli.parse()
        mock_config.stop()
        return config

    def setUp(self):
        # Mock path validation
        self.mock_os = MockOSMethods(
            mock_paths=['model_analyzer.config.input.config_utils'])
        self.mock_os.start()

    def tearDown(self):
        self.mock_os.stop()

    def _get_next_fake_results(self):
        throughput_value = self._get_next_perf_throughput_value()

        measurement = construct_run_config_measurement(
            model_name=MagicMock(),
            model_config_names=["test_config_name"],
            model_specific_pa_params=MagicMock(),
            gpu_metric_values=MagicMock(),
            non_gpu_metric_values=[{
                "perf_throughput": throughput_value
            }],
            metric_objectives=MagicMock(),
            model_config_weights=MagicMock())

        return [measurement]

    def _get_next_perf_throughput_value(self):
        self._fake_throughput *= 2
        return self._fake_throughput


if __name__ == "__main__":
    unittest.main()
