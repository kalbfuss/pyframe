"""Collection of classes to access and index file repositories.

Provides interface definitions for classes :class:`repository.Repository` and :class:`repository.File`. Actual implementations are provided by sub-packages.

The following implementations, i.e. sub-packages, are currently available:
    - local: Files are stored on a local file system.
    - webdav: Files are stored on a WebDAV accessible share.

The :class:`repository.Index` class provides functionality to index file meta
data for the purpose of caching, filtering and sorting.

Author: Bernd Kalbfuß
License: t.b.d.
"""

from . file import RepositoryFile
from . repository import Repository, FileIterator, InvalidUuidError, InvalidConfigurationError
from . index import Index, MetaData
