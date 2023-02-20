"""Module providing slideshow class."""

from repository import Index, RepositoryFile

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.anchorlayout import AnchorLayout

from slideshow import SlideshowImage, SlideshowVideo


class InvalidSlideshowConfigurationError(Exception):
    """Invalid slideshow configuration error."""

    def __init__(self, msg, config=None):
        """Initialize class instance."""
        super().__init__(msg)
        self.config = config


class Slideshow(AnchorLayout):
    """Slideshow widget.

    The slideshow widget iterates through files in an index (repository.Index)
    and displays them by creating the corresponding widgets. Currently, images (SlideshowImage) and videos (SlideshowVideo) are supported.
    Slideshow behavior can be influenced by the slide show configuration and
    optional parameters, which are passed to the constructor.
    """

    def __init__(self, index, config, **args):
        """Initialize slideshow instance.

        :param index: Index of files in active repositories.
        :type index: repository.Index
        :param config: Slideshow configuration from configuration file section.
        :type config: dict
        :raises InvalidSlideshowConfigurationError:
        """
        AnchorLayout.__init__(self, anchor_x='center', anchor_y='center')
        self._index = index
        self._config = config
        self._args = args

        self._criteria = dict()
        # Compile filter criteria from slideshow configuration.
        for key, value in config.items():

            # Retrieve files in a specific or random order.
            if key == "sequence":
                if value == "random":
                    self._criteria['order'] = Index.ORDER_RANDOM
                elif value == "date" and config['order'] == "ascending":
                    self._criteria['order'] = Index.ORDER_DATE_ASC
                elif value == "date" and config['order'] == "descending":
                    self._criteria['order'] = Index.ORDER_DATE_DESC
                elif value == "name" and config['order'] == "ascending":
                    self._criteria['order'] = Index.ORDER_NAME_ASC
                elif value == "name" and config['order'] == "descending":
                    self._criteria['order'] = Index.ORDER_NAME_DESC
                else:
                    raise InvalidSlideshowConfigurationError(f"Invalid value '{value}' for slideshow parameter 'sequence' specified.", config)

            # Limit iteration to the n most recent files based on the creation
            # date.
            if key == "mostRecent":
                if int(config['mostRecent']) > 0:
                    self._criteria['mostRecent'] = int(config['mostRecent'])
                else:
                    raise InvalidSlideshowConfigurationError(f"Invalid value '{value}' for slideshow parameter 'mostRecent' specified.", config)

            # Filter for orientation of content.
            if key == "orientation":
                if value == "landscape":
                    self._criteria['orientation'] = RepositoryFile.ORIENTATION_LANDSCAPE
                elif value == "portrait":
                    self._criteria['orientation'] = RepositoryFile.ORIENTATION_PORTRAIT
                else:
                    raise InvalidSlideshowConfigurationError(f"Invalid value '{value}' for slideshow parameter 'orientation' specified.", config)

            # Filter for file type.
            if key == "fileType":
                if value is None:
                    raise InvalidSlideshowConfigurationError("At least one file type must be specified for slideshow parameter 'fileType'.", config)
                # Convert to list if single value specified.
                if type(value) == str:
                    value = [value]
                types = list()
                for fileType in value:
                    if fileType == "images":
                        types.append(RepositoryFile.TYPE_IMAGE)
                    elif fileType == "videos":
                        types.append(RepositoryFile.TYPE_VIDEO)
                    else:
                        raise InvalidSlideshowConfigurationError(f"Invalid type '{fileType}' for slideshow parameter 'fileType' specified.", config)
                self._criteria['type'] = types

            # Filter for file tags.
            if key == "tags":
                if value is None:
                    raise InvalidSlideshowConfigurationError("At least one tag must be specified for slideshow parameter 'tags'.", config)
                # Convert to list if single value specified.
                if type(value) == str:
                    value = [value]
                self._criteria['tags'] = value

        # Create selective index iterator with sorting/filter criteria from the
        # slideshow configuration.
        self._iterator = self._index.iterator(**self._criteria)

        # Create current widget from first file, add to layout and start playing.
        file = next(self._iterator)
        self._currentWidget = self._create_widget(file)
        self.add_widget(self._currentWidget)
        # Create next widget from second file
        try:
            file = next(self._iterator)
            # Create new iterator if end of iteration has been reached.
        except StopIteration:
            self._iterator = self._index.iterator(**self._criteria)
            file = next(self._iterator)

        self._nextWidget = self._create_widget(file)

        # Bind keyboard listener
        Window.bind(on_keyboard=self._on_keyboard)
        # Set clock interval and callback function
        Clock.schedule_interval(self._clock_callback, config['pause'])

    def _create_widget(self, file):
        """Create widget for display of the specified file.

        :param file: File to be displayed
        :type file: repository.File
        :rtype: Widget
        """
        if file.type == RepositoryFile.TYPE_IMAGE:
            widget = SlideshowImage(file, self._config)
        elif file.type == RepositoryFile.TYPE_VIDEO:
            widget = SlideshowVideo(file, self._config)
        return widget

    def next_file(self):
        """Display next file in the index."""
        # Remove current widget from layout.
        self.remove_widget(self._currentWidget)
        # Make next widget the current widget.
        self._currentWidget = self._nextWidget
        # Add current widget to layout.
        self.add_widget(self._currentWidget)
        # Retrieve next file in repository.
        try:
            file = next(self._iterator)
        # Create new iterator if end of iteration has been reached.
        except StopIteration:
            Logger.info("End of iteration. Restarting iteration.")
            self._iterator = self._index.iterator(**self._criteria)
            file = next(self._iterator)
        # Create widget for next frame.
        self._nextWidget = self._create_widget(file)

    def _clock_callback(self, dt):
        """Clock callback function. Display the next file in the slideshow."""
        # Display next file in repository.
        self.next_file()

    def _on_keyboard(self, window, key, *args):
        """Handle keyboard events.

        The following events are currently supported:
        - Right arrow: Show net file.
        - Left arrow: Show previous file (not yet implemented).
        - Escape: Exit application.
        """
        Logger.info(f"Key '{key}' pressed.")
        # Display previous file if left arrow pressed.
        if key == 276:
            # Not yet implemented as index iterators do not (yet) allow to go backwards.
            pass
        # Exit application if escape key pressed.
        elif key == 27:
            App.get_running_app().stop()
            # Display next file for all other keys
        else:
            Clock.unschedule(self._clock_callback)
            self.next_file()
            Clock.schedule_interval(self._clock_callback, self._config['pause'])
        return True
