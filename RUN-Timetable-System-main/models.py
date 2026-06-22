from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base

# This is the base class for our database tables
Base = declarative_base()

class Course(Base):
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    course_code = Column(String, unique=True, nullable=False) # e.g., 'CMP 401'
    title = Column(String, nullable=False)
    units = Column(Integer, nullable=False)
    estimated_students = Column(Integer, nullable=False)
    lecturer = Column(String, nullable=True)
    
    # Auto-Extracted Fields
    department = Column(String, nullable=False) # e.g., 'CMP'
    level = Column(Integer, nullable=False)     # e.g., 400
    semester = Column(Integer, nullable=False)  # e.g., 1 or 2
    category = Column(String, nullable=False)   # e.g., 'Core', 'GST', 'FIC'

class Venue(Base):
    __tablename__ = 'venues'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    venue_type = Column(String, nullable=False) # e.g., 'Lab', 'Hall'
    allowed_prefixes = Column(String, nullable=False) # e.g., 'CMP, MTH'

# Create the SQLite engine
engine = create_engine('sqlite:///timetable.db', echo=False)

# This function builds the tables when we run the app
def init_db():
    Base.metadata.create_all(engine)