""""...


The following test script is based on instructions provided as part of the
project description [1]. An overview of common EXIF tags is provided in [2].

Dependencies;
-------------
- py3exiv2
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
import os.path
import repository
import tempfile

from datetime import datetime


class RepositoryFile(repository.RepositoryFile):
    """File within a webdav repository."""

    # Extensions of supported files
    EXT_IMAGE = ("*.jpg", "*.jpeg", "*.png")
    EXT_VIDEO = ("*.mp4", "*.mv4")

    def __init__(self, uuid, rep, index=None):
        """Initialize file."""
        # Call constructor of parent class.
        repository.RepositoryFile.__init__(self, uuid, rep, index)

        # Basic initialization.
        self._cache_file = None
        self._path = None

        # Attempt to extract meta data from file content.
        if not self._in_index:
            logging.info(f"Extracting meta data of file '{self.uuid}' from file content.")
            # If image try to extract meta data from EXIF tag.
            if self._type == repository.RepositoryFile.TYPE_IMAGE:
                self._download()
                self._extract_image_meta_data(self._path)
            elif self._type == repository.RepositoryFile.TYPE_VIDEO:
                self._download()
                self._extract_video_meta_data(self._path)

    def _download(self):
        """Download file from WebDav repository to local cache file."""
        if self._cache_file is None:
            # Create temporary file for local caching inside cache directory
            # of the WebDav repository.
            self._cache_file = tempfile.NamedTemporaryFile(dir=self._rep.cache_dir)
            self._path = self._cache_file.name
            logging.info(f"Local cache file '{self._path}' created.")

            # Download file from WebDav repository.
            logging.info(f"Downloading file '{self.uuid}' from webdav repository.")
            self._rep.client.download_from(self._cache_file, self._uuid)

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
