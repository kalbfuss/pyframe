""""Module for rclone repository files."""

import logging
import os
import os.path
import repository
import tempfile

from datetime import datetime
from rclone_python import rclone
from repository import IoError, UuidError


class RepositoryFile(repository.RepositoryFile):
    """File within an rclone repository."""

    def __init__(self, uuid, rep, index=None, index_lookup=True, extract_metadata=True, info=None):
        """Initialize file."""
        # Call constructor of parent class.
        super().__init__(uuid, rep, index, index_lookup)

        # Basic initialization.
        self._cache_file = None
        self._path = None

        # Set file name from uuid
        self._name = os.path.basename(uuid)

        # Attempt to determine last modification date.
        if not self._in_index and info is not None:
            try:
                info = rclone.ls(f'"{os.path.join(rep.root, uuid)}"', max_depth=1)[0]
            except Exception as e:
                raise IoError(f"An exception occurred while scanning the rclone root directory. {e}", e)
            try:
                modified = info.get('ModTime', None)
                if modified is not None:
                    self._last_modified = datetime.strptime(modified, "%a, %d %b %Y %H:%M:%S %Z")
            except (ValueError, TypeError):
                logging.warn(f"Failed to convert last modified date string '{modified}' to datetime. Using current datetime instead.")

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
            logging.info(f"Downloading file '{self.uuid}' from rclone repository to local cache file.")
            try:
                rclone.copy(f'"{os.path.join(self._rep.root, self._uuid)}"', f'"{self._path}"')
            except Exception as e:
                raise repository.IoError(f"An exception occurred while downloading file from rclone repository. {e}", e)

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
