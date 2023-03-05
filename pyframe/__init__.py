"""Collection of classes to generate slideshows.

Provides :class:`slideshow.Slideshow` to generate slideshows of supported
content. Rendering of the following content is currently supported:

* Images via :class:`slideshow.SlideshowImage`
* Videso via :class:`slideshow.SlideshowVideo`

Author: Bernd Kalbfuß
License: t.b.d.
"""

from . logging import LogHandler
from . image import SlideshowImage
from . video import SlideshowVideo
from . indexer import Indexer
from . slideshow import Slideshow, InvalidSlideshowConfigurationError
from . scheduler import Scheduler
from . app import App
