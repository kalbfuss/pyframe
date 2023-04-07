"""Module for local repository files."""

import logging
import os
import os.path
import repository

from repository import UuidError
from datetime import datetime


class RepositoryFile(repository.RepositoryFile):
    """File within a local repository.

    For images the following properties are read out from EXIF tag if available:
    width, height, rotation, creation_date, description, rating, tags.

    See repository.File for documentation of properties.
    """

    def __init__(self, uuid, rep, index=None, index_lookup=True, extract_metadata=True):
        """Initialize file."""
        super().__init__(uuid, rep, index, index_lookup)

        # Throw exception if file does not exist
        self._path = os.path.join(rep.root, uuid)
        if not os.path.isfile(self._path):
            raise UuidError("There is no file with UUID '{uuid}'.", uuid)

        # Set file name from uuid
        self._name = os.path.basename(uuid)

        # Determine last modification and file creation date.
        last_modified = datetime.fromtimestamp(os.path.getmtime(self._path))
        if not self._in_index or self.last_updated < last_modified:
            self._last_modified = last_modified
            self._creation_date = datetime.fromtimestamp(os.path.getctime(self._path))

        # Attempt to extract metadata from file content.
        if (not self._in_index or self.last_updated < last_modified) and extract_metadata:
            self.extract_metadata()

    def __enter__(self):
        """Return file-like object for access to file content.

        Note that this function is not thread-safe. Function __exit__ must be
        called prior to calling __enter__ again.

        :return: File-like object providing access to file content.
        :rtype: file
        """
        self._file = open(self._path, "rb")
        return self._file

    def __exit__(self, type, value, traceback):
        """Close file-like object previously returned."""
        self._file.close()

    def extract_metadata(self):
        """Extract metadata from file content."""
        logging.debug(f"Extracting metadata of file '{self.uuid}' from file content.")
        # If image try to extract metadata from EXIF tag.
        if self._type == repository.RepositoryFile.TYPE_IMAGE:
            self._extract_image_metadata(self._path)
        elif self._type == repository.RepositoryFile.TYPE_VIDEO:
            self._extract_video_metadata(self._path)

    @property
    def source(self):
        """Return the full path of the file.

        :return: Full path of file.
        :rtype: str
        """
        return self._path
