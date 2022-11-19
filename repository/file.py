"""..."""

import ffmpeg
import fnmatch
import logging
import pyexiv2

from abc import ABC, abstractmethod
from datetime import datetime


class InvalidFileError(Exception):
    """Invalid file error."""

    def __init__(self, msg, uuid=None):
        super().__init__(msg)
        self.file = file


class RepositoryFile(ABC):
    """File within a repository.

    Abstract base class providing basic functionality common to all File
    subclasses.

    Properties:
        uuid (str): Universally unique identifier (UUID) of the file. Typically
            the full path of the file within the repository.
        rep (repository.Repository): Repository containing the file.
        name (str): Name of the file. Default is None.
        index (repository.Index): Optional file meta data index. Default is
            None.
        type (int): Type of the file. Default is None. If set the following
            values may be returend:
            TYPE_UNKNOWN: Unknown file type
            TYPE_IMAGE: Image file
            TYPE_VIDEO: Video file
        width (int): Width of the file content in pixels. Default is None.
        height (int): Height of the file content in pixels. Default is None.
        rotation (int): Clock-wise rotation of the content in degrees. Default
            is None. If set the following values may be returned: 0, 90, 180
            or 270.
        orientation (int): Orientation of the content considering rotation.
            Default is None. If set the following values may be returned:
            ORIENTATION_LANDSCAPE: Content wider than high (default)
            ORIENTATION_PORTRAIT: Content heigher than wide
        creation_date (DateTime): Creation date of file content. Default is
            None.
        description (str): Description of the file content. Default is None.
        rating (int): Rating of the file content. Default is None.
        source (str): Source of the file (e.g. full path or URL).
        tags (set of str): User defined tags on the file. Not to be confounded
            with EXIF tags in image files. Default is None.
    """

    # File type definitions
    TYPE_UNKNOWN = 0
    TYPE_IMAGE = 1
    TYPE_VIDEO = 2

    # Orientation definitions
    ORIENTATION_LANDSCAPE = 0
    ORIENTATION_PORTRAIT = 1

    def __init__(self, uuid, rep, index=None):
        """Initialize file instance.

        :param uuid: UUID of the file.
        :type uuid: str
        :param rep: Repository containing file
        :type rep: repository.Repository
        :param index: Optional file meta data index. Default is None.
        :type index: repository.Index
        """
        # Basic initialization.
        self._in_index = False
        self._uuid = uuid
        self._rep = rep
        self._index = index
        self._type = RepositoryFile.TYPE_UNKNOWN
        self._name = str()
        self._width = 0
        self._height = 0
        self._rotation = 0
        self._orientation = RepositoryFile.ORIENTATION_LANDSCAPE
        self._creation_date = datetime.today()
        self._description = str()
        self._rating = 0
        self._tags = list()

        # Attempt to determine type from extension.
        self._type_from_extension()

        # Try to retrieve meta data from index if available.
        mdata = None
        if index is not None:
            mdata = index.lookup(self, rep)

        if mdata is not None:
            logging.info(f"Assigning meta data of file '{self._uuid}' from index.")
            self._in_index = True
            self._type = mdata.type
            self._width = mdata.width
            self._height = mdata.height
            self._rotation = mdata.rotation
            self._orientation = mdata.orientation
            self._creation_date = mdata.creation_date
            self._description = mdata.description
            self._rating = mdata.rating
            self._tags = [tag.name for tag in mdata.tags]

    def __repr__(self):
        """Provide string representation of file instance.

        :return: String representation
        :rtype: str
        """
        return f"File=(uuid='{self.uuid}', rep=0x{id(self.rep):x}, name={self.name}, type={self.type}, width={self.width}, height={self.height}, rotation={self.rotation}, orientation={self.orientation}, creation_date='{self.creation_date}', description='{self.description}', rating={self.rating}, tags={self.tags})"

    # Extensions of supported files
    EXT_IMAGE = ("*.jpg", "*.jpeg", "*.png")
    EXT_VIDEO = ("*.mp4", "*.mv4")

    def _extract_image_meta_data(self, path):
        """Extract image meta data from file content.

        Uses the pyexiv2 library to extract image meta data from the image
        file and stores meta data in corresponding object properties.
        """
        # Extract all meta data from image file
        data = pyexiv2.metadata.ImageMetadata(path)
        data.read()

        # Try to obtain image dimensions from meta data
        self._width = data.dimensions[0]
        self._height = data.dimensions[1]

        # Try to obtain rotation from meta data
        orientation = data.get_orientation()
        if orientation == 8:
            self._rotation = 90
        elif orientation == 3:
            self._rotation = 180
        elif orientation == 6:
            self._rotation = 270

        # Derive orientation from dimensions and rotation.
        if (self._width < self._height and (self.rotation == 0 or self.rotation == 180)) or (self._width > self._height and (self.rotation == 90 or self.rotation == 270)):
            self._orientation = RepositoryFile.ORIENTATION_PORTRAIT
        else:
            self._orientation = RepositoryFile.ORIENTATION_LANDSCAPE

        # Try to obtain image comment from meta data
        self._description = data.comment
        # Or from image description EXIF tag if availabe
        if self._description == "" and "Exif.Image.ImageDescription" in data.exif_keys:
            self._description = data["Exif.Image.ImageDescription"].value

        # Extract creation date from EXIF tag if available
        if "Exif.Photo.DateTimeOriginal" in data.exif_keys:
            self._creation_date = data["Exif.Photo.DateTimeOriginal"].value

        # Extract rating from EXIF tag if available
        if "Exif.Image.Rating" in data.exif_keys:
            self._rating = data["Exif.Image.Rating"].value

        # Extract image tags (keywords) from IPTC tag if available
        if "Iptc.Application2.Keywords" in data.iptc_keys:
            self._tags = data["Iptc.Application2.Keywords"].value

    def _extract_video_meta_data(self, path):
        """Extract video meta data from file content.

        Uses the ffmpeg ffprobe command to extract video meta data from the
        video file and stores meta data in corresponding object properties.
        """
        data = ffmpeg.probe(path)['streams'][0]
        logging.info(data)

        # Try to obtain image dimensions from meta data.
        if data.get('width') != None:
            self._width = int(data.get('width'))
        if data.get('height') != None:
            self._height = int(data.get('height'))

        # Try to obtain rotation from meta data.
        rotate = data['tags'].get('rotate')
        if rotate != None:
            if rotate == "0":
                self._rotation = 0
            elif rotate == "90":
                self._rotation = 270
            elif rotate == "180":
                self._rotation == 180
            elif rotate == "270":
                self._rotation = 90

        # Derive orientation from dimensions and rotation.
        if (self._width < self._height and (self.rotation == 0 or self.rotation == 180)) or (self._width > self._height and (self.rotation == 90 or self.rotation == 270)):
            self._orientation = RepositoryFile.ORIENTATION_PORTRAIT
        else:
            self._orientation = RepositoryFile.ORIENTATION_LANDSCAPE

        # Try to extract creation time from meta data.
        creation_time = data['tags'].get('creation_time')
        if creation_time is not None:
            try:
                self._creation_date = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                logging.info(f"Invalid creation time format {creation_time}")

        # Log debug information
