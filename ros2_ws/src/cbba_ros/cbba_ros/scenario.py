import os

import yaml
from ament_index_python.packages import get_package_share_directory


def default_scenario_path():
    return os.path.join(get_package_share_directory('cbba_ros'), 'config', 'scenario.yaml')


def load_scenario(path=None):
    with open(path or default_scenario_path()) as f:
        return yaml.safe_load(f)
