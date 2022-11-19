"""..."""

import exifread
import ffmpeg
import fnmatch
import logging


from datetime import datetime
from iptcinfo3 import IPTCInfo


class RepositoryFile:
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

        Uses the exifread library to extract EXIF meta data and IPTCInfo3
        library to extract IPTC meta data from the image file. Meta data is
        stored in the corresponding object properties.

        Note the star rating tag is not yet supported by exifread and therefore
        always remains at the default.
        """

        # Open image file for reading (binary mode)
        file = open(path, 'rb')
        # Return Exif tags
        tags = exifread.process_file(file)

        # Obtain width from meta data if available
        if "EXIF ExifImageWidth" in tags:
            self._width = tags["EXIF ExifImageWidth"].values[0]

        # Obtain height from meta data if available
        if "EXIF ExifImageLength" in tags:
            self._height = tags["EXIF ExifImageLength"].values[0]

        # Obtain rotation from meta data if available
        if "Image Orientation" in tags:
            orientation = tags["Image Orientation"].values[0]
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

        # Etract image description if available
        if "Image ImageDescription" in tags:
            self._description = tags["Image ImageDescription"].values

        # Extract creation date if available
        if "EXIF DateTimeOriginal" in tags:
            try:
                creation_date = tags["EXIF DateTimeOriginal"].values
                self._creation_date = datetime.strptime(creation_date, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                logging.error(f"Invalid creation time format {creation_date}")

        # Extract rating if available
        # Tag is currently not supported by exifread
#        if "Image Rating" in data.exif_keys:
#            self._rating = data["Image Rating"].value

        # Extract image tags(keywords) from IPTC tag if available
        info = IPTCInfo(path)
        self._tags = info["keywords"]

    def _extract_video_meta_data(self, path):
        """Extract video meta data from file content.

        Uses the ffmpeg ffprobe command to extract video meta data from the
        video file and stores meta data in corresponding object properties.
        """
        data = ffmpeg.probe(path)['streams'][0]
        logging.debug(data)

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
        creation_date = data['tags'].get('creation_time')
        if creation_date is not None:
            try:
                self._creation_date = datetime.strptime(creation_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                logging.error(f"Invalid creation time format {creation_date}")

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
                return
        for pattern in RepositoryFile.EXT_VIDEO:
            if fnmatch.fnmatch(fname, pattern.upper()):
                self._type = RepositoryFile.TYPE_VIDEO
                return

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
