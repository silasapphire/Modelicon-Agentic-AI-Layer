import yaml


def load_config():
    """
    Read config.yaml and return the settings.
    """

    with open("config/config.yml", "r") as file:
        config = yaml.safe_load(file)

    return config


config = load_config()

