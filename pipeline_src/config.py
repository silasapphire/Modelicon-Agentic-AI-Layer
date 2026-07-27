from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "pipeline_config" / "config.yml"


def load_config():
    """
    Read config.yaml and return the settings.
    """

    with open(CONFIG_PATH, "r") as file:
        config = yaml.safe_load(file)

    return config


config = load_config()

