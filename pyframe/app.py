"""Module providing Pyframe application."""

import logging
import repository.local
import repository.webdav
import threading
import time
import yaml

import kivy.app

from repository import Index
from repository import Repository, InvalidConfigurationError, InvalidUuidError
from . import Indexer, Handler, logHandler, Slideshow, Scheduler, InvalidSlideshowConfigurationError

from kivy.logger import Logger, LOG_LEVELS
from kivy.core.window import Window


class App(kivy.app.App):
    """Pyframe main application."""

    def _create_repositories(self, config, index):
        """Create file repositories from configuration."""
        # Exit application if no repositories have been defined.
        if 'repositories'not in config or type(config['repositories']) is not dict:
            Logger.critical("Configuration: Exiting application as no repositories have been defined.")
            App.get_running_app().stop()

        # Extract global repository configuration
        global_config = {key: config[key] for key in ('index_update_interval', 'index_update_at', 'cache') if key in config}

        # Create repositories.
        for uuid, rep_config in config['repositories'].items():
            # Skip disabled repositories.
            if rep_config.get('enabled') is False:
                Logger.info(f"Configuration: Skipping repository '{uuid}' as it has been disabled.")
                continue
            # Combine global and local configuration. Local configuration
            # settings supersede global settings.
            combined_config = global_config
            combined_config.update(rep_config)
            try:
                # Create repository of the specified type and queue for indexing.
                if rep_config.get('type') == "local":
                    Logger.info(f"Configuration: Creating local repository '{uuid}' and starting to build index in the background.")
                    rep = repository.local.Repository(uuid, combined_config, index=index)
                    interval = combined_config.get('index_update_interval', 0)
                    at = combined_config.get('index_update_at', None)
                    self._indexer.queue(rep, interval, at)

                if rep_config.get('type') == "webdav":
                    Logger.info(f"Configuration: Creating WebDav repository '{uuid}' and starting to build index in the background.")
                    rep = repository.webdav.Repository(uuid, combined_config, index=index)
                    interval = combined_config.get('index_update_interval', 0)
                    at = combined_config.get('index_update_at', None)
                    self._indexer.queue(rep, interval, at)

            # Catch any invalid configuration errors
            except InvalidConfigurationError:
                Logger.error(f"Configuration: Skipping repository '{uuid}' as its configuration is invalid.")
            # Catch any invalid UUIR errors
            except InvalidUuidError:
                Logger.error(f"Configuration: Skipping repository '{uuid}' as its UUID is invalid.")

        # Exit application if no valid repositories have been defined.
        if len(Repository._repositories.items()) == 0:
            Logger.critical("Configuration: Exiting application as no valid repositories have been defined.")
            App.get_running_app().stop()

    def _create_slideshows(self, config, index):
        """Create slideshows from configuration.

        Slideshow configurations are extracted from the 'slideshows' section
        in the configuration file. One slideshow is created per has entry.
        Slideshow instances are collected in the hash _slideshows, with the key
        being identical to the slideshow name in the configuration file.
        """
        # Exit application if no slideshow has been defined.
        if 'slideshows' not in config or type(config['slideshows']) is not dict:
            Logger.critical("Configuration: Exiting application as no slideshow has been defined.")
            exit()
            App.get_running_app().stop()

        # Create empty dictionary to collect slideshows
        self._slideshows = dict()
        # Extract global slideshow configuration
        global_config = {key: config[key] for key in ('rotation', 'bgcolor', 'fileTypes', 'mostRecent', 'order', 'orientation', 'pause', 'resize', 'sequence', 'tags') if key in config}

        # Create slideshows from configuration.
        for slideshow, slideshow_config in config['slideshows'].items():
            # Combine global and local configuration. Local configuration
            # settings supersede global settings.
            combined_config = global_config
            combined_config.update(slideshow_config)
            # Create new slideshow and add to hash
            try:
                self._slideshows[slideshow] = Slideshow(index, combined_config)
            except InvalidSlideshowConfigurationError:
                Logger.error(f"Configuration: Skipping repository '{repository}' as its configuration is invalid.")

        # Exit application if no valid repositories have been defined.
        if len(self._slideshows.items()) == 0:
            Logger.critical("Configuration: Exiting application as no valid slideshows have been defined.")
            App.get_running_app().stop()

    def build(self):
        """Build Kivy application.

        Loads the application configuration from the default configuration file.
        Creates configured repositories and builds an index across the latter.
        """
        # Set log level of default python Logger. This logger is used by non-kivy dependent components.
        logging.basicConfig(level=logging.INFO)
        # Set log level of kivy logger.
        Logger.setLevel(LOG_LEVELS["info"])
        # Reduce logging by IPTCInfo and exifread to errors.
        logging.getLogger("iptcinfo").setLevel(logging.ERROR)
        logging.getLogger("exifread").setLevel(logging.ERROR)
        # Reduce logging by SQLAlchemy to errors.
        logging.getLogger("sqlalchemy").setLevel(logging.WARN)
        # Redirect all log messages from the background thread into a rotated
        # log file using a special log handler.
        global logHandler
        logHandler = Handler("./log", "indexer")
        logging.getLogger().addHandler(logHandler)

        # Load configuration from yaml file.
        with open('./config.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)
        Logger.debug(f"Configuration: Configuration = {config}")

        # Create/load index.
        if hasattr(config, 'index'):
            index_file = config['index']
        else:
            index_file = "./index.sqlite"
        index = Index(index_file)

        # Create background indexer.
        self._indexer = Indexer(index)
        # Create repositories.
        self._create_repositories(config, index)
        # Start building index in the background.
        self._indexer.start()
        # Create slideshows.
        self._create_slideshows(config, index)

        # Change to full screen mode.
#        Window.fullscreen = 'auto'
        Window.size = (800, 450)
        # Disable display of mouse cursor
        Window.show_cursor = False

        # Make first slideshow the main root widget
        root = next(iter(self._slideshows.values()))

        # Wait until index contains at least one entry.
        while root.length() == 0:
            time.sleep(1)
            Logger.info("Slideshow still empty. Giving more time to build index.")
        Logger.info(f"Proceeding with {root.length()} files in slideshow.")

        # Create scheduler if configured.
        if 'schedule' in config:
            self._scheduler = Scheduler(config['schedule'], self)
        else:
            # Start playing slideshow immediately otherwise
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
