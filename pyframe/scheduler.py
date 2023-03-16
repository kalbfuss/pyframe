"""Module providing slideshow scheduler."""

import schedule
import subprocess

from schedule import ScheduleValueError

from kivy.clock import Clock
from kivy.logger import Logger, LOG_LEVELS


class InvalidScheduleConfigurationError(Exception):
    """Invalid schedule configuration error."""

    def __init__(self, msg, config=None):
        """Initialize class instance."""
        super().__init__(msg)
        self.config = config


class Scheduler:
    """Slideshow scheduler.

    The slideswhow scheduler implements a simple, YAML/dict configurable
    scheduler for the display of slideshow during certain periods.
    The scheduler uses the python schedule package [1]. The run_pending method
    of the default scheduler is triggered by the Kivy Clock.
    Scheduling is event based. Events can be be used to turn the display on or
    off and select the slideshow to be displayed.

    [1] https://github.com/dbader/schedule
    """

    def __init__(self, config, app):
        """ Initialize scheduler instance.

        :param config: Scheduler configuration from the corresponding
            configuration file section.
        :type config: dict
        :param app: Pyframe application
        :type app: pyframe.App
        :raises: InvalidScheduleConfigurationError
        """
        self._app = app

        # Define valid and required keys per event configuration.
        valid_keys = {"display_mode", "slideshow", "time"}
        required_keys = {"display_mode", "time"}

        # Build schedule from configuration
        Logger.info("Scheduler: Building schedule from configuration.")
        for event, event_config in config.items():

            # Make sure all required parameters have been specified.
            keys = set(event_config.keys())
            if not required_keys.issubset(keys):
                raise InvalidScheduleConfigurationError(f"As a minimum, the schedule parameters {required_keys} are required, but only the parameter(s) {keys.intersection(required_keys)} has/have been specified in the configuration of event '{event}'.", event_config)

            # Make sure only valid parameters have been specified.
            if not keys.issubset(valid_keys):
                raise InvalidScheduleConfigurationError(f"Only the schedule parameters {valid_keys} are accepted, but the additional parameter(s) {keys.difference(valid_keys)} has/have been specified in the configuration of event '{event}'.", event_config)

            # Check value of parameter display mode.
            display_mode = event_config['display_mode']
            if display_mode is True: event_config['display_mode'] = "on"
            elif display_mode is False: event_config['display_mode'] = "off"
            elif display_mode == "on": pass
            elif display_mode == "off": pass
            elif display_mode == "motion": pass
            else:
                raise InvalidScheduleConfigurationError(f"Invalid display mode '{display_mode}' in the configuration of event '{event}'. Valid display modes are 'on', 'off', and 'motion'.", event_config)

            # Check value of parameter slideshow if specified.
            if 'slideshow' in event_config and event_config['slideshow'] not in self._app.slideshows:
                raise InvalidScheduleConfigurationError(f"Invalid slideshow  '{event_config['slideshow']}' in the configuration of event '{event}'. Valid slideshows are {self._app.slideshows}.", event_config)

            # Schedule events.
            try:
                schedule.every().day.at(event_config['time']).do(self._on_event, event_config)
                Logger.info(f"Scheduler: Event '{event}' scheduled at '{event_config['time']}'.")
            # Catch all schedule errors.
            except (TypeError, ScheduleValueError) as e:
                raise InvalidScheduleConfigurationError(f"The configuration {event_config} for event '{event}' is invalid: {e}", event_config)

        # Turn display off
        self._app.display_mode = "off"
        # Set clock interval and callback function.
        self.run_pending(0)

    def run_pending(self, dt):
        """Run pending schedule jobs."""
        schedule.run_pending()
        Clock.schedule_once(self.run_pending, schedule.idle_seconds())

    def _on_event(self, config):
        """Handle scheduled events."""
        # Set slideshow if specified.
        slideshow = config.get('slideshow')
        if slideshow is not None:
            self._app.slideshow = slideshow
        # Set display mode if specified.
        display_mode = config.get('display_mode')
        if display_mode is not None:
            self._app.display_mode = display_mode
            self._app.play()
