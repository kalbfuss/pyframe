"""Module providing slideshow class."""

from repository import Index, RepositoryFile, IOError

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget

from pyframe import SlideshowImage, SlideshowVideo


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

    def __init__(self, name, index, config):
        """Initialize Slideshow instance.

        :param name: Name of slideshow.
        :type name: str
        :param index: Index of files in active repositories.
        :type index: repository.Index
        :param config: Slideshow configuration from configuration file section.
        :type config: dict
        :raises InvalidSlideshowConfigurationError:
        """
        AnchorLayout.__init__(self, anchor_x='center', anchor_y='center')
        self._name = name
        self._index = index
        self._config = config
        self._event = None
        self._currentWidget = None
        self._nextWidget = None
        self._iterator = None
        self._length = 0

        # Make sure only valid parameters have been specified.
        valid_keys = {'always_excluded_tags', 'bg_color', 'excluded_tags', 'file_types', 'most_recent', 'order', 'orientation', 'pause', 'repositories', 'sequence', 'resize', 'rotation', 'tags'}
        keys = set(config.keys())
        if not keys.issubset(valid_keys):
            raise InvalidSlideshowConfigurationError(f"The configuration of slideshow '{self._name}' contains additional parameters. Only the slideshow parameters {valid_keys} are accepted, but the additional parameter(s) {keys.difference(valid_keys)} has/have been specified.", config)

        self._criteria = dict()
        # Compile filter criteria from slideshow configuration.
        for key, value in config.items():

            # Filter repository by uuid.
            if key == "repositories":
                self._criteria['repository'] = value

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
                    raise InvalidSlideshowConfigurationError(f"Invalid value '{value}' for parameter 'sequence' in slideshow '{self._name}' specified. Acceptable values are 'name', 'date' and 'random'.", config)

            # Limit iteration to the n most recent files based on the creation
            # date.
            if key == "most_recent":
                if type(config['most_recent']) is int and config['most_recent'] > 0:
                    self._criteria['most_recent'] = int(config['most_recent'])
                else:
                    raise InvalidSlideshowConfigurationError(f"Invalid value '{value}' for parameter 'most_recent' in slideshow '{self._name}' specified. The value must be a positive integer.", config)

            # Filter for orientation of content.
            if key == "orientation":
                if value == "landscape":
                    self._criteria['orientation'] = RepositoryFile.ORIENTATION_LANDSCAPE
                elif value == "portrait":
                    self._criteria['orientation'] = RepositoryFile.ORIENTATION_PORTRAIT
                else:
                    raise InvalidSlideshowConfigurationError(f"Invalid value '{value}' for parameter 'orientation' in slideshow '{self._name}' specified. Acceptable values are 'landscape' and 'portrait'.", config)

            # Filter for file type.
            if key == "file_types":
                if value is None:
                    raise InvalidSlideshowConfigurationError(f"At least one file type must be specified for parameter 'file_type' in slideshow '{self._name}'.", config)
                # Convert to list if single value specified.
                if type(value) == str:
                    value = [value]
                types = list()
                for file_type in value:
                    if file_type == "images":
                        types.append(RepositoryFile.TYPE_IMAGE)
                    elif file_type == "videos":
                        types.append(RepositoryFile.TYPE_VIDEO)
                    else:
                        raise InvalidSlideshowConfigurationError(f"Invalid type '{file_type}' for parameter 'file_type' in slideshow '{self._name}' specified. Acceptable values are 'images' and 'videos'.", config)
                self._criteria['type'] = types

            # Filter for file tags.
            if key == "tags":
                if value is None or value == "":
                    raise InvalidSlideshowConfigurationError(f"At least one tag must be specified for parameter 'tags' in slideshow '{self._name}'.", config)
                # Convert to list if single value specified.
                if type(value) == str:
                    value = [value]
                self._criteria['tags'] = value

            # Filter out excluded tags.
            if key == "excluded_tags":
                if value is None or value == "":
                    raise InvalidSlideshowConfigurationError(f"At least one tag must be specified for parameter 'excluded_tags' in slideshow '{self._name}'.", config)
                # Convert to list if single value specified.
                if type(value) == str:
                    value = [value]
                # Add or append criterion
                if 'excluded_tags' not in self._criteria:
                    self._criteria['excluded_tags'] = value
                else:
                    self._criteria['excluded_tags'].append(*value)

            # Filter out excluded tags.
            if key == "always_excluded_tags":
                if value is None or value == "":
                    raise InvalidSlideshowConfigurationError(f"At least one tag must be specified for parameter 'always_excluded_tags' in slideshow '{self._name}'.", config)
                # Convert to list if single value specified.
                if type(value) == str:
                    value = [value]
                # Add or append criterion
                if 'excluded_tags' not in self._criteria:
                    self._criteria['excluded_tags'] = value
                else:
                    self._criteria['excluded_tags'].append(*value)

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

    def length(self):
        """Returns the number of files in the slideshow."""
        # Return initial count of current iterator if exists.
        if self._iterator is not None:
            return self._length()
        else:
            # Create temporary iterator otherwise to determine length.
            return self._index.iterator(**self._criteria).count()

    def _next_widget(self):
        """Return widget of the next file in the slideshow.

        Catches any exception that occurs during file retrieval and skips the
        respective file.

        :return: Next file in the slideshow.
        :rtype: Widget
        """
        attempts = 0
        while True:
            try:
                # Attempt to retrieve next file in repository.
                file = next(self._iterator)
                widget = self._create_widget(file)
                # Exit loop if no exception occurred
                break
            # Create new iterator if end of iteration has been reached and try
            # again.
            except StopIteration:
                Logger.info("Slideshow: End of iteration. Restarting iteration.")
                self._iterator = self._index.iterator(**self._criteria)
                continue
            # Log error if any other exception occurred and try again.
            except IOError as e:
                Logger.error(f"Slideshow: An I/O error occurred while retrieving the next file: {e.exception}.")
                continue
            finally:
                attempts = attempts + 1
                # Stop slideshow and return empty widget if number of attempts
                # exceeds limit.
                if attempts > 5:
                    Logger.error(f"Slideshow: Stopping slidewhow after {attempts} failed attempts to retrieve next file.")
                    self.stop()
                    return Widget()
        return widget

    def next(self):
        """Display next file in the index."""
        # Remove current widget from layout.
        self.remove_widget(self._currentWidget)
        # Make next widget the current widget.
        self._currentWidget = self._nextWidget
        # Add current widget to layout.
        self.add_widget(self._currentWidget)
        # Create widget for next frame.
        self._nextWidget = self._next_widget()

    def play(self):
        """Start playing slideshow."""
        # Skip if already playing
        if self._event is not None:
            return
        # Create selective index iterator with sorting/filter criteria from the
        # slideshow configuration.
        self._iterator = self._index.iterator(**self._criteria)
        # Save number of images in the slide show
        self._length = self._iterator.count()
        # Create current widget from first file, add to layout and start playing.
        self._currentWidget = self._next_widget()
        self.add_widget(self._currentWidget)
        # Create next widget from second file
        self._nextWidget = self._next_widget()
        # Schedule callback function
        self._event = Clock.schedule_interval(self._clock_callback, self._config['pause'])

    def stop(self):
        """Stop playing slideshow."""
        # Unschedule callback function
        if self._event is not None:
            self._event.cancel()
            self._event = None
        # Remove and destroy current widget
        if self._currentWidget is not None:
            self.remove_widget(self._currentWidget)
            self._currentWidget = None
        # Destroy next widget and iterator
        self._nextWidget = None
        self._iterator = None

    def _clock_callback(self, dt):
        """Clock callback function. Display the next file in the slideshow."""
        # Display next file in repository.
        self.next()
