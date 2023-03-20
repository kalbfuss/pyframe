"""Module providing slideshow content base class."""

from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from datetime import datetime
from math import ceil


class Content(Widget):
    """Slideshow content widget.

    Base class for slideshow image and video widgets. Provides basic
    functionality for labeling.
    """

    def __init__(self, file, config):
        """Initialize the slideshow content instance."""
        super().__init__()
        self._file = file
        self._config =  config

        # Create and add white (foreground) and black (shadow) labels.
        self._wlabel = Label(markup=True, halign="right", valign="bottom", color=(1, 1, 1, 1), font_blended=True)
        self._blabel = Label(markup=True, halign="right", valign="bottom", color=(0, 0, 0, 1))
        self.add_widget(self._blabel)
        self.add_widget(self._wlabel)
        # Set the label text.
        mode = config.get('label_mode', "off")
        if mode is True or mode == "on" or mode == "auto":
            label = self.label
            self._wlabel.text = label
            self._blabel.text = label
        # Call _adjust_label method after the widget's size has been set.
        self.bind(size=self._adjust_label)

    def _label_off(self, dt):
        "Turn label off."
        self._wlabel.text = ""
        self._blabel.text = ""

    def _label_on(self, dt):
        "Turn label on."
        self._wlabel.text = self.label
        self._blabel.text = self.label

    @property
    def file(self):
        """Return linked repository file.

        :return: linked repository file
        :rtype: repository.file
        """
        return self._file

    @property
    def config(self):
        """Return content configuration.

        :return: configuration passed to the constructor
        :rtype: dict
        """
        return self._config

    @property
    def label(self):
        """Return label text.

        The label text is built from properties and meta data of the linked
        file. Text creation can be controlled via the configuration.

        :return: label text
        :rtype: str
        """
        label = str()
        label_content = self.config.get('label_content', "short")
        # Add description and separate if available.
        description = self.file.description
        if description:
            label= f"[b]{description}[/b] · "
        # Return if only description requested.
        if label_content == "description": return
        # Format and append creation date.
        date_str = self.file.creation_date.strftime("%Y-%m-%d %H:%M:%S")
        label = label + f"{date_str}"
        # Return if only short label requested.
        if label_content == "short": return label
        # Format and append tags if any.
        if self.file.tags:
            tag_str = str()
            for tag in self.file.tags:
                tag_str = tag_str + f" #{tag}"
            label = label + f" · [i]{tag_str}[/i]"
        # Append file and repository uuid.
        label = label + f" · {self.file.uuid} [i]in[/i] {self.file.rep.uuid}"
        return label

    def _adjust_label(self, *args):
        """Adjust label when the widget becomes visible and its size is set."""
        # Set font size.
        font_size = round(self.config.get('label_font_size', 0.05) * self.height)
        self._wlabel.font_size = font_size
        self._blabel.font_size = font_size
        # Set padding.
        padding = round(self.config.get('label_padding', 0.05) * self.width)
        self._wlabel.padding = (padding, padding)
        self._blabel.padding = (padding, padding)
        # Resize labels.
        offset = ceil(0.03*font_size)
        self._wlabel.pos = (self.x, self.y + offset)
        self._wlabel.size = (self.width - offset, self.height)
        self._wlabel.text_size = self._wlabel.size
        self._blabel.pos = (self.x + offset, self.y)
        self._blabel.size = (self.width - offset, self.height - offset)
        self._blabel.text_size = self._blabel.size
        # Schedule events to turn labels off and on.
        mode = self.config.get('label_mode', "on")
        pause = self.config.get('pause')
        duration = self.config.get('label_duration', 24)
        if mode == "auto" and pause is not None and duration < pause:
            Clock.schedule_once(self._label_off, duration/2)
            Clock.schedule_once(self._label_on, pause - duration/2)
