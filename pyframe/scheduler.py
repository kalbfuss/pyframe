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
        valid_keys = {"display", "slideshow", "time"}
        required_keys = {"display", "time"}

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

            try:
                # Schedule job to switch display on and start playing slideshow.
                if event_config['display'] == True or event_config['display'] == "on":
                    schedule.every().day.at(event_config['time']).do(self.display_on, event_config['slideshow'])
                # Schedule job to switch display off.
                elif event_config['display'] == False or event_config['display'] == "off":
                    schedule.every().day.at(event_config['time']).do(self.display_off)
                # Raise exception due to invalid value for 'display'.
                else:
                    raise InvalidScheduleConfigurationError(f"The value '{event_config['display']}' for parameter 'display' in the configuration of event '{event}' is invalid.", event_config)

                Logger.info(f"Scheduler: Event '{event}' scheduled at '{event_config['time']}'.")

            # Catch all schedule errors.
            except (TypeError, ScheduleValueError):
                raise InvalidScheduleConfigurationError(f"The configuration {event_config} for event '{event}' is invalid.", event_config)

        # Turn display off
        self.display_off()
        # Set clock interval and callback function
        self.run_pending(0)

    def run_pending(self, dt):
        """Runs pending schedule jobs.
        """
        schedule.run_pending()
        Clock.schedule_once(self.run_pending, schedule.idle_seconds())

    def display_on(self, slideshow=None):
        """Turns display on and starts playing of slideshow.
        """
        Logger.info("Scheduler: Display on.")
        # Turn display on. Works only on Linux with X server.
        subprocess.run("/usr/bin/xset dpms force on", shell=True)
        # Start playing slideshow
        self._app.play_slideshow(slideshow)
        return

    def display_off(self):
        """Stops playing of slideshow and turns display off.
        """
        Logger.info("Scheduler: Turn display off.")
        # Stop playing slideshow_config
        self._app.stop_slideshow()
        # Turn display off. Works only on Linux with X server.
        subprocess.run("/usr/bin/xset dpms force off", shell=True)
        return
