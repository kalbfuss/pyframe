"""Module providing common definitions."""

APPLICATION_NAME = "Pyframe"
APPLICATION_DESCRIPTION = "Digital photo frame"
VERSION = "0.x"
PROJECT_NAME = "Pyframe project"


class ConfigError(Exception):
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


def check_valid_required(config, valid_keys, required_keys):
    """Check for valid and required configuration parameters.

    Checks whether only valid and all required parameters (keys) have been
    specified. Raises a configuration error exception otherwise.

    :param config: configuration to be checked
    :type config: dict
    :param valid_keys: valid configuration keys
    :type valid keys: set
    :param required_keys: required configuration keys
    :type required_keys: set
    :raises: ConfigError
    """
    # Make sure only valid parameters have been specified.
    keys = set(config.keys())
    if not keys.issubset(valid_keys):
        raise ConfigError(f"The configuration contains additional parameters. Only the parameters {valid_keys} are accepted, but the additional parameter(s) {keys.difference(valid_keys)} has/have been specified.", config)

    # Make sure all required parameters have been specified.
    if not required_keys.issubset(keys):
        raise ConfigError(f"As a minimum, the parameters {required_keys} are required, but the parameter(s) {required_keys.difference(keys)} has/have not been specified.")

def check_param(name, value, recurse=False, required=True, is_int=False, is_color=False, gr=None, ge=None, lo=None, le=None, options=None):
    """Check validity of configuration parameter.

    Checks the validity of a configuration parameter based on specified
    tests. Raises a configuration error exception if acceptance criteria are
    not met.

    The parameter value may either be provided directly or indirectly
    in the form of a dictionary. If a dictionary is provided as value, the
    parameter value is looked up via the parameter name.

    The function allows to recurse into lists and sets, for instance if the
    parameter value is a list of strings or numbers. In this case, specified
    tests are applied to each element of the set/list.

    :param name: parameter name
    :type name: str
    :param value: parameter value or dictionary
    :type value: type of parameter value or dict
    :param recurse: True if function shall recurse into sets and lists
    :type recurse: bool
    :param required: True if parameter must have value
    :type required: bool
    :param is_int: True if value must be integer
    :type is_int: bool
    :param is_color: True if value must be color definition
    :type is_color: bool
    :param gr: parameter value must be > gr
    :type gr: numeric
    :param ge: parameter value must be >= ge
    :type ge: numeric
    :param lo: parameter value must be < lo
    :type lo: numeric
    :param le: parameter value must be <= le
    :type le: numeric
    :param options: valid parameter values
    :type options: set or list
    :raises: ConfigError
    """
    config = value
    # Obtain parameter value from dictionary if dictionary specified.
    if isinstance(value, dict): value = config.get(name)

    # Check for non-type and empty lists/sets.
    if value is None or (isinstance(value, (list,set)) and len(value) ==0):
        # Return immediately if value is not required.
        if required is False: return
        # Rais exception otherwise.
        else: raise ConfigError(f"No value for parameter '{name}' specified.", config)

    # Compile generic error message prefix.
    prefix = f"Invalid value '{value}' for parameter '{name}' specified."

    # Ensure that value is valid color definition.
    if is_color:
        if not isinstance(value, list) or len(value) != 3:
            raise ConfigError(f"{prefix} Value must be valid color definition of type [r, g, b].", config)
        for rgb in value:
            if not isinstance(rgb, (int, float)) or rgb < 0 or rgb > 1:
                raise ConfigError(f"{prefix} Color values must be numeric within range [0,1].", config)
        # Prevent all further tests.
        return

    # Recurse into list items if requested.
    if isinstance(value, (list,set)):
        if recurse:
            for v in value:
                check_param(name, v, False, required, is_int, is_color, gr, ge, lo, le, options)
        # Prevent all further tests.
        return

    # Ensure that value is integer.
    if is_int and not isinstance(value, int):
        raise ConfigError(f"{prefix} Value must be integer.", config)
    # Ensure that value is greater than a certain value.
    if gr is not None and not value > gr:
        raise ConfigError(f"{prefix} Value must be > {gr}.", config)
    # Ensure that value is greater than or equal to a certain value.
    if ge is not None  and not value > ge:
        raise ConfigError(f"{prefix} Value must be >= {ge}.", config)
    # Ensure that value is lower than a certain value.
    if lo is not None  and not value < lo:
        raise ConfigError(f"{prefix} Value must be < {lo}.", config)
    # Ensure that value is lower than or equal to a certain value.
    if le is not None  and not value <= le:
        raise ConfigError(f"{prefix} Value must be <= {le}.", config)
    # Ensure that value is one of pre-defined options.
    if options is not None and value not in options:
        raise ConfigError(f"{prefix} Valid values are {options}.", config)
