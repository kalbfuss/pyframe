"""Module providing metadata index class.

The following test script is based on the tutorial by Philipp Wagner [1]. The
script depends on the following debian packages:
- python3-sqlalchemy

References;
----------
1. https://bytefish.de/blog/first_steps_with_sqlalchemy/
"""

import logging

from repository import RepositoryFile, InvalidUuidError, Repository
from sqlalchemy import create_engine, desc, event, func, update, delete, or_, Column, DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, sessionmaker, scoped_session


# Install listener for connection events to automatically enable foreign key
# constraint checking by SQLite.
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraint checking by sqlite."""
#    logging.debug("Enable foreign key database constraints.")
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


Base = declarative_base()


class MetaData(Base):
    """Database model for file metadata.

    Database representation of file metadata using SQLAlchemy object relational
    mapper. Properties resemble properties of class repository.RepositoryFile.

    Properties:
        id(Integer): Numerical unique identifier. Automatically generated.
        rep_uuid(String(36)): Universally unique identifier of the repository
            containing the file.
        file_uuid(String(255)): Universally unique identifier of the file.
        type(Integer): Type of the file. See repository.RepositoryFile for
            acceptable values.
        width(Integer): Width of the file content in pixels.
        height(Integer): Height of the file content in pixels.
        rotation(Iteger): Clock-wise rotation of the content in degrees. See
            repository.RepositoryFile for acceptable values.
        orientation(Integer): Orientation of the content considering rotation.
            See repository.RepositoryFile for acceptable values.
        creation_date(DateTime): Creation date of the file content.
        last_modified(DateTime): Date of last file modification.
        last_updated(DateTime): Date of last metadata update.
        description(String(255)): Description of the file.
        rating(Integer): Rating of the file content.
        verified(Boolean): Verification flag set during index building. True if
            file exists. False if not yet verified or does not exist.
    """

    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    rep_uuid = Column(String(Repository.MAX_LEN_UUID), nullable=False)
    # File uuid needs to be unique within a repository, but not across repositories.
#    file_uuid = Column(String(255), unique=True, nullable=False)
    file_uuid = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    rotation = Column(Integer)
    orientation = Column(Integer)
    creation_date = Column(DateTime)
    description = Column(String(255))
    rating = Column(Integer)
    last_modified = Column(DateTime)
    last_updated = Column(DateTime)
    verified = Column(Boolean)
    tags = relationship("MetaDataTag", secondary="tag_file", backref=backref("files", lazy="dynamic"))


class MetaDataTag(Base):
    """Database model for tags in file metadata.

    Database representation of tags in file metadata using SQLAlchemy object
    relational mapper. Tags and metadata are connected via a separate table
    'tag_file' in the database.

    Properties:
        id(Integer): Numerical unique identifier. Automatically generated.
        name(String(255)): Unique name of the tag.
    """

    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)


class Link(Base):
    """Association table for file metadata and tags."""

    __tablename__ = "tag_file"
    tag_id = Column(Integer, ForeignKey('tags.id', ondelete="CASCADE"), primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id', ondelete="CASCADE"), primary_key=True)


class Index:
    """File metadata index.

    Enables quick lookup and filtering of files based on their metadata. Index
    may span multiple repositories. Files and repositories are referenced via
    there universal unique identifiers.

    Use method build() to build metadata index. Method build() may be run in
    the background from a different thread.
    """

    def __init__(self, dbname="index.sqlite"):
        """Initialize file index.

        :param dbname: Name of database. Default is "index.sqlite".
        :type dbname: str
        """
        self._dbname = dbname
        try:
            logging.info(f"Opening file index database '{dbname}'")
            # Determine whether we want verbose SQL debugging information.
            echo_flag = False
            if logging.getLogger("sqlalchemy").getEffectiveLevel() <= logging.DEBUG:
                echo_flag = True
            # Create sqlite database engine
            self._engine = create_engine(f"sqlite:///{dbname}", echo=echo_flag)
            # Create base class metadata
            Base.metadata.create_all(self._engine)
            # Open database session
            self._session_factory = sessionmaker(bind=self._engine)
            self._scoped_session = scoped_session(self._session_factory)
            self._session = self._scoped_session()
        except Exception as e:
            logging.critical(f"An error ocurred while opening the index database '{dbname}': {e}")

    def __del__(self):
        self.close()

    def build(self, rep, rebuild=False):
        """Build metadata index.

        Build method may be called from a different thread to build the index in
        the background. The method thus creates its own session and prevents
        files from looking up metadata from the index.

        :param rep: Repository for which to build the index.
        :type rep: repository.Repository
        :param rebuild: Indicates whether index is to be completely rebuilt.
            Default (False) is to update only, i.e. add the missing entries.
        :type rebuild: bool
        """
        # Create new session since build may be called from different thread.
        session = self._scoped_session()

        # Delete all metadata for the specified repository.
        if rebuild:
            logging.info(f"Rebuilding metadata index for repository '{rep.uuid}'.")
            try:
                logging.debug(f"Deleting all metadata entries of repository '{rep.uuid}'.")
                # Delete all file entries for the specified repository.
                session.query(MetaData).filter(MetaData.rep_uuid == rep.uuid).delete()
                session.commit()
                # Delete all unused tags.
                tags = session.query(MetaDataTag).all()
                for tag in tags:
                    if tag.files.count() == 0:
                        logging.info(f"Deleting unused tag '{tag.name}'.")
                        session.delete(tag)
                session.commit()
            except Exception as e:
                logging.error(f"An error occurred while deleting metadata of repository {rep.uuid} from index: {e}")
        # Mark existing metadata entries for verification.
        else:
            logging.info(f"Updating metadata index for repository '{rep.uuid}'.")
            try:
                logging.debug(f"Resetting verification flags for all metadata entries of repository '{rep.uuid}'.")
                query = update(MetaData).where(MetaData.rep_uuid == rep.uuid).values(verified=False)
                session.execute(query)
                session.commit()
            except Exception as e:
                logging.error(f"An error occurred while marking metadata entries of repository '{rep.uuid}' for verification: {e}")

        # Iterate through all files in the repository.
        for file in rep.iterator(index_lookup=False, extract_metadata=False):
            try:
                # Create new metadata entry for file if not included in the
                # index yet or outdated.
                mdata = session.query(MetaData).filter(MetaData.rep_uuid == rep.uuid).filter(MetaData.file_uuid == file.uuid).first()
                if mdata is None or mdata.last_updated < file.last_modified:
                    # Extract metadata from file.
                    file.extract_metadata()

                    # Create all necessary tags in database.
                    tags = list()
                    if file.tags:
                        for name in file.tags:
                            # Try to query tag from database.
                            tag = session.query(MetaDataTag).filter(MetaDataTag.name == name).first()
                            # Create and add tag to database otherwise.
                            if tag is None:
                                logging.info(f"Adding tag '{name}'.")
                                tag = MetaDataTag(name=name)
                            tags.append(tag)

                    # Create/update metadata entry with file metadata.
                    if mdata is None:
                        logging.info(f"Adding metadata of file '{file.uuid}' to index.")
                    else:
                        logging.info(f"Updating metadata of file '{file.uuid}' in index.")
                    mdata = MetaData(rep_uuid=file.rep.uuid, file_uuid=file.uuid, name=file.name, type=file.type, width=file.width, height=file.height, rotation=file.rotation,
                                     orientation=file.orientation, creation_date=file.creation_date,
                                     last_modified=file.last_modified,
                                     last_updated=file.last_updated, description=file.description, rating=file.rating,
                                     verified=True, tags=tags)
                    session.add(mdata)
                    # Commit all changes to the database.
                    session.commit()
                else:
                    logging.debug(f"Skipping file '{file.uuid} as already included in index.")
                    # Mark entry as verified.
                    query = update(MetaData).where(MetaData.rep_uuid == rep.uuid).where(MetaData.file_uuid == file.uuid).values(verified=True)
                    session.execute(query)
                    # Do not immediately commit update for performance reasons.
#                    session.commit()
            except Exception as e:
                logging.error(f"An error occurred while building the metadata index: {e}")

        # Delete entries which have not been successfulyy verified.
        query = delete(MetaData).where(MetaData.verified == False)
        session.execute(query)
        # Commit pending changes and close session
        session.commit()
        session.close()

    def close(self):
        try:
            logging.debug(f"Closing file index database '{self._dbname}'")
            # Close database session and dispose engine
            if self._session:
                self._session.close()
            if self._engine: self._engine.dispose()
        except Exception as e:
            logging.error(f"An error ocurred while closing the index database '{self._dbname}': {e}")

    def lookup(self, file, rep):
        """Lookup file metadata.

        :param file: File for which to lookup metadata.
        :type file: repository.Index
        :param rep: Repository containing the file.
        :type rep: repository.Repository
        :return: Returns a metadata object for the file if available. Returns
            None otherwise.
        :return type: repository.MetaData
        """
        try:
            mdata = self._session.query(MetaData).filter(MetaData.rep_uuid == rep.uuid).filter(MetaData.file_uuid == file.uuid).first()
            return mdata
        except Exception as e:
            logging.error(f"An error ocurred while looking up metadata from index for file '{file.uuid}' in repository '{rep.uuid}': {e}")
            return None

    def count(self):
        """Count the number of rows in the index.

        :return: Number of rows in the index.
        :return type: int
        """
        return self._session.query(MetaData).count()

    # Order type definitions
    ORDER_RANDOM = 0
    ORDER_DATE_ASC = 1
    ORDER_DATE_DESC = 2
    ORDER_NAME_ASC = 3
    ORDER_NAME_DESC = 4

    def iterator(self, **criteria):
        """Return selective iterator.

        Return selective iterator which allows to traverse through a
        sub-population of files in the index according to specified criteria.

        :param criteria: Selection criteria
        :type criteria: dict
        :return: Selective iterator
        :return type: repository.SelectiveIndexIterator
        """
        return SelectiveIndexIterator(self._session, **criteria)


class InvalidIterationCriteriaError(Exception):
    """Invalid index iteration criteria error."""

    def __init__(self, msg, criteria=None):
        """Initialize class instance."""
        super().__init__(msg)
        self.criteria = criteria


class SelectiveIndexIterator:
    """Selective index iterator.

    Selective iterator which allows to traverse through a sub-population of
    files in the index according to specified criteria.
    """

    def __init__(self, session, **criteria):
        """Initialize selective index iterator.

        :param session: SQLAlchemy database session
        :type session: sqlalchemy.orm.Session
        :param criteria: Dictionary containing iteration criteria
        :type criteria: dict
        :raises: InvalidIterationCriteriaError
        """
        # Initialize query.
        query = session.query(MetaData)

        # Make sure only valid parameters have been specified.
        valid_keys = {'excluded_tags', 'most_recent', 'order', 'orientation', 'repository', 'tags', 'type'}
        keys = set(criteria.keys())
        if not keys.issubset(valid_keys):
            raise InvalidIterationCriteriaError(f"Only the parameters {valid_keys} are accepted, but the additional parameter(s) {keys.difference(valid_keys)} has/have been specified.")

        # Helper function to raise error.
        def __raise():
            raise InvalidIterationCriteriaError(f"Invalid value '{value}' for parameter '{key}' specified.", criteria)

        # Extend query based on iteration criteria.
        for key, value in criteria.items():

            # Filter for repository by UUID
            if key == "repository":
                if type(value) is str:
                    query = query.filter(MetaData.rep_uuid == value)
                elif type(value) is list:
                    query = query.filter(MetaData.rep_uuid.in_(value))
                else:
                    __raise()

            # Filter for file type.
            elif key == "type":
                if type(value) is int:
                    query = query.filter(MetaData.type == value)
                elif type(value) is list:
                    query = query.filter(MetaData.type.in_(value))
                else:
                    __raise()

            # Filter for orientation of content.
            elif key == "orientation":
                if value in [RepositoryFile.ORIENTATION_LANDSCAPE, RepositoryFile.ORIENTATION_PORTRAIT]:
                    query = query.filter(MetaData.orientation == value)
                else:
                    __raise()

            # Limit iteration to files with specified tags.
            elif key == "tags":
                query = query.filter(MetaData.tags.any(func.lower(MetaDataTag.name).in_([tag.lower() for tag in value])))

            # Exclude files with excluded tags from iteration.
            elif key == "excluded_tags":
                query = query.filter(or_(~MetaData.tags.any(func.lower(MetaDataTag.name).in_([tag.lower() for tag in value])), MetaData.tags == None))

        # Determine limiting date to limit iteration to the n most recent files
        # based on the creation date. Outside of the loop since query needs to
        # be executed after all filters, but prior to specifying any order
        # (see below).
        if 'most_recent' in criteria:
            value = criteria['most_recent']
            if type(value) is int and value > 0:
                # Sort relevant entries by creation date in descending order and
                # limit to n most recent entries. Save the creation date of the
                # last result to obtain the creation date limit.
                date_limit = query.order_by(desc(MetaData.creation_date)).limit(value).all()[-1].creation_date
            else:
                __raise()

        # Retrieve files in a specific or random order.
        if 'order' in criteria:
            value = criteria['order']
            if value == Index.ORDER_RANDOM:
                query = query.order_by(func.random())
            elif value == Index.ORDER_DATE_ASC:
                query = query.order_by(MetaData.creation_date)
            elif value == Index.ORDER_DATE_DESC:
                query = query.order_by(desc(MetaData.creation_date))
            elif value == Index.ORDER_NAME_ASC:
                query = query.order_by(func.upper(MetaData.name))
            elif value == Index.ORDER_NAME_DESC:
                query = query.order_by(desc(func.upper(MetaData.name)))
            else:
                __raise()

        # Limit iteration to the n most recent files based on the creation
        # date. An additional limit is specified since in theory multiple images
        # may have the very same creation date. Processed last since limit must
        # be applied at the very end of the query.
        if 'most_recent' in criteria:
            value = criteria['most_recent']
            query = query.filter(MetaData.creation_date >= date_limit).limit(value)

        # Query data and save iterator for list with metadata objects.
        self._count = query.count()
        self._iterator = query.all().__iter__()

    def __iter__(self):
        """Return self as iterator.

        :return: Self
        :return type: repository.SelectiveIndexIterator
        """
        return self

    def __next__(self):
        """Return next file in iteration.

        :return: Next file in iteration
        :return type: repository.RepositoryFile
        :raises: StopIteration
        """
        # Repeat until we have a valid file or end of iteration is reached. Note
        # that StopIteration is not raised explicitly, but raised implicitly as
        # the end of the list with metadata objects is reached.
        while True:
            # Retrieve next metadata object in iteration.
            mdata = self._iterator.__next__()
            self._count = self._count - 1
            # Try to obtain corresponding file.
            try:
                return Repository.by_uuid(mdata.rep_uuid).file_by_uuid(mdata.file_uuid)
            except InvalidUuidError:
                pass

    def count(self):
        """Return number of remaining elments in iteration."""
        return self._count
