"""Collection of classes to generate slideshows.

Provides :class:`slideshow.Slideshow` to generate slideshows of supported
content. Rendering of the following content is currently supported:

* Images via :class:`slideshow.SlideshowImage`
* Videso via :class:`slideshow.SlideshowVideo`

Author: Bernd Kalbfuß
License: t.b.d.
"""

from . video import SlideshowVideo
from . image import SlideshowImage
from . slideshow import Slideshow, InvalidSlideshowConfigurationError
from . scheduler import Scheduler
