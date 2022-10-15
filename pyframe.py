"""
"""

import logging
import repository.local
import repository.webdav
import yaml

from repository import Index
from repository import Repository
from slideshow import Slideshow

from kivy.app import App
from kivy.logger import Logger, LOG_LEVELS
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout


class MainApp(App):
    """
    """

    def build(self):
        """Build Kivy application.

        Loads the application configuration from the default configuration file.
        Creates configured repositories and builds an index across the latter.
        """
        # Set log level of default python Logger. This logger is used by non-kivy dependent components.
        logging.basicConfig(level=logging.DEBUG)
        # Set log level of kivy logger.
        Logger.setLevel(LOG_LEVELS["debug"])

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

        # Exit application if no repositories have been defined.
        if not 'repositories' in config:
            Logger.critical("Configuration: Exiting application as no repositories have been defined.")
            App.get_running_app().stop()

        # Create repositories.
        for uuid, rep_config in config['repositories'].items():
            # Skip disabled repositories.
            if rep_config.get('enabled') == False:
                Logger.info(f"Configuration: Skipping repository '{uuid}' as it has been disabled.")
                continue
            # Create repository of the specified type and build index.
            if rep_config.get('type') == "local":

                # Extract defined parameters (keys).
                keys = set(rep_config.keys())
                # Define allowed and required parameters (keys).
                required_keys = {"root"}
                allowed_keys = {"type", "root", "enabled"}

                # Report error if minimum required parameters have not been defined.
                if not required_keys.issubset(keys):
                    Logger.error(f"Configuration: Skipping repository '{uuid}' as its configuration is incomplete.")
                else:
                    # Warn if additional, unused parameters have been defined.
                    if not keys.issubset(allowed_keys):
                        Logger.warn(f"Configuration: Configuration of repository '{uuid}' contains additional, unused parameters.")

                    Logger.debug(f"Configuration: Creating repository '{uuid}' and building index.")
                    rep = repository.local.Repository(uuid, rep_config['root'], index=index)
#                    index.build(rep, rebuild=True)
                    index.build(rep, rebuild=False)

            if rep_config.get('type') == "webdav":

                # Extract defined parameters (keys).
                keys = set(rep_config.keys())
                # Define allowed and required parameters (keys).
                required_keys = {"url", "user", "password"}
                allowed_keys = {"type", "url", "root", "user", "password", "enabled"}

                # Report error if minimum required parameters have not been defined.
                if not required_keys.issubset(keys):
                    Logger.error(f"Configuration: Skipping repository '{uuid}' as its configuration is incomplete.")
                else:
                    # Warn if additional, unused parameters have been defined.
                    if not keys.issubset(allowed_keys):
                        Logger.warn(f"Configuration: Configuration of repository '{uuid}' contains additional, unused parameters.")

                    Logger.debug(f"Configuration: Creating repository '{uuid}' and building index.")
                    rep_config['cache'] = config['cache']
                    rep = repository.webdav.Repository(uuid, rep_config, index=index)
#                    index.build(rep, rebuild=True)
                    index.build(rep, rebuild=False)

        # Exit application if no valid repositories have been defined.
        if len(Repository._repositories.items()) == 0:
            Logger.critical("Configuration: Exiting application as no valid repositories have been defined.")
            App.get_running_app().stop()

        # Change to full screen mode.
        #Window.fullscreen = 'auto'
        Window.size = (990, 512)

        # Exit application if no slideshow has been defined.
        if not 'slideshow' in config:
            Logger.critical("Configuration: Exiting application as no slideshow has been defined.")
            App.get_running_app().stop()

        # Extract parameters from root config which shall be passed on to slideshow.
        args = {key: config[key] for key in ('rotation', 'bgcolor')}
        # Add slide show as root widget and adjust size to size of window.
        root = Slideshow(index, config['slideshow'], **args)
        return root


if __name__ == "__main__":
    MainApp().run()
