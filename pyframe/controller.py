"""Module providing Pyframe controller interface."""

from abc import ABC, abstractmethod


class Controller(ABC):
    """Pyframe controller.

    Provides interface for the control of photo frames. The class is abstract
    and needs to be implemented by the inheriting class.
    """

    @property
    @abstractmethod
    def display_mode(self):
        """Return the display mode.

        :return: display mode
        :rtype: str
        """
        pass

    @display_mode.setter
    @abstractmethod
    def display_mode(self, mode):
        """Set the display mode.

        :param mode: display mode
        :type mode: str
        """
        pass

    @abstractmethod
    def next(self):
        """Change to next file in slideshow."""
        pass

    @abstractmethod
    def pause(self):
        """Pause playing the current slideshow."""
        pass

    @abstractmethod
    def play(self):
        """Start playing the current slideshow."""
        pass

    @abstractmethod
    def previous(self):
        """Change to previous file in slideshow."""
        pass

    @abstractmethod
    def stop(self):
        """Stop playing the current slideshow."""
        pass


    @abstractmethod
    def touch(self):
        """Touch to prevent screen timeout."""
        pass