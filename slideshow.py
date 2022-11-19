"""Module providing slideshow and related classes."""

from repository import Index, RepositoryFile

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Color, Rectangle
from kivy.logger import Logger
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.image import AsyncImage
from kivy.uix.video import Video
from kivy.uix.widget import Widget


class SlideshowVideo(Widget):
    """Video slideshow widget.

    Loads the video from the specified File and starts playing it as soon as the
    widget becomes visible. The video is scaled to fit the entire widget,
    respecting the aspect ratio.
    """

    def __init__(self, file, rotation=0, bgcolor=[1, 1, 1]):
        """Initialize slideshow video instance.

        :param file: Repository file instance for the video to be displayed.
        :type file: repository.File
        :param rotation: Angle in degrees by which the video is rotated clockwise.
        :type rotation: int
        :param bgolor: Canvas background color for areas, which are not covered by the video. The default ist [1, 1, 1] (white).
        :type bgcolor: list of float (3x)
        """
        Widget.__init__(self)
        self._file = file
        self._rotation = file.rotation - rotation
        self._bgcolor = bgcolor
        self._video = Video(source=file.source, state='stop', options={'allow_stretch': True, 'eos': 'loop'})
        self.add_widget(self._video)
        # Call update_canvas method when the size of the widget changes.
        self.bind(size=self.update_canvas)
        # Call autoplay method when the widget becomes visible/invisible.
        self.bind(parent=self.autoplay)

    def autoplay(self, *args):
        """Start/stop playing the video when the widget becomes visible/invisible."""
        if self.parent is None:
            self._video.state = 'stop'
        else:
            self._video.state = 'play'

    def update_canvas(self, *args):
        """Update canvas when the size of the widget changes."""
        # Clear before and after groups of video canvas.
        self._video.canvas.before.clear()
        self._video.canvas.after.clear()

        # Fill canvas with background color.
        with self._video.canvas.before:
            Color(self._bgcolor)
            Rectangle(pos=(0, 0), size=self.size)

        # Rotate canvas if required.
        if (self._rotation != 0):
            # Determine widget and image aspect ratios.
            widget_ratio = self.width/self.height
            # We need to rely on the file meta data in this case since the Kivy
            # video class does not have a video_ratio attribute and the
            # dimensions of the widget have not been adjusted yet.
            video_ratio = self._file.width/self._file.height
            # Correct image aspect ratio for image rotation. i.e. aspect ratio
            # corresponds to the ratio after rotation.
            if abs(self._rotation) == 90 or abs(self._rotation == 270):
                video_ratio = 1/video_ratio

            # Determine required maximum dimension for the rotation
            # transformation based on aspect ratios.
            if widget_ratio > video_ratio and video_ratio > 1:
                max_dim = round(self.height*video_ratio)
            elif widget_ratio <= video_ratio and video_ratio >= 1:
                max_dim = self.width
            elif widget_ratio >= video_ratio and video_ratio <= 1:
                max_dim = self.height
            else:  # widget_ratio < image_ratio and image_ratio < 1
                max_dim = round(self.width/video_ratio)

            # Set size of image widget to square with maximum dimension
            self._video.size = (max_dim, max_dim)
            # Adjust position of image widget within slideshow image widget
            # to center rotated image.
            self._video.x = round(self.x + (self.width - max_dim)/2)
            self._video.y = round(self.y + (self.height - max_dim)/2)

            # Log debug information
#            Logger.debug(f"Video uuid: {self._file.uuid}")
#            Logger.debug(f"Video type: {self._file.type}")
#            Logger.debug(f"Video source: {self._file.source}")
#            Logger.debug(f"Video orientation: {self._file.orientation}")
#            Logger.debug(f"Video rotation: {self._file.rotation}")
#            Logger.debug(f"Total rotation: {self._rotation}")
#            Logger.debug(f"Widget width: {self.width}")
#            Logger.debug(f"Widget height: {self.height}")
#            Logger.debug(f"Widget aspect ratio: {widget_ratio}")
#            Logger.debug(f"max_dim: {max_dim}")
#            Logger.debug(f"Video width: {self._video.width}")
#            Logger.debug(f"Video height: {self._video.height}")
#            Logger.debug(f"Video aspect ratio: {video_ratio}")
#            Logger.debug(f"Video x: {self._video.x}")
#            Logger.debug(f"Video y: {self._video.y}")
#            Logger.debug(f"Video center: {self._video.center}")

            # Apply rotation.
            with self._video.canvas.before:
                PushMatrix()
                Rotate(angle=self._rotation, origin=self._video.center, axis=(0, 0, 1))
            with self._video.canvas.after:
                PopMatrix()
        else:
            self._video.size = self.size


