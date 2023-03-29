"""Module providing Pyframe application."""

import copy
import logging
import repository.local
import repository.webdav
import subprocess
import sys
import time
import traceback
import yaml

import kivy.app

from repository import Index, Repository, InvalidConfigurationError, InvalidUuidError
from . import Indexer, Handler, Slideshow, Scheduler, MqttInterface, InvalidSlideshowConfigurationError, Controller, DISPLAY_MODE, DISPLAY_STATE, PLAY_STATE

from kivy.base import ExceptionManager
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.logger import Logger, LOG_LEVELS


class ExceptionHandler(kivy.base.ExceptionHandler):
    """Pyframe exception handler.

    Logs all exceptions, but continues with the execution. The main purpose of
    the handler is to prevent the application from exiting unexpectedly.
    """

    def __init__(self, app):
        """Initialize exception handler instance."""
        super().__init__()
        self._app = app

    def handle_exception(self, exception):
        """Log all exceptions and continue with execution.

        For unknown reasons, the exception is not always provided as an argument
        albeit the kivy documentation says so. The method thus retrieves the
        last raised exception via a system call.
        """
        # Make sure we do not produce any unhandled exceptions within the
        # exception handler.
        try:
            # Log information on exception.
            Logger.error("App: An exception was raised:")
            # Formatting the excpetion has failed for unknown reasons in the
            # past. Putting into separate try block to make sure subsequent
            # code is executed.
            try:
                # Retrieve information on last exception via system call since
                # exception object passed to handler sometimes seems to be
                # missing/incomplete.
                _, e, _ = sys.exc_info()
                Logger.error(f"App: {''.join(traceback.format_exception(e)).rstrip()}")
            except:
                pass
            Logger.error("App: Ignoring and continuing with execution.")
            # Wait for a moment to slow down infinite loops.
            time.sleep(10)
            # Restart slideshow if playing.
            if self._app.play_state == PLAY_STATE.PLAYING:
                self._app.stop()
                self._app.play()
            # Continue with execution.
        except: pass
        return ExceptionManager.PASS


