# Copyright (c) 2021, NVIDIA CORPORATION. All rights reserved.
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

import yaml


def _get_sweep_configs():

    sweep_configs = []
    model_config = {
        'run_config_search_max_concurrency': 2,
        'run_config_search_max_instance_count': 2,
        'run_config_search_max_preferred_batch_size': 2,
        'model_names': {
            'classification_chestxray_v1': {
                'model_config_parameters': {
                    'instance_group': [{
                        'count': [1, 2],
                        'kind': 'KIND_GPU'
                    }]
                }
            }
        },
    }

    model_config['total_param'] = 4
    model_config['total_param_remote'] = 2
    model_config['total_models'] = 2
    model_config['total_models_remote'] = 1
    sweep_configs.append(model_config)

    model_config = {
        'run_config_search_disable': True,
        'model_names': ['classification_chestxray_v1']
    }

    model_config['total_param'] = 1
    model_config['total_param_remote'] = 1
    model_config['total_models'] = 1
    model_config['total_models_remote'] = 1
    sweep_configs.append(model_config)

    model_config = {
        'run_config_search_max_concurrency': 2,
        'run_config_search_max_instance_count': 2,
        'run_config_search_max_preferred_batch_size': 2,
        'model_names': ['classification_chestxray_v1'],
    }

    model_config['total_param_remote'] = 2
    model_config['total_models_remote'] = 1
    model_config['total_param'] = 16
    model_config['total_models'] = 8

    sweep_configs.append(model_config)

    model_config = {
        'run_config_search_max_concurrency': 2,
        'run_config_search_max_instance_count': 2,
        'run_config_search_max_preferred_batch_size': 1,
        'model_names': {
            'classification_chestxray_v1': {
                'parameters': {
                    'concurrency': [1]
                },
            }
        },
    }

    model_config['total_param'] = 6
    model_config['total_param_remote'] = 1
    model_config['total_models'] = 6
    model_config['total_models_remote'] = 1
    sweep_configs.append(model_config)

    model_config = {
        'run_config_search_max_concurrency': 2,
        'run_config_search_max_instance_count': 2,
        'run_config_search_max_preferred_batch_size': 2,
        'model_names': {
            'classification_chestxray_v1': {
                'parameters': {
                    'concurrency': [1]
                },
                'model_config_parameters': {
                    'instance_group': [{
                        'count': [1, 2],
                        'kind': 'KIND_GPU'
                    }]
                }
            }
        },
    }

    model_config['total_param'] = 2
    model_config['total_param_remote'] = 1
    model_config['total_models'] = 2
    model_config['total_models_remote'] = 1
    sweep_configs.append(model_config)

    model_config = {
        'run_config_search_disable': True,
        'model_names': {
            'classification_chestxray_v1': {
                'parameters': {
                    'concurrency': [1]
                }
            }
        },
    }

    model_config['total_param'] = 1
    model_config['total_param_remote'] = 1
    model_config['total_models'] = 1
    model_config['total_models_remote'] = 1
    sweep_configs.append(model_config)

    model_config = {
        'run_config_search_disable': True,
        'concurrency': [1],
        'model_names': {
            'classification_chestxray_v1': {
                'model_config_parameters': {
                    'instance_group': [{
                        'count': [1, 2],
                        'kind': 'KIND_GPU'
                    }]
                }
            }
        },
    }

    model_config['total_param'] = 2
    model_config['total_param_remote'] = 1
    model_config['total_models'] = 2
    model_config['total_models_remote'] = 1
    sweep_configs.append(model_config)

    model_config = {
        'run_config_search_disable': True,
        'model_names': {
            'classification_chestxray_v1': {
                'model_config_parameters': {
                    'instance_group': [{
                        'count': [1, 2],
                        'kind': 'KIND_GPU'
                    }]
                }
            }
        },
    }

    model_config['total_param'] = 2
    model_config['total_param_remote'] = 1
    model_config['total_models'] = 2
    model_config['total_models_remote'] = 1
    sweep_configs.append(model_config)

    return sweep_configs


def get_all_configurations():

    run_params = []
    run_params += _get_sweep_configs()
    return run_params


if __name__ == "__main__":
    for i, configuration in enumerate(get_all_configurations()):
        total_param = configuration['total_param']
        total_param_remote = configuration['total_param_remote']
        total_models_remote = configuration['total_models_remote']
        total_models = configuration['total_models']
        del configuration['total_param']
        del configuration['total_param_remote']
        del configuration['total_models']
        del configuration['total_models_remote']
        with open(f'./config-{i}-param.txt', 'w') as file:
            file.write(str(total_param))
        with open(f'./config-{i}-param-remote.txt', 'w') as file:
            file.write(str(total_param_remote))
        with open(f'./config-{i}-models.txt', 'w') as file:
            file.write(str(total_models))
        with open(f'./config-{i}-models-remote.txt', 'w') as file:
            file.write(str(total_models_remote))
        with open(f'./config-{i}.yml', 'w') as file:
            yaml.dump(configuration, file)
