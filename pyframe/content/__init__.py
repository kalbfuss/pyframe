"""Collection of classes to display content in slideshows.

Rendering of the following content is currently supported:

* Images via :class:`pyframe.content.SlideshowImage`
* Videos via :class:`pyframe.content.SlideshowVideo`
* Error messages via :class:`pyframe.content.ErrorMessage

Author: Bernd Kalbfuß
License: t.b.d.
"""

from . base import ContentBase
from . image import SlideshowImage
from . video import SlideshowVideo
