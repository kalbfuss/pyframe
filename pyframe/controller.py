"""Module providing Pyframe controller."""

from abc import ABC, abstractmethod


class Controller(ABC):
    """Pyframe controller.

    Provides interface for control of the photo frame.
    """

    @abstractmethod
    def play(self):
        """Start playing the current slideshow."""
        pass

    @abstractmethod
    def pause(self):
        """Pause playing the current slideshow."""
        pass

    @abstractmethod
    def stop(self):
        """Stop playing the current slideshow."""
        pass

    @abstractmethod
    def previous(self):
        """Change to previous file in slideshow."""
        pass

    @abstractmethod
    def next(self):
        """Change to next file in slideshow."""
        pass

    @abstractmethod
    def touch(self):
        """Touch to prevent screen timeout."""
        pass
