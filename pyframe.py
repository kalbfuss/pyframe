"""Pyframe main module."""

import logging
import repository.local
import repository.webdav
import threading
import time
import yaml

from repository import Index
from repository import Repository, InvalidConfigurationError, InvalidUuidError
from slideshow import Slideshow

from kivy.app import App
from kivy.logger import Logger, LOG_LEVELS
from kivy.core.window import Window


def build_index(index, rep):
    """Build repository index (helper function)."""
    index.build(rep)


class PyframeApp(App):
    """Pyframe main application."""

    def build(self):
        """Build Kivy application.

        Loads the application configuration from the default configuration file.
        Creates configured repositories and builds an index across the latter.
        """
        # Set log level of default python Logger. This logger is used by non-kivy dependent components.
        logging.basicConfig(level=logging.DEBUG)
        # Set log level of kivy logger.
        Logger.setLevel(LOG_LEVELS["debug"])
        # Reduce logging by SQLAlchemy to errors.
        logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

        # Load configuration from yaml file.
        with open('./config.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)
        Logger.debug(f"Configuration: Configuration = {config}")

        # Exit application if no repositories have been defined.
        if 'repositories'not in config:
            Logger.critical("Configuration: Exiting application as no repositories have been defined.")
            App.get_running_app().stop()

        # Exit application if no slideshow has been defined.
        if 'slideshow' not in config:
            Logger.critical("Configuration: Exiting application as no slideshow has been defined.")
            exit()

        # Create/load index.
        if hasattr(config, 'index'):
            index_file = config['index']
        else:
            index_file = "./index.sqlite"
        index = Index(index_file)

        # Create repositories.
        for uuid, rep_config in config['repositories'].items():
            # Skip disabled repositories.
            if rep_config.get('enabled') is False:
                Logger.info(f"Configuration: Skipping repository '{uuid}' as it has been disabled.")
                continue
            try:
                # Create repository of the specified type and build index.
                if rep_config.get('type') == "local":
                    Logger.info(f"Creating local repository '{uuid}' and starting to build index in the background.")
                    rep = repository.local.Repository(uuid, rep_config, index=index)
                    threading.Thread(target=build_index, args=(index, rep)).start()

                if rep_config.get('type') == "webdav":
                    Logger.info(f"Configuration: Creating WebDav repository '{uuid}' and starting to build index in the background.")
                    rep_config['cache'] = config['cache']
                    rep = repository.webdav.Repository(uuid, rep_config, index=index)
                    threading.Thread(target=build_index, args=(index, rep)).start()

            # Catch any invalid configuration errors
            except InvalidConfigurationError:
                Logger.error(f"Skipping repository '{uuid}' as its configuraiton is invalid.")
            # Catch any invalid UUIR errors
            except InvalidUuidError:
                Logger.error(f"Skipping repository '{uuid}' as its UUID is invalid.")

        # Exit application if no valid repositories have been defined.
        if len(Repository._repositories.items()) == 0:
            Logger.critical("Configuration: Exiting application as no valid repositories have been defined.")
            App.get_running_app().stop()

        # Wait until index contains at least one entry.
        while index.count() < 2:
            time.sleep(1)
            Logger.info("Index still empty. Giving more time to build.")
        Logger.info(f"Proceeding with {index.count()} index entries.")

        # Change to full screen mode.
        #Window.fullscreen = 'auto'
        Window.size = (990, 512)

        # Extract parameters from root config which shall be passed on to slideshow.
        args = {key: config[key] for key in ('rotation', 'bgcolor')}
        # Add slide show as root widget and adjust size to size of window.
        root = Slideshow(index, config['slideshow'], **args)
        return root


if __name__ == "__main__":
    PyframeApp().run()
