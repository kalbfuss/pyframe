""""...


The following test script is based on instructions provided as part of the
project description [1]. An overview of common EXIF tags is provided in [2].

Dependencies;
-------------
- boost (indirectly via py3exiv2)
- ffmpeg-python
- webdavclient3

Requires the following ubuntu/debian packages libexiv2, libexiv2-dev,
libboost-all-dev

References;
----------
1. https://py3exiv2.tuxfamily.org/
2. https://www.exiv2.org/tags.html
3. https://github.com/kkroening/ffmpeg-python
4. https://pypi.org/project/webdavclient3/
"""

import logging
import os
import os.path
import repository
import tempfile

from datetime import datetime
from repository import IoError, UuidError


class RepositoryFile(repository.RepositoryFile):
    """File within a webdav repository."""

    def __init__(self, uuid, rep, index=None, index_lookup=True, extract_metadata=True):
        """Initialize file."""
        # Call constructor of parent class.
        super().__init__(uuid, rep, index, index_lookup)

        # Basic initialization.
        self._cache_file = None
        self._path = None

        # Set file name from uuid
        self._name = os.path.basename(uuid)

        # Attempt to determine last modification and file creation date.
        if not self._in_index:
            try:
                info = self._rep.client.info(self.uuid)
            except Exception as e:
                raise IoError(f"An exception occurred while retrieving webdav file information: {e}", e.exception)
            logging.debug(f"Webdav info record of file '{self.uuid}': {info}")
            try:
                modified = info.get('modified', None)
                if modified is not None:
                    self._last_modified = datetime.strptime(modified, "%a, %d %b %Y %H:%M:%S %Z")
            except (ValueError, TypeError):
                logging.warn(f"Failed to convert last modified date string '{modified}' to datetime. Using current datetime instead.")
                self._last_modified = datetime.now()
            try:
                created = info.get('created', None)
                if created is not None:
                    self._creation_date = datetime.strptime(created, "%a, %d %b %Y %H:%M:%S %Z")
            except (ValueError, TypeError):
                logging.warn(f"Failed to convert created date string '{created}' to datetime. Using current datetime instead.")
                self._last_modified = datetime.now()

        # Attempt to extract metadata from file content.
        if not self._in_index and extract_metadata:
            self.extract_metadata()

    def __del__(self):
        """Delete the file."""
        # Close and delete cache file if exists to prevent clean up errors.
        if self._cache_file is not None:
            try:
                self._cache_file.close()
            except FileNotFoundError:
                # Ignore any file not found errors, which can occur if the
                # cache directory and its content are deleted before the
                # temporary file.
                pass

    def _download(self):
        """Download file from WebDav repository to local cache file.

        :raises: IoError
        """
        if self._cache_file is None:
            # Create temporary file for local caching inside cache directory
            # of the WebDav repository.
            self._cache_file = tempfile.NamedTemporaryFile(dir=self._rep.cache_dir)
            self._path = self._cache_file.name
            logging.debug(f"Local cache file '{self._path}' created.")

            # Download file from WebDav repository.
            logging.info(f"Downloading file '{self.uuid}' from webdav repository to local cache file.")
            try:
                self._rep.client.download_from(self._cache_file, self._uuid)
            except Exception as e:
                raise repository.IoError("An exception occurred while downloading file from webdav repository:", e)

    def extract_metadata(self):
        """Extract metadata from file content."""
        # Download file if file type is supported.
        if self.type in (repository.RepositoryFile.TYPE_IMAGE, repository.RepositoryFile.TYPE_VIDEO):
            self._download()
        # Attempt to extract metadata from file content.
        logging.debug(f"Extracting metadata of file '{self.uuid}' from file content.")
        if self._type == repository.RepositoryFile.TYPE_IMAGE:
            self._extract_image_metadata(self._path)
        elif self._type == repository.RepositoryFile.TYPE_VIDEO:
            self._download()
            self._extract_video_metadata(self._path)

    @property
    def source(self):
        """Return the full path of the local cache file.

        : return: Full path of local cache file.
        : rtype: str
        """
        # Make sure to download file before returning path.
        self._download()
        # Return full path to local cache file.
        return self._path