class App(kivy.app.App, Controller):
    """Pyframe main application."""

    def __configure_logging(self):
        """Configure logging.

        Adjusts log levels based on the application configuration and adds a
        custom log handler for logging to rotating log files.
        """
        # Obtain log level and verify validity.
        level = self._config['log_level']
        if level not in ['debug', 'info', 'warn', 'error']:
            Logger.critical(f"Configuration: The specified log level '{level}' is invalid. Acceptable values are 'debug', 'info', 'warn', 'error' and 'critical'.")
            sys.exit(1)

        # Set log levels of default python and Kivy Logger.
        numeric_level = LOG_LEVELS[level]
        logging.basicConfig(level=numeric_level)
        Logger.setLevel(numeric_level)

        # Reduce logging by IPTCInfo and exifread to errors or specified log
        # level, whatever is higher.
        logging.getLogger("iptcinfo").setLevel(max(logging.ERROR, numeric_level))
        logging.getLogger("exifread").setLevel(max(logging.ERROR, numeric_level))
        # Reduce logging by SQLAlchemy to warnings or specified log lever,
        # whatever is higher.
        logging.getLogger("sqlalchemy").setLevel(max(logging.WARN, numeric_level))

        # Write all log messages to rotating log files using a special log
        # handler if file logging is activated. A separate log file is used for
        # the background indexing thread.
        if self._config['logging'] == "on" or self._config['logging'] == True:
            try:
                self._logHandler = Handler(self._config['log_dir'], "indexer")
                logging.getLogger().addHandler(self._logHandler)
            except Exception as e:
                Logger.critical(f"Configuration: {e}")
                sys.exit(1)

    def __create_repositories(self):
        """Create file repositories from configuration."""
        config = self._config
        index = self._index

        # Exit application if no repositories have been defined.
        if 'repositories' not in config or type(config['repositories']) is not dict:
            Logger.critical("Configuration: Exiting application as no repositories have been defined.")
            sys.exit(1)

        # Extract global repository configuration.
        global_config = {key: config[key] for key in ('index_update_interval', 'index_update_at', 'cache') if key in config}

        # Create repositories based on the configuration.
        for uuid, rep_config in config['repositories'].items():
            # Skip disabled repositories.
            if rep_config.get('enabled') is False:
                Logger.info(f"Configuration: Skipping repository '{uuid}' as it has been disabled.")
                continue
            # Combine global and local configuration. Local configuration
            # settings supersede global settings.
            combined_config = copy.deepcopy(global_config)
            combined_config.update(rep_config)
            rep_type = combined_config.get('type')
            try:
                # Create local repository.
                if rep_type == "local":
                    Logger.info(f"Configuration: Creating local repository '{uuid}'.")
                    rep = repository.local.Repository(uuid, combined_config, index=index)
                # Create webdav repository.
                elif rep_type == "webdav":
                    Logger.info(f"Configuration: Creating WebDAV repository '{uuid}'.")
                    rep = repository.webdav.Repository(uuid, combined_config, index=index)
                # Catch any invalid repository types.
                else:
                    Logger.critical(f"Configuration: The type '{rep_type}' of repository '{uuid}' is invalid. Acceptable values are 'local' or 'webdav'.")
                    sys.exit(1)

                # Queue the repository for indexing.
                interval = combined_config.get('index_update_interval', 0)
                at = combined_config.get('index_update_at', None)
                self._indexer.queue(rep, interval, at)

            # Catch any invalid configuration errors.
            except InvalidConfigurationError as e:
                Logger.critical(f"Configuration: {e}")
                sys.exit(1)
            # Catch any invalid UUID errors.
            except InvalidUuidError:
                Logger.error(f"Configuration: The repository UUID '{uuid}' is invalid.")
                sys.exit(1)

        # Exit application if no valid repositories have been defined.
        if len(Repository._repositories.items()) == 0:
            Logger.critical("Configuration: Exiting application as no valid repositories have been defined.")
            sys.exit(1)

    def __create_slideshows(self):
        """Create slideshows from configuration.

        Slideshow configurations are extracted from the 'slideshows' section
        in the configuration file. One slideshow is created per has entry.
        Slideshow instances are collected in the hash _slideshows, with the key
        being identical to the slideshow name in the configuration file.
        """
        config = self._config
        index = self._index
        # Exit application if no slideshow has been defined.
        if 'slideshows' not in config or type(config['slideshows']) is not dict:
            Logger.critical("Configuration: Exiting application as no slideshows have been defined.")
            sys.exit(1)

        # Create empty dictionary to collect slideshows
        self._slideshows = dict()
        # Extract global slideshow configuration
        global_config = {key: config[key] for key in ('always_excluded_tags', 'bg_color', 'excluded_tags', 'file_types', 'label_content', 'label_duration', 'label_font_size', 'label_mode',  'label_padding', 'most_recent', 'order', 'orientation', 'pause', 'resize', 'rotation', 'sequence', 'tags') if key in config}

        # Create slideshows from configuration.
        for name, config in config['slideshows'].items():
            # Combine global and local configuration. Local configuration
            # settings supersede global settings.
            combined_config = copy.deepcopy(global_config)
            combined_config.update(config)
            # Create new slideshow, bind 'on_content_change' event and add to
            # slideshow do dictionary.
            try:
                slideshow = Slideshow(name, index, combined_config)
                slideshow.bind(on_content_change=self.on_content_change)
                self._slideshows[name] = slideshow
            except InvalidSlideshowConfigurationError as e:
                Logger.critical(f"Configuration: {e}")
                sys.exit(1)

        # Exit application if no valid repositories have been defined.
        if len(self._slideshows.items()) == 0:
            Logger.critical("Configuration: Exiting application as no valid slideshows have been defined.")
            sys.exit(1)

    def __init_display(self):
        """Initialize display and window."""

        # Check value of parameter display mode.
        display_mode = self._config['display_mode']
        values = [ item.value for item in DISPLAY_MODE ]
        if display_mode not in values:
            Logger.critical(f"Configuration: Invalid display mode '{display_mode}' specified. Valid display modes are '{values}'.")
            sys.exit(1)

        display_state = self._config['display_state']
        # Convert from booleans to "on" and "off"
        if display_state is True: display_state = "on"
        elif display_state is False: display_state = "off"
        # Check value of parameter display state.
        values = [ item.value for item in DISPLAY_STATE ]
        if display_state not in values:
            Logger.critical(f"Configuration: Invalid display state '{display_state}' specified. Valid display states are '{values}'.")
            sys.exit(1)

        # Check value of parameter display timeout
        display_timeout = self._config['display_timeout']
        if type(display_timeout) is not int or display_timeout < 0:
            Logger.critical(f"Configuration: Invalid value '{display_timeout}' for parameter display timeout specified. Timeout needs to be a positive integer.")
            sys.exit(1)

        # Initialize display state and mode.
        self._display_timeout = display_timeout
        self._timeout_event = None
        self._display_mode = ""
        self._display_state = ""
        self.display_state = display_state
        self.display_mode = display_mode

        # Set window size.
        value = self._config['window_size']
        if type(value) is list and len(value) == 2 and value[0] > 0 and value[1] > 0:
            Window.size = (value)
        elif value == "full":
            Window.fullscreen = 'auto'
        else:
            Logger.critical(f"Configuration: Invalid value '{value}' for parameter 'window_size' specified. Acceptable values are '[width, height]' and 'full'.")
            sys.exit(1)
        # Disable display of mouse cursor
        Window.show_cursor = False

    def __load_config(self):
        """Load application configuration.

        Loads the application configuration from the default configuration file
        and applies default values where missing.
        """
        # Load configuration from yaml file.
        with open('./config.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)
        self._config.update(config)
        Logger.debug(f"Configuration: Configuration = {self._config}")
        return self._config

    # Default configuration.
    _config = {
        'bg_color': [0.9,0.9,0.8],
        'cache': "./cache",
        'display_mode': "static",
        'display_state': "on",
        'display_timeout': 300,
        'enable_exception_handler': "on",
        'enable_scheduler': "on",
        'enable_mqtt': "on",
        'file_types': [ "images", "videos" ],
        'index': "./index.sqlite",
        'index_update_interval': 0,
        'label_mode': "off",
        'label_content': "full",
        'label_duration': 24,
        'label_font_size': 0.08,
        'label_padding': 0.03,
        'logging': "on",
        'log_level': "warn",
        'log_dir': "./log",
        'order': "ascending",
        'pause': 60,
        'resize': "fill",
        'rotation': 0,
        'sequence': "name",
        'window_size': [ 800, 450 ]
    }

    def build(self):
        """Build Kivy application.

        Loads the application configuration from the default configuration file.
        Creates configured repositories and builds an index across the latter.
        """
        self._scheduler = None
        self._mqtt_interface = None
        self._play_state = PLAY_STATE.STOPPED

        # Bind to window 'on_request_close' event for safe shutdown of the
        # application.
        Window.bind(on_request_close=self.on_request_close)
        # Register 'state_change' event, which is fired upon content and
        # controller state changes.
        self.register_event_type('on_state_change')

        # Load configuration.
        self.__load_config()
        # Configure logging.
        self.__configure_logging()

        # Create/load index.
        self._index = Index(self._config['index'])
        # Create background indexer.
        self._indexer = Indexer(self._index)
        # Create repositories.
        self.__create_repositories()
        # Start building index in the background.
        self._indexer.start()
        # Create slideshows.
        self.__create_slideshows()

        # Make first slideshow the main root widget
        self.root = next(iter(self._slideshows.values()))

        # Create mqtt interface if configured and activated.
        if 'mqtt' in self._config and self._config['enable_mqtt'] == "on" or self._config['enable_mqtt'] is True:
            try:
                self._mqtt_interface = MqttInterface(self._config['mqtt'], self)
            except Exception as e:
                Logger.critical(f"Configuration: {e}")
                sys.exit(1)

        # Bind keyboard listener
        Window.bind(on_keyboard=self.on_keyboard)

        # Initialize display
        self.__init_display()

        # Create scheduler if configured and activated.
        if 'schedule' in self._config and (self._config['enable_scheduler'] == "on" or self._config['enable_scheduler'] is True):
            try:
                self._scheduler = Scheduler(self._config['schedule'], self)
            except Exception as e:
                Logger.critical(f"Configuration: {e}")
                sys.exit(1)
        # Start playing first defined slideshow otherwise.
        else:
            self.play()

        # Install default exception handler to prevent the application from
        # exiting unexpectedly. All exceptions are caught and logged, but the
        # appplication continues with the execution afterwards.
        value = self._config.get('enable_exception_handler')
        if value == "on" or value is True:
            ExceptionManager.add_handler(ExceptionHandler(self))

        return self.root

    def on_content_change(self, slideshow, *largs):
        """Handle slideshow content change events."""
        Logger.debug(f"App: Event 'on_content_change' from slideshow '{slideshow.name}' received. Forwarding as event 'on_stage_change'.")
        # Forward as 'on_state_change' event.
        self.dispatch('on_state_change')
        # Consume event.
        return True

    def on_keyboard(self, window, key, *args):
        """Handle keyboard events.

        The following events are currently supported:
        - Right arrow: Show net file.
        - Left arrow: Show previous file (not yet implemented).
        - Escape: Exit application.
        """
        Logger.info(f"App: Key '{key}' pressed.")
        # Exit application if escape key pressed.
        if key == 27:
            # Let the default handler do the necessary work.
            return False
        # Touch controller to prevent screen timeout.
        self.touch()
        # Display next file if right arrow pressed.
        if key == 275:
            self.next()
        # Display previous file if left arrow pressed.
        elif key == 276:
            self.previous()
        # Consume event.
        return True

    def on_state_change(self, *largs):
        """Default handler for 'on_state_change' events."""
        pass

    def close(self):
        """Prepare application for safe exit.

        Shuts down the MQTT remote controller, scheduler and stops the current
        the current slideswhow."""
        # Stop current slideshow.
        self.stop()
        # Stop MQTT interface if running.
        if self._mqtt_interface is not None:
            Logger.info("App: Stopping MQTT interface.")
            self._mqtt_interface.stop()
        # Stop scheduler if running.
        if self._scheduler is not None:
            Logger.info("App: Stopping scheduler.")
            self._scheduler.stop()
        # Close metadata index if open.
        if self._index is not None:
            Logger.info("App: Closing metadata index.")
            self._index.close()

    def on_request_close(self, *largs, **kwargs):
        """Prepare for application closure after 'on_request_close' event.

        By default, the event 'on_request_close' is dispatched after the esacape
        key has been pressed. The event is not consumed (false return value)
        such that the application is closed by kivy afterwards.
        """
        Logger.info("App: Application closure requested. Preparing for safe exit.")
        self.close()
        return False

    def on_display_timeout(self, dt):
        """Handle display timeouts in motion mode."""
        # Pause playing slideshow and turn display off.
        Logger.info(f"Controller: Display has timed out.")
        self.pause()
        self.display_off()

    @property
    def current_file(self):
        """Return the current repository file.

        :return: current file
        :rtype: repository.File
        """
        return self.root.current_file

    @property
    def display_mode(self):
        """Return display mode.

        See enumeration DISPLAY_MODE for possible values.

        :return: display mode
        :rtype: str
        """
        return self._display_mode

    @display_mode.setter
    def display_mode(self, mode):
        """Set display mode.

        See enumeration DISPLAY_MODE for possible values.

        :param mode: display mode
        :type mode: str
        """
        # Return if already in the right mode.
        if mode == self._display_mode: return
        Logger.info(f"Controller: Changing display mode from '{self._display_mode}' to '{mode}'.")
        # Turn display on and start playing slideshow.
        # Cancel previously scheduled timeout event.
        if self._timeout_event is not None:
            self._timeout_event.cancel()
        #  Set display to motion mode and start playing slideshow.
        if mode == DISPLAY_MODE.STATIC: pass
        elif mode == DISPLAY_MODE.MOTION:
            # Update last touch time stamp and schedule timeout event.
            self._last_touch = time.time()
            self._timeout_event = Clock.schedule_once(self.on_display_timeout, self._display_timeout)
        # Raise exception upon invalid display mode.
        else:
            raise Exception(f"The selected display mode '{mode}' is invalid. Acceptable values are '{[ item.value for item in DISPLAY_MODE ]}'.")
        # Update display mode.
        self._display_mode = mode
        self.dispatch('on_state_change')

    def display_on(self):
        """Turn the display on."""
        # Return if already on.
        if self._display_state == DISPLAY_STATE.ON: return
        Logger.info("Controller: Turning display on.")
        # Turn display off on Linux with X server.
        subprocess.run("/usr/bin/xset dpms force on", shell=True,  stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
        # Update display state.
        self._display_state = DISPLAY_STATE.ON
        self.dispatch('on_state_change')

    def display_off(self):
        """Turn the display off."""
        # Return if already off.
        if self._display_state == DISPLAY_STATE.OFF: return
        Logger.info("Controller: Turning display off.")
        # Turn display on Linux with X server.
        subprocess.run("/usr/bin/xset dpms force off", shell=True, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
        # Update display state.
        self._display_state = DISPLAY_STATE.OFF
        self.dispatch('on_state_change')

    @property
    def display_state(self):
        """Return display state.

        See enumeration DISPLAY_STATE for possible values.

        :return: display state
        :rtype: str
        """
        return self._display_state

    @display_state.setter
    def display_state(self, state):
        """Set display state.

        See enumeration DISPLAY_STATE for possible values.

        :param state: display state
        :type mode: str
        """
        if self._display_state == state: return
        if state == DISPLAY_STATE.ON: self.display_on()
        elif state == DISPLAY_STATE.OFF: self.display_off()
        else:
            raise Exception(f"The selected display state '{state}' is invalid. Acceptable values are '{[ item.value for item in DISPLAY_STATE ]}'.")

    @property
    def display_timeout(self):
        """Return display timeout.

        :return: display timeout in seconds
        :rtype: int
        """
        return _display_timeout

    @display_timeout.setter
    def display_timeout(self, timeout):
        """Set display timeout.

        :param timeout: display timeout in seconds
        :type timeout: int
        """
        Logger.info(f"Controller: Setting display timeout to {timeout}s.")
        self._display_timeout = timeout

    def pause(self):
        """Pause playing the current slideshow."""
        if self._play_state == PLAY_STATE.PAUSED: return
        Logger.info(f"Controller: Pausing slideshow '{self.slideshow}'.")
        self.root.pause()
        self._play_state = PLAY_STATE.PAUSED
        self.dispatch('on_state_change')

    def play(self):
        """Start/resume playing the current slideshow."""
        if self._play_state == PLAY_STATE.PLAYING: return
        Logger.info(f"Controller: Playing/resuming slideshow '{self.slideshow}'.")
        self.root.play()
        self._play_state = PLAY_STATE.PLAYING
        self.display_on()
        self.dispatch('on_state_change')

    @property
    def play_state(self):
        """Return play state.

        See enumeration PLAY_STATE for possible values.

        :return: play state
        :rtype: str
        """
        return self._play_state

    @play_state.setter
    def play_state(self, state):
        """Set play state.

        See enumeration PLAY_STATE for possible values.

        :param mode: play state
        :type mode: str
        """
        if self._play_state == state: return
        if state == PLAY_STATE.PLAYING: self.play()
        elif state == PLAY_STATE.PAUSED: self.pause()
        elif state == PLAY_STATE.STOPPED: self.stop()
        else:
            raise Exception(f"The selected play state '{state}' is invalid. Acceptable values are '{[ item.value for item in PLAY_STATE ]}'.")

    def stop(self):
        """Stop playing the current slideshow."""
        if self._play_state == PLAY_STATE.STOPPED: return
        Logger.info(f"Controller: Stopping slideshow '{self.slideshow}'.")
        self.root.stop()
        self._play_state = PLAY_STATE.STOPPED
        self.display_off()
        self.dispatch('on_state_change')

    def previous(self):
        """Change to previous file in slideshow."""
        # Skip if not playing.
        if self._play_state == PLAY_STATE.STOPPED: return
        Logger.info(f"Controller: Changing to previous file in slideshow '{self.slideshow}'.")
        self.root.previous()

    def next(self):
        """Change to next file in slideshow."""
        # Skip if not playing.
        if self._play_state == PLAY_STATE.STOPPED: return
        Logger.info(f"Controller: Changing to next file in slideshow '{self.slideshow}'.")
        self.root.next()

    @property
    def slideshow(self):
        """Return name of the current slideshow.

        :return: slideshow name
        :rtype: str
        """
        return self.root.name

    @slideshow.setter
    def slideshow(self, name):
        """Set current slideshow by its name.

        :param name: slideshow name
        :type name: str
        """
        # Retrieve slideshow by its name. Stick to the current slideshow if
        # specified slideshow does not exist.
        new_root = self._slideshows.get(name, self.root)
        if new_root is not self.root:
            # Save play state and stop playing the current slideshow.
            cur_play_state = self.play_state
            self.stop()
            # Replace the root widget.
            Logger.info(f"Controller: Setting slideshow to '{name}'.")
            Window.add_widget(new_root)
            Window.remove_widget(self.root)
            self.root = new_root
            self.play_state = cur_play_state
            self.dispatch('on_state_change')

    @property
    def slideshows(self):
        """Return names of all slideshows.

        :return: list of slideshow names
        :rtype: list of str
        """
        return list(self._slideshows.keys())

    def touch(self):
        """Update last touch time stamp and prevent screen timeout in display motion mode."""
        # Update last touch time stamp.
        self._last_touch = time.time()
        # Return if display not in motion mode or slideshow stopped.
        if self.display_mode != DISPLAY_MODE.MOTION or self.play_state == PLAY_STATE.STOPPED: return
        # Cancel previously scheduled timeout event.
        if self._timeout_event is not None:
            self._timeout_event.cancel()
        # Restart playing the slideshow.
        self.play()
        # Schedule new timeout event.
        self._timeout_event = Clock.schedule_once(self.on_display_timeout, self._display_timeout)
        # Log next display timeout.
        next_timeout_asc = time.asctime(time.localtime(self._last_touch + self._display_timeout))
        Logger.debug(f"Controller: Controller has been touched. Next display timeout scheduled in {self._display_timeout} s at {next_timeout_asc}.")
