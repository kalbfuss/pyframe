"""Module providing Pyframe application."""

import copy
import logging
import repository.local
import repository.webdav
import sys
import threading
import time
import yaml

import kivy.app

from repository import Index
from repository import Repository, InvalidConfigurationError, InvalidUuidError
from . import Indexer, Handler, Slideshow, Scheduler, InvalidSlideshowConfigurationError

from kivy.logger import Logger, LOG_LEVELS
from kivy.core.window import Window


class App(kivy.app.App):
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
        # Redirect all log messages from the background thread into a rotated
        # log file using a special log handler.
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
        global_config = {key: config[key] for key in ('rotation', 'bg_color', 'file_type', 'most_recent', 'order', 'orientation', 'pause', 'resize', 'sequence', 'tags') if key in config}

        # Create slideshows from configuration.
        for slideshow, slideshow_config in config['slideshows'].items():
            # Combine global and local configuration. Local configuration
            # settings supersede global settings.
            combined_config = copy.deepcopy(global_config)
            combined_config.update(slideshow_config)
            # Create new slideshow and add to hash
            try:
                self._slideshows[slideshow] = Slideshow(index, combined_config)
            except InvalidSlideshowConfigurationError as e:
                Logger.critical(f"Configuration: {e}")
                sys.exit(1)

        # Exit application if no valid repositories have been defined.
        if len(self._slideshows.items()) == 0:
            Logger.critical("Configuration: Exiting application as no valid slideshows have been defined.")
            sys.exit(1)

    # Define default configuration parameter values
    _config = {
        'bg_color': [0.9,0.9,0.8],
        'cache': "./cache",
        'file_type': [ "images", "videos" ],
        'index': "./index.sqlite",
        'index_update_interval': 0,
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

    def build(self):
        """Build Kivy application.

        Loads the application configuration from the default configuration file.
        Creates configured repositories and builds an index across the latter.
        """
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

        # Change to full screen mode.
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

        # Make first slideshow the main root widget
        root = next(iter(self._slideshows.values()))

        # Wait until index contains at least one entry.
        while root.length() == 0:
            time.sleep(1)
            Logger.warn("App: Slideshow still empty. Giving more time to build index.")
        Logger.info(f"App: Proceeding with {root.length()} files in slideshow.")

        # Create scheduler if configured.
        if 'schedule' in self._config:
            try:
                self._scheduler = Scheduler(self._config['schedule'], self)
            except Exception as e:
                Logger.critical(f"Configuration: {e}")
                sys.exit(1)

        # Start playing first defined slideshow otherwise.
        else:
            root.play()
        return root

    def play_slideshow(self, slideshow=None):
        """Starts playing the specified slideshow.

        :param slideshow: Name of the slideshow to be played. The name is
            optional. If no name is specified or no slideshow with the specified
            name exists, the current slideshow is used.
        :type slideshow: str
        """
        # Stop playing current slideshow.
        self.stop_slideshow()
        # Switch to new slideshow if specified. Continue to use current
        # slideshow if new slideshow does not exist.
        if slideshow is not None:
            new_root = self._slideshows.get(slideshow, self.root)
            if new_root is not self.root:
                Window.add_widget(new_root)
                Window.remove_widget(self.root)
                self.root = new_root

        # Start playing new slideshow.
        self.root.play()

    def stop_slideshow(self):
        if self.root is not None:
            self.root.stop()
