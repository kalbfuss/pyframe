"""Collection of classes to generate slideshows.

Provides :class:`slideshow.Slideshow` to generate slideshows of supported
content. Rendering of the following content is currently supported:

* Images via :class:`slideshow.SlideshowImage`
* Videso via :class:`slideshow.SlideshowVideo`

Author: Bernd Kalbfuß
License: t.b.d.
"""


from . mylogging import Handler
from . content import Content
from . video import SlideshowVideo
from . image import SlideshowImage
from . indexer import Indexer
from . scheduler import Scheduler
from . slideshow import Slideshow, InvalidSlideshowConfigurationError
from . controller import Controller
from . mqtt import MqttInterface
from . app import App
