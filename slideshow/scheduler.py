"""Module providing slideshow scheduler."""

import schedule
import subprocess

from schedule import ScheduleValueError

from kivy.clock import Clock
from kivy.logger import Logger, LOG_LEVELS


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

    def __init__(self, config, slideshow):
        """ Initialize Scheduler instance.

        :param config: Scheduler configuration from the corresponding
            configuration file section.
        :type config: dict
        :param slideshow: ...
        :type slideshow: slideshow.Slideshow
        """
        self._slideshow = slideshow

        # Build schedule from configuration
        Logger.info("Scheduler: Building schedule from configuration.")

        for event, event_config in config.items():
            # Select job based on 'display' parameter
            if event_config['display'] or event_config['display'] == "on":
                job = self.display_on
            else:
                job = self.display_off
            # Attept to schedule job
            try:
                schedule.every().day.at(event_config['time']).do(job)
                Logger.info(f"Scheduler: Event '{event}' scheduled at '{event_config['time']}'.")
            except (TypeError, ScheduleValueError):
                Logger.error(f"Scheduler: Skipping event '{event}' as its configuration is invalid.")

        # Turn display off
        self.display_off()
        # Set clock interval and callback function
        self.run_pending(0)

    def run_pending(self, dt):
        """Runs pending schedule jobs.
        """
        schedule.run_pending()
        Clock.schedule_once(self.run_pending, schedule.idle_seconds())

    def display_on(self):
        """Turns display on and starts playing of slideshow.
        """
        Logger.info("Scheduler: Display on.")
        # Start playing slideshow
        self._slideshow.play()
        return

    def display_off(self):
        """Stops playing of slideshow and turns display off.
        """
        Logger.info("Scheduler: Display off.")
        # Stop playing slideshow_config
        self._slideshow.stop()
        # Turn display off. Works only on Linux with X server.
        subprocess.run("/usr/bin/xset dpms force off", shell=True)
        return
