import pytest
from genetic_algorithm import prepare_lecture_batches, calculate_fitness, Schedule


class SimpleCourse:
    def __init__(self, course_code, department, estimated_students, category, level=100, semester=1, lecturer=None):
        self.course_code = course_code
        self.department = department
        self.estimated_students = estimated_students
        self.category = category
        self.level = level
        self.semester = semester
        self.lecturer = lecturer


class SimpleVenue:
    def __init__(self, id, capacity, allowed_prefixes):
        self.id = id
        self.capacity = capacity
        self.allowed_prefixes = allowed_prefixes


def test_prepare_lecture_batches_does_not_split_small_course():
    course = SimpleCourse('CMP 401', 'CMP', 40, 'Core')
    venue = SimpleVenue(1, 60, 'CMP')

    result = prepare_lecture_batches([course], [venue])

    assert len(result) == 1
    assert result[0].course_code == 'CMP 401'
    assert result[0].is_batch is False
    assert result[0].base_code == 'CMP 401'


def test_prepare_lecture_batches_splits_large_course():
    course = SimpleCourse('CMP 401', 'CMP', 200, 'Core')
    venue = SimpleVenue(1, 60, 'CMP')

    result = prepare_lecture_batches([course], [venue])

    assert len(result) >= 2
    assert all(hasattr(c, 'is_batch') for c in result)
    assert all(c.base_code == 'CMP 401' for c in result)


def test_calculate_fitness_penalizes_room_double_booking():
    course1 = SimpleCourse('CMP 401', 'CMP', 20, 'Core')
    course2 = SimpleCourse('CMP 402', 'CMP', 20, 'Core')
    venue = SimpleVenue(1, 60, 'CMP')

    schedule = Schedule([
        {'course': course1, 'venues': [venue], 'slot': 0},
        {'course': course2, 'venues': [venue], 'slot': 0}
    ])

    scored = calculate_fitness(schedule, 'Lecture Timetable')

    assert scored.clashes == 2
    assert scored.fitness < 1000


def test_calculate_fitness_enforces_gst_pin():
    course = SimpleCourse('GST 101', 'GST', 50, 'GST')
    venue = SimpleVenue(1, 60, 'ALL')

    schedule = Schedule([
        {'course': course, 'venues': [venue], 'slot': 0}
    ])

    scored = calculate_fitness(schedule, 'Lecture Timetable')
    assert scored.fitness < 1000


def test_calculate_fitness_allows_gst_at_wed_late():
    course = SimpleCourse('GST 101', 'GST', 50, 'GST')
    venue = SimpleVenue(1, 60, 'ALL')

    schedule = Schedule([
        {'course': course, 'venues': [venue], 'slot': 11}
    ])

    scored = calculate_fitness(schedule, 'Lecture Timetable')
    assert scored.fitness == 1000