class SlideshowImage(Widget):
    """Image slideshow widget.

    Loads the image from the specified File and starts playing it as soon as the
    widget becomes visible. The image is scaled to fit the entire widget,
    respecting the aspect ratio.
    """

    def __init__(self, file, rotation=0, bgcolor=[1, 1, 1]):
        """Initialize slideshow image instance.

        :param file: Repository file instance for the image to be displayed.
        :type file: repository.File
        :param rotation: Angle in degrees by which the image is rotated clockwise.
        :type rotation: int
        :param bgolor: Canvas background color for areas, which are not covered by the image. The default ist [1, 1, 1] (white).
        :type bgcolor: list of float (3x)
        """
        Widget.__init__(self)
        self._file = file
        self._rotation = file.rotation - rotation
        self._bgcolor = bgcolor
        self._image = AsyncImage(source=file.source, allow_stretch=True)
        self.add_widget(self._image)
        # Call update_canvas method when the size of the widget changes.
        self.bind(size=self.update_canvas)

    def update_canvas(self, *args):
        """Update canvas when the size of the widget changes."""
        # Clear before and after groups of image canvas.
        self._image.canvas.before.clear()
        self._image.canvas.after.clear()

        # Fill canvas with background color.
        with self._image.canvas.before:
            Color(self._bgcolor)
            Rectangle(pos=(0, 0), size=self.size)

        # Rotate canvas if required.
        if self._rotation != 0:
            # Determine aspect ratios of image slideshow widget (this widget)
            # and image.
            widget_ratio = self.width/self.height
#           image_ratio = self._file.width/self._file.height
            image_ratio = self._image.image_ratio
            # Correct image aspect ratio for image rotation. i.e. aspect ratio
            # corresponds to the ratio after rotation.
            if abs(self._rotation) == 90 or abs(self._rotation == 270):
                image_ratio = 1/image_ratio

            # Determine required maximum dimension for the rotation
            # transformation based on aspect ratios.
            if widget_ratio > image_ratio and image_ratio > 1:
                max_dim = round(self.height*image_ratio)
            elif widget_ratio <= image_ratio and image_ratio >= 1:
                max_dim = self.width
            elif widget_ratio >= image_ratio and image_ratio <= 1:
                max_dim = self.height
            else:  # widget_ratio < image_ratio and image_ratio < 1
                max_dim = round(self.width/image_ratio)

            # Set size of image widget to square with maximum dimension
            self._image.size = (max_dim, max_dim)
            # Adjust position of image widget within slideshow image widget
            # to center rotated image.
            self._image.x = round(self.x + (self.width - max_dim)/2)
            self._image.y = round(self.y + (self.height - max_dim)/2)

            # Log debug information
#            Logger.debug(f"Image uuid: {self._file.uuid}")
#            Logger.debug(f"Image type: {self._file.type}")
#            Logger.debug(f"Image source: {self._file.source}")
#            Logger.debug(f"Image orientation: {self._file.orientation}")
#            Logger.debug(f"Image rotation: {self._file.rotation}")
#            Logger.debug(f"Total rotation: {self._rotation}")
#            Logger.debug(f"Widget width: {self.width}")
#            Logger.debug(f"Widget height: {self.height}")
#            Logger.debug(f"Widget aspect ratio: {widget_ratio}")
#            Logger.debug(f"max_dim: {max_dim}")
#            Logger.debug(f"Image width: {self._image.width}")
#            Logger.debug(f"Image height: {self._image.height}")
#            Logger.debug(f"Image aspect ratio: {image_ratio}")
#            Logger.debug(f"Image x: {self._image.x}")
#            Logger.debug(f"Image y: {self._image.y}")
#            Logger.debug(f"Image center: {self._image.center}")

            # Apply rotation.
            with self._image.canvas.before:
                PushMatrix()
                Rotate(angle=self._rotation, origin=self._image.center, axis=(0, 0, 1))
            with self._image.canvas.after:
                PopMatrix()
        # Set size of image widget to size of image slideshow widget (this
        # widget) otherwise and let image widget do the scaling.
        else:
            self._image.size = self.size


class InvalidSlideshowConfigurationError(Exception):
    """Invalid slideshow configuration error."""

    def __init__(self, msg, config=None):
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
                    self._criteria['order'] = ORDER_DATE_ASC
                elif value == "date" and config['order'] == "descending":
                    self._criteria['order'] = ORDER_DATE_DESC
                elif value == "name" and config['order'] == "ascending":
                    self._criteria['order'] = ORDER_NAME_ASC
                elif value == "name" and config['order'] == "descending":
                    self._criteria['order'] = ORDER_NAME_DESC
                else:
                    raise InvalidSlideshowConfigurationError(f"Incorrect sequence '{value}' specified.", config)

            # Limit iteration to the n most recent files based on the creation
            # date.
            if key == "mostRecent":
                if int(config['mostRecent']) > 0:
                    self._criteria['mostRecent'] = int(config['mostRecent'])
                else:
                    raise InvalidSlideshowConfigurationError(f"Invalid value '{value}' for mostRecent specified.", config)

            # Filter for orientation of content.
            if key == "orientation":
                if value == "landscape":
                    self._criteria['orientation'] = RepositoryFile.ORIENTATION_LANDSCAPE
                elif value == "portrait":
                    self._criteria['orientation'] = RepositoryFile.ORIENTATION_PORTRAIT
                else:
                    raise InvalidSlideshowConfigurationError(f"Invalid orientation '{value}' specified.", config)

            # Filter for file type.
            if key == "fileType":
                if value is None:
                    raise InvalidSlideshowConfigurationError(f"At least one file type has to be specified.", config)
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
                        raise InvalidSlideshowConfigurationError(f"Invalid type '{fileType}' specified.", config)
                self._criteria['type'] = types

            # Filter for file tags.
            if key == "tags":
                if value is None:
                    raise InvalidSlideshowConfigurationError(f"At least one tag has to be specified.", config)
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
            widget = SlideshowImage(file, **self._args)
        elif file.type == RepositoryFile.TYPE_VIDEO:
            widget = SlideshowVideo(file, **self._args)
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