#        logging.debug(f"\twidth: {self._width}")
#        logging.debug(f"\theight: {self._height}")
#        logging.debug(f"\torientation: {self._orientation}")
#        logging.debug(f"\trotation: {self._rotation}")
#        logging.debug(f"\tcreation_date: {self._creation_date}")

    def _type_from_extension(self):
        """Determine file type based on file extension."""
        fname = self._uuid.upper()
        for pattern in RepositoryFile.EXT_IMAGE:
            if fnmatch.fnmatch(fname, pattern.upper()):
                self._type = RepositoryFile.TYPE_IMAGE
        for pattern in RepositoryFile.EXT_VIDEO:
            if fnmatch.fnmatch(fname, pattern.upper()):
                self._type = RepositoryFile.TYPE_VIDEO

    @property
    def uuid(self):
        """Return UUID of the file.

        :return: Universally unique identifier (UUID) of the file. Typically
            the full path of the file within the repository.
        :rtype: str
        """
        return self._uuid

    @property
    def rep(self):
        """Return repository containing the file.

        :return: Repository containing the file.
        :rtype: repository.Repository
        """
        return self._rep

    @property
    def name(self):
        """Return name of the file.

        :return: Name of the file.
        :rtype: str
        """
        return self._name

    @property
    def source(self):
        """Return the source of the file (e.g. full path or URL).

        :return: Source of the file.
        :rtype: str
        """
        return None

    @property
    def type(self):
        """Return type of the file.

        :return: Type of the file. The following values may be returend:
            TYPE_UNKNOWN: Unknown file type
            TYPE_IMAGE: Image file
            TYPE_VIDEO: Video file
        :rtype: int
        """
        return self._type

    @property
    def width(self):
        """Return width of the file content.

        :return: Width of the file content in pixels.
        :rtype: int
        """
        return self._width

    @property
    def height(self):
        """Return height of the file content.

        :return: Height of file content in pixels.
        :rtype: int
        """
        return self._height

    @property
    def rotation(self):
        """Return rotation of the file content.

        :return: Clock-wise rotation of the content in degrees. Typical
            values are 0, 90, 180 and 270.
        :rtype: int
        """
        return self._rotation

    @property
    def orientation(self):
        """Return orientation of the file content.

        :return: Orientation of the content considering rotation. The
            following values may be returned:
            ORIENTATION_LANDSCAPE: Content wider than high (default)
            ORIENTATION_PORTRAIT: Content heigher than wide.
        :rtype: int
        """
        return self._orientation

    @property
    def creation_date(self):
        """Return creation date of the file content.

        :return: Creation date of the file content. Note that this is not
            necessarily the creation date of the file.
        :rtype: DateTime
        """
        return self._creation_date

    @property
    def description(self):
        """Return description of the file content.

        :return: Description of the file content.
        :rtype: str
        """
        return self._description

    @property
    def rating(self):
        """Return rating of the file content.

        :return: Rating of the file content. Typically a star rating with values
            from 1 to 5.
        :rtype: int
        """
        return self._rating

    @property
    def tags(self):
        """Return tags on the file.

        :return: Tags on the file.
        :rtype: set of str
        """
        return self._tags
