from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Course, Venue


def test_database_course_and_venue_insertions():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        course = Course(
            course_code='CMP 401',
            title='Database Systems',
            units=3,
            department='CMP',
            level=400,
            semester=1,
            estimated_students=40,
            category='Core'
        )
        venue = Venue(
            name='Hall A',
            capacity=80,
            venue_type='Lecture Hall',
            allowed_prefixes='CMP'
        )
        session.add(course)
        session.add(venue)
        session.commit()

        assert session.query(Course).count() == 1
        assert session.query(Venue).count() == 1


def test_course_save_and_retrieve():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        course = Course(
            course_code='GST 101',
            title='Communication Skills',
            units=2,
            department='GST',
            level=100,
            semester=1,
            estimated_students=100,
            category='GST'
        )
        session.add(course)
        session.commit()

        record = session.query(Course).filter_by(course_code='GST 101').first()
        assert record.title == 'Communication Skills'
