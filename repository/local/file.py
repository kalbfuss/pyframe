"""Module for local repository files."""

import logging
import os
import os.path
import repository

from repository import InvalidUuidError
from datetime import datetime


class RepositoryFile(repository.RepositoryFile):
    """File within a local repository.

    For images the following properties are read out from EXIF tag if available:
    width, height, rotation, creation_date, description, rating, tags.

    See repository.File for documentation of properties.
    """

    def __init__(self, uuid, rep, index=None):
        """Initialize file."""
        repository.RepositoryFile.__init__(self, uuid, rep, index)

        # Throw exception if file does not exist
        self._path = os.path.join(rep.root, uuid)
        if not os.path.isfile(self._path):
            raise InvalidUuidError("There is no file with UUID '{uuid}'.", uuid)

        # Determine file creation and last modification date
        last_modified = datetime.fromtimestamp(os.path.getmtime(self._path))

        # Attempt to extract meta data from file content.
        if not self._in_index or self.last_updated < last_modified:
            # Determine file creation and last modification date
            self._last_modified = last_modified
            self._creation_date = datetime.fromtimestamp(os.path.getctime(self._path))

            logging.info(f"Extracting meta data of file '{self.uuid}' from file content.")
            # If image try to extract meta data from EXIF tag.
            if self._type == repository.RepositoryFile.TYPE_IMAGE:
                self._extract_image_meta_data(self._path)
            elif self._type == repository.RepositoryFile.TYPE_VIDEO:
                self._extract_video_meta_data(self._path)

    def __enter__(self):
        """Return file-like object for access to file content.

        Note that this function is not thread-safe. Function __exit__ must be
        called prior to calling __enter__ again.

        :return: File-like object providing access to file content.
        :rtype: file
        """
        self._file = open(self._path, "r")
        return self._file

    def __exit__(self, type, value, traceback):
        """Close file-like object previously returned."""
        self._file.close()

    @property
    def source(self):
        """Return the full path of the file.

        :return: Full path of file.
        :rtype: str
        """
        return self._path
