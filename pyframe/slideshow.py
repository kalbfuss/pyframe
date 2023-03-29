"""Module providing slideshow class."""

from repository import Index, RepositoryFile, IOError

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget

from . import PLAY_STATE

from pyframe.content import SlideshowImage, SlideshowVideo


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

    def __compile_filter_criteria(self):
        """Compile filter criteria.

        Helper function to compile filter criteria from the slideshow
        configuration and convert them into criteria compatible with a selective
        index iterator. Filter criteria are stored in the attribute _criteria
        of the object.
        """
        config = self._config
        self._criteria = dict()

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
                Logger.debug(f"Slideshow: Filtering for tags '{value}' from criterion 'tags' in slideshow '{self._name}'.")
                self._criteria['tags'] = value

            # Filter out excluded tags.
            if key == "excluded_tags":
                if value is None or value == "":
                    raise InvalidSlideshowConfigurationError(f"At least one tag must be specified for parameter 'excluded_tags' in slideshow '{self._name}'.", config)
                # Convert to list if single value specified.
                if type(value) == str:
                    value = [value]
                Logger.debug(f"Slideshow: Excluding tags '{value}' from criterion 'excluded_tags' in slideshow '{self._name}'.")
                # Add or append criterion
                if 'excluded_tags' not in self._criteria:
                    self._criteria['excluded_tags'] = value
                else:
                    self._criteria['excluded_tags'] += value

            # Filter out excluded tags.
            if key == "always_excluded_tags":
                if value is None or value == "":
                    raise InvalidSlideshowConfigurationError(f"At least one tag must be specified for parameter 'always_excluded_tags' in slideshow '{self._name}'.", config)
                # Convert to list if single value specified.
                if type(value) == str:
                    value = [value]
                # Add or append criterion
                Logger.debug(f"Slideshow: Excluding tags '{value}' from criterion 'always_excluded_tags' in slideshow '{self._name}'.")
                if 'excluded_tags' not in self._criteria:
                    self._criteria['excluded_tags'] = value
                else:
                    self._criteria['excluded_tags'] += value

    def __init__(self, name, index, config):
        """Initialize slideshow instance.

        :param name: name of slideshow.
        :type name: str
        :param index: index of files in active repositories.
        :type index: repository.Index
        :param config: slideshow configuration from configuration file section.
        :type config: dict
        :raises InvalidSlideshowConfigurationError:
        """
        AnchorLayout.__init__(self, anchor_x='center', anchor_y='center')
        self._name = name
        self._index = index
        self._config = config
        self._play_state = PLAY_STATE.STOPPED
        self._event = None
        self._current_widget = None
        self._iterator = None

        # Make sure only valid parameters have been specified.
        valid_keys = {'always_excluded_tags', 'bg_color', 'excluded_tags', 'file_types', 'label_content', 'label_duration', 'label_font_size', 'label_mode', 'label_padding', 'most_recent', 'order', 'orientation', 'pause', 'repositories', 'sequence', 'resize', 'rotation', 'tags'}
        keys = set(config.keys())
        if not keys.issubset(valid_keys):
            raise InvalidSlideshowConfigurationError(f"The configuration of slideshow '{self._name}' contains additional parameters. Only the slideshow parameters {valid_keys} are accepted, but the additional parameter(s) {keys.difference(valid_keys)} has/have been specified.", config)

        # Compile filter criteria for use with selective index iterator.
        self.__compile_filter_criteria()
        # Register event fired upon slideshow content changes.
        self.register_event_type('on_content_change')

    def _create_widget(self, file):
        """Create widget for display of the specified file.

        :param file: file to be displayed
        :type file: repository.File
        :rtype: Widget
        """
        if file.type == RepositoryFile.TYPE_IMAGE:
            widget = SlideshowImage(file, self._config)
        elif file.type == RepositoryFile.TYPE_VIDEO:
            widget = SlideshowVideo(file, self._config)
        return widget

    def _create_next_widget(self, previous=False):
        """Return widget for the next file in the slideshow.

        Alternatively, a widget for the previous file in the slideshow may be
        returend by setting the 'previous' flag to True.

        Catches any exception that occurs during file retrieval and skips the
        respective file. An empty widget is returned after 5 failed attempts.
        If the end of the iteration is reached, the iteration is restarted.

        :param previous: Set to True if widget for previous file shall be
            returend.
        :type previous: bool
        :return: next file in the slideshow.
        :rtype: Widget
        """
        attempts = 0
        while True:
            try:
                # Attempt to retrieve next file in repository.
                if previous is False:
                    file = next(self._iterator)
                # Or attempt to retrieve previous file in repository if previous
                # flag has been set.
                else:
                    file = self._iterator.previous()
                widget = self._create_widget(file)
                # Exit loop if no exception occurred.
                break
            # Create new iterator if end of iteration has been reached and try
            # again.
            except StopIteration:
                Logger.info("Slideshow: End of slideshow reached. Restarting slideshow.")
                self._iterator = self._index.iterator(**self._criteria)
                # Make sure to return next and not previous file.
                previous = False
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

    @property
    def file_count(self):
        """Return number of files in the slideshow."""
        # Return initial count of current iterator if exists.
        if self._iterator is not None:
            return self._iterator.length
        else:
            # Create temporary iterator otherwise to determine length.
            return self._index.iterator(**self._criteria).length

    @property
    def current_file(self):
        """Return linked repository file for the current content widget.

        Note that the method may return None if no currrent file is available,
        e.g. if the slideshow is stopped.

        :return: linked repository file
        :rtype: repository.file
        """
        if self._current_widget is not None:
            return self._current_widget.file
        else: return None

    @property
    def name(self):
        """Return name of the slidshow.

        :return: name of slideshow
        :rtype: str
        """
        return self._name

    @property
    def play_state(self):
        """Return play state.

        See enumeration PLAY_STATE for possible values.

        :return: play state
        :rtype: str
        """
        return self._play_state

    def next(self, reschedule=True, previous=False):
        """Display next file in index."""
        # Skip if not playing.
        if self._play_state == PLAY_STATE.STOPPED: return
        # Unschedule and re-schedule callback function
        if reschedule and self._play_state == PLAY_STATE.PLAYING and self._event is not None:
            self._event.cancel()
            self._event = Clock.schedule_interval(self._clock_callback, self._config['pause'])
        # Remove current widget from layout.
        if self._current_widget is not None:
            self.remove_widget(self._current_widget)
        # Make widget from next file the current widget.
        self._current_widget = self._create_next_widget(previous)
        # Stop playing content in current widget if slideshow is paused.
        if self._play_state == PLAY_STATE.PAUSED and hasattr(self._current_widget, 'stop'):
            self._current_widget.stop()
        # Add current widget to layout.
        self.add_widget(self._current_widget)
        # Fire event to indicate content change
        self.dispatch('on_content_change', self)

    def on_content_change(self, *largs):
        """Default handler for 'on_content_change' event."""
        # Do nothing.
        Logger.debug("Slideshow: Ignoring event 'on_content_change' since it should have been handled elsewhere.")

    def pause(self):
        """Pause playing slideshow."""
        # Skip if already paused.
        if self._play_state == PLAY_STATE.PAUSED: return
        # Unschedule the callback function.
        if self._event is not None:
            self._event.cancel()
            self._event = None
        # Stop playing content in current widget.
        if hasattr(self._current_widget, 'stop'):
            self._current_widget.stop()
        # Update state.
        self._play_state = PLAY_STATE.PAUSED

    def play(self):
        """Start playing slideshow."""
        # Skip if already playing.
        if self._play_state == PLAY_STATE.PLAYING: return
        # Create selective index iterator with sorting/filter criteria from the
        # slideshow configuration.
        self._iterator = self._index.iterator(**self._criteria)
        # Create current widget from first file and add to layout.
        self._current_widget = self._create_next_widget()
        self.add_widget(self._current_widget)
        # Schedule callback function to start playing slideshow.
        self._event = Clock.schedule_interval(self._clock_callback, self._config['pause'])
        # Update state.
        self._play_state = PLAY_STATE.PLAYING
        # Fire event to indicate content change.
        self.dispatch('on_content_change', self)

    def previous(self, reschedule=True):
        """Display previous file in index."""
        self.next(previous=True)

    def stop(self):
        """Stop playing slideshow."""
        # Skip if already stopped.
        if self._play_state == PLAY_STATE.STOPPED: return
        # Unschedule callback function.
        if self._event is not None:
            self._event.cancel()
            self._event = None
        # Remove current widget from layout.
        if self._current_widget is not None:
            self.remove_widget(self._current_widget)
        # Reset selective index iterator with sorting/filter criteria from the
        # slideshow configuration.
        self._iterator = None
        self._current_widget = None
        # Update state otherwise.
        self._play_state = PLAY_STATE.STOPPED
        # Fire event to indicate content change.
        self.dispatch('on_content_change', self)

    def _clock_callback(self, dt):
        """Clock callback function. Display the next file in the slideshow."""
        # Display next file in repository.
        self.next(reschedule=False)
