"""Module providing common definitions."""

APPLICATION_NAME = "Pyframe"
APPLICATION_DESCRIPTION = "Digital photo frame"
VERSION = "0.x"
PROJECT_NAME = "Pyframe project"


class ConfigurationError(Exception):
    """Pyframe configuration error.

    Generic configuration error excption class, which can be used by any
    configurable pyframe component.
    """

    def __init__(self, msg, config=None):
        """Initialize configuration error instance.

        :param config: invalid configuration (default: None)
        :type config: dict
        """
        super().__init__(msg)
        self.config = config


def check_config(config, valid_keys, required_keys):
    """Check configuration parameters.

    Checks whether only valid and all required parameters (keys) have been
    specified. Raises a configuration error exception otherwise.

    :param config: configuration to be checked
    :type config: dict
    :param valid_keys: valid configuration keys
    :type valid keys: set
    :param required_keys: required configuration keys
    :type required_keys: set
    :raises: ConfigurationError
    """
    # Make sure only valid parameters have been specified.
    keys = set(config.keys())
    if not keys.issubset(valid_keys):
        raise ConfigurationError(f"The configuration contains additional parameters. Only the parameters {valid_keys} are accepted, but the additional parameter(s) {keys.difference(valid_keys)} has/have been specified.", config)

    # Make sure all required parameters have been specified.
    if not required_keys.issubset(keys):
        raise ConfigurationError(f"As a minimum, the parameters {required_keys} are required, but the parameter(s) {required_keys.difference(keys)} has/have not been specified.")
