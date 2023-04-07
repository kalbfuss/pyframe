"""Module providing slideshow class."""

from repository import Index, RepositoryFile, IoError

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget

from repository import ConfigError, check_param, check_valid_required

from .content import ErrorMessage, SlideshowImage, SlideshowVideo
from .controller import PLAY_STATE


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
                check_param('sequence', config, options={"random", "date", "name"})
                check_param('order', config, options={"ascending", "descending"})
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

            # Limit iteration to the n most recent files based on the creation
            # date.
            if key == "most_recent":
                check_param('most_recent', config, is_int=True, gr=0)
                self._criteria['most_recent'] = config['most_recent']

            # Filter for orientation of content.
            if key == "orientation":
                check_param('orientation', config, options={"landscape", "portrait"})
                map = {'landscape': RepositoryFile.ORIENTATION_LANDSCAPE, 'portrait': RepositoryFile.ORIENTATION_PORTRAIT}
                self._criteria['orientation'] = map[value]

            # Filter for file type.
            if key == "file_types":
                check_param('file_types', config, recurse=True, options={"images", "videos"})
                # Convert to list if single value specified.
                if type(value) == str: value = [value]
                map = {'images': RepositoryFile.TYPE_IMAGE, 'videos': RepositoryFile.TYPE_VIDEO}
                self._criteria['type'] = [ map[type] for type in value ]

            # Filter for file tags.
            if key == "tags":
                check_param('tags', config)
                # Convert to list if single value specified.
                if type(value) == str: value = [value]
                Logger.debug(f"Slideshow: Filtering for tags '{value}' from criterion 'tags' in slideshow '{self._name}'.")
                self._criteria['tags'] = value

            # Filter out excluded tags.
            if key == "excluded_tags":
                check_param('excluded_tags', config)
                # Convert to list if single value specified.
                if type(value) == str: value = [value]
                # Add or append criterion
                Logger.debug(f"Slideshow: Excluding tags '{value}' from criterion 'excluded_tags' in slideshow '{self._name}'.")
                self._criteria['excluded_tags'] = self._criteria.get('excluded_tags', []) + value

            # Filter out excluded tags.
            if key == "always_excluded_tags":
                check_param('always_excluded_tags', config)
                # Convert to list if single value specified.
                if type(value) == str: value = [value]
                # Add or append criterion
                Logger.debug(f"Slideshow: Excluding tags '{value}' from criterion 'always_excluded_tags' in slideshow '{self._name}'.")
                self._criteria['excluded_tags'] = self._criteria.get('excluded_tags', []) + value

    # Required and valid configuration parameters
    CONF_REQ_KEYS = {'bg_color', 'label_content', 'label_duration', 'label_font_size', 'label_mode', 'label_padding', 'pause', 'resize', 'rotation'}
    CONF_VALID_KEYS = {'always_excluded_tags', 'excluded_tags', 'file_types', 'most_recent', 'order', 'orientation', 'repositories', 'sequence', 'tags'} | CONF_REQ_KEYS

    def __init__(self, name, index, config):
        """Initialize slideshow instance.

        :param name: name of slideshow.
        :type name: str
        :param index: index of files in active repositories.
        :type index: repository.Index
        :param config: slideshow configuration from configuration file section.
        :type config: dict
        :raises ConfigError:
        """
        AnchorLayout.__init__(self, anchor_x='center', anchor_y='center')
        self._name = name
        self._index = index
        self._config = config
        self._play_state = PLAY_STATE.STOPPED
        self._next_event = None
        self._current_widget = None
        self._iterator = None

        # Check the configuration for valid and required parameters.
        check_valid_required(config, self.CONF_VALID_KEYS, self.CONF_REQ_KEYS)
        # Check parameter values.
        check_param('pause', config, is_int=True, gr=0)
        check_param('rotation', config, is_int=True, options={0, 90, 180, 270})
        check_param('bg_color', config, is_color=True)
        check_param('label_content', config, options={"description", "full", "short"})
        check_param('label_duration', config, is_int=True, gr=0)
        check_param('label_font_size', config, gr=0, le=0.2)
        check_param('label_mode', config, options={"auto", "off", "on"})
        check_param('label_padding', config, gr=0, le=0.2)
        check_param('resize', config, options={"fit", "fill"})

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
        # Return error message widget if the slideshow does not contain any
        # files and re-create index iterator.
        if self._iterator.length == 0:
            Logger.error("Slideshow: The slideshow does not contain any files.")
            # Re-create index iterator for a new chance. Possibly, the
            # background indexer has added new files in the meantime.
            self._iterator = self._index.iterator(**self._criteria)
            return ErrorMessage("The slideshow does not contain any files.", self._config)

        # Make up to 5 attempts to create the next content widget. Return an
        # error message widget otherwise.
        attempts = 0
        while True:
            try:
                # Attempt to retrieve next file in repository.
                if previous is False:
                    file = next(self._iterator)
                # Or attempt to retrieve previous file in repository if previous
                # flag is set.
                else:
                    file = self._iterator.previous()
                widget = self._create_widget(file)
                # Exit loop if no exception occurred.
                break
            # Create new iterator if end of slideshow has been reached and try
            # again.
            except StopIteration:
                Logger.info("Slideshow: End of slideshow reached. Restarting slideshow.")
                self._iterator = self._index.iterator(**self._criteria)
                # Make sure to return next and not previous file.
                previous = False
                continue
            # Log error if any other exception occurred and try again.
            except IoError as e:
                Logger.error(f"Slideshow: An I/O error occurred while retrieving the next file: {e.exception}.")
                continue
            finally:
                attempts = attempts + 1
                # Restart slideshow and return error message widget if number of
                # failed attempts exceeds 5.
                if attempts >= 5:
                    Logger.error(f"Slideshow: Restarting slideshow after {attempts} failed attempts to retrieve the next file.")
                    # Re-create index iterator for a new chance. Possibly, the
                    # background indexer has updated the index in the meantime.
                    self._iterator = self._index.iterator(**self._criteria)
                    return ErrorMessage(f"Restarting slideshow after {attempts} failed attempts to retrieve the next file.", self._config)
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
        # Skip if not playing or paused.
        if self._play_state == PLAY_STATE.STOPPED: return
        # Unschedule and re-schedule callback function.
        if reschedule and self._play_state == PLAY_STATE.PLAYING and self._next_event is not None:
            self._next_event.cancel()
            self._next_event = Clock.schedule_interval(self._clock_callback, self._config['pause'])
        # Remove current widget from layout.
        if self._current_widget is not None:
            self.remove_widget(self._current_widget)
        # Make widget from next file the current widget.
        self._current_widget = self._create_next_widget(previous)
        # Stop playing content in current widget if slideshow is paused.
        if self._play_state == PLAY_STATE.PAUSED:
            self._current_widget.stop()
        # Add current widget to layout.
        self.add_widget(self._current_widget)
        # Fire event to indicate content change
        self.dispatch('on_content_change', self)

    def on_content_change(self, *largs):
        """Default handler for 'on_content_change' event."""
        # Do nothing.
        Logger.warn("Slideshow: Ignoring event 'on_content_change' since it should have been handled elsewhere.")

    def pause(self):
        """Pause playing slideshow."""
        # Skip if already paused or stopped.
        if self._play_state == PLAY_STATE.PAUSED or self._play_state == PLAY_STATE.STOPPED: return
        # Unschedule the callback function.
        if self._next_event is not None:
            self._next_event.cancel()
            self._next_event = None
        # Stop playing content in current widget.
        self._current_widget.stop()
        # Update state.
        self._play_state = PLAY_STATE.PAUSED

    def play(self):
        """Start playing slideshow."""
        # Skip if already playing.
        if self._play_state == PLAY_STATE.PLAYING: return
        # Create new selective index iterator with sorting/filter criteria from
        # the slideshow configuration if not paused.
        if self._play_state != PLAY_STATE.PAUSED:
            self._iterator = self._index.iterator(**self._criteria)
        # Remove current widget from layout.
        if self._current_widget is not None:
            self.remove_widget(self._current_widget)
        # Create current widget from first file and add to layout.
        self._current_widget = self._create_next_widget()
        self.add_widget(self._current_widget)
        # Schedule callback function to start playing slideshow.
        self._next_event = Clock.schedule_interval(self._clock_callback, self._config['pause'])
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
        if self._next_event is not None:
            self._next_event.cancel()
            self._next_event = None
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
