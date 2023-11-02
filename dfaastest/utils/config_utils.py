import yaml


def get_config():
    with open('dfaastest/config.yaml', 'r') as file:
        config_yaml = yaml.safe_load(file)

    return config_yaml


def get_funk_names():
    # Read possible function names to use
    funk_names = []

    dfaastest_config = get_config()

    for funk_name in dfaastest_config['funk_generator']:
        funk_names.append(funk_name)

    return funk_names

def get_load_generator_config():
    dfaastest_config = get_config()
    return dfaastest_config['load_generator']
