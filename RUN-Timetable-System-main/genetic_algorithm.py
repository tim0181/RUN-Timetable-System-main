import random
import copy
import math

# ==========================================
# GENETIC ALGORITHM PARAMETERS
# ==========================================
POPULATION_SIZE = 200
GENERATIONS = 1000
MUTATION_RATE = 0.15
ELITE_PERCENTAGE = 0.10

# --- GRID CONSTANTS ---
TOTAL_EXAM_SLOTS = 18    # 6 Days * 3 Sessions
TOTAL_LECTURE_SLOTS = 20 # 5 Days * 4 Sessions (2-hour blocks)
WEDNESDAY_LATE_SLOT = 11 # Slot index for Wed 15:00-17:00 (Pinned GST/FIC)
FRIDAY_LATE_SLOT = 19    # Slot index for Fri 15:00-17:00 (Forbidden)

class Schedule:
    def __init__(self, assignments):
        self.assignments = assignments
        self.fitness = 0
        self.clashes = 0

def prepare_lecture_batches(courses, all_venues):
    """
    PRE-PROCESSOR: Splits oversized lecture courses into Group A, Group B.
    Exams are ignored here (they split by space, not time).
    RULE: Only split IF required capacity >= 1.5x the largest available venue.
    """
    processed_courses = []
    
    for course in courses:
        # 1. Prune the search space to find allowed venues
        valid_venues = [v for v in all_venues if 'ALL' in v.allowed_prefixes.upper() or course.department.upper() in v.allowed_prefixes.upper()]
        if not valid_venues:
            valid_venues = all_venues
            
        largest_venue = max(valid_venues, key=lambda x: x.capacity)
        required_capacity = course.estimated_students * 1.2
        
        # 2. THE 1.5x OVERFLOW RULE
        if required_capacity >= (1.5 * largest_venue.capacity):
            # Massive breach detected! We must split into batches.
            num_batches = math.ceil(required_capacity / largest_venue.capacity)
            students_per_batch = course.estimated_students // num_batches
            
            for i in range(num_batches):
                batch_course = copy.deepcopy(course)
                batch_course.course_code = f"{course.course_code} (Group {chr(65+i)})"
                batch_course.estimated_students = students_per_batch
                batch_course.is_batch = True
                batch_course.base_code = course.course_code 
                processed_courses.append(batch_course)
        else:
            # If it's under capacity, OR only slightly over capacity (e.g., 1.2x), do not split!
            course.is_batch = False
            course.base_code = course.course_code
            processed_courses.append(course)
            
    return processed_courses

def get_best_fit_venues(course, venues, timetable_type):
    # Determine the multiplier based on the exam or lecture type
    multiplier = 2.0 if timetable_type == "Exam Timetable" else 1.2
    required_capacity = course.estimated_students * multiplier
    
    # Filter venues to ONLY those the department is allowed to use
    valid_venues = []
    for v in venues:
        if v.allowed_prefixes.upper() == "ALL" or course.department.upper() in v.allowed_prefixes.upper():
            valid_venues.append(v)
            
    if not valid_venues:
        return []

    large_enough_venues = [v for v in valid_venues if v.capacity >= required_capacity]
    
    if large_enough_venues:
        large_enough_venues.sort(key=lambda x: x.capacity)
        pool_size = min(5, len(large_enough_venues))
        chosen_venue = random.choice(large_enough_venues[:pool_size])
        return [chosen_venue]
    else:
        # If no single venue is big enough, split it across the largest available ones
        valid_venues.sort(key=lambda x: x.capacity, reverse=True)
        allocated = []
        current_cap = 0
        for v in valid_venues:
            allocated.append(v)
            current_cap += v.capacity
            if current_cap >= required_capacity:
                break
        return allocated

def calculate_fitness(schedule, timetable_type):
    """
    THE REDEEMER'S MATRIX: Evaluates based on constraints and matrices.
    """
    is_exam = (timetable_type == "Exam Timetable")
    fitness_score = 1000
    clashes = 0
    
    venue_slot_tracker = {} 
    student_slot_tracker = {}
    lecturer_slot_tracker = {} # Tracks optional lecturer allocations
    batch_tracker = {} # Tracks Group A/B back-to-back logic
    
    for assignment in schedule.assignments:
        course = assignment['course']
        assigned_venues = assignment['venues'] 
        slot = assignment['slot']
        
        day = slot // 3 if is_exam else slot // 4
        slot_of_day = slot % 3 if is_exam else slot % 4
        
        # --- HARD CONSTRAINTS ---
        # 1. Room Double-Booking
        for venue in assigned_venues:
            if (venue.id, slot) in venue_slot_tracker:
                fitness_score -= 100
                clashes += 1
            else:
                venue_slot_tracker[(venue.id, slot)] = course
                
        # 2. Cohort Double-Booking (e.g., CMP 400L)
        if "GST" not in course.category.upper() and "FIC" not in course.category.upper():
            cohort_key = (course.department, course.level, slot)
            if cohort_key in student_slot_tracker:
                fitness_score -= 100
                clashes += 1
            else:
                student_slot_tracker[cohort_key] = course

        # 3. Lecturer Double-Booking (Optional Check)
        course_lecturer = getattr(course, 'lecturer', None)
        if course_lecturer: # Only applies if the lecturer field is populated
            lecturer_key = (course_lecturer, slot)
            if lecturer_key in lecturer_slot_tracker:
                fitness_score -= 100
                clashes += 1
            else:
                lecturer_slot_tracker[lecturer_key] = course

        # --- THE REDEEMER'S LECTURE MATRIX (Soft Constraints) ---
        if not is_exam:
            # The Universal GST/FIC Pin (Wed 15:00)
            is_universal = ("GST" in course.category.upper() or "FIC" in course.category.upper())
            if is_universal and slot != WEDNESDAY_LATE_SLOT:
                fitness_score -= 200 # Heavy penalty for placing GST outside Wed 3pm
            if not is_universal and slot == WEDNESDAY_LATE_SLOT:
                fitness_score -= 100 # Keep Wed 3pm clear for GSTs
                
            # The 3 PM Target Penalty (Slot index 3 of any day)
            if slot_of_day == 3 and slot != WEDNESDAY_LATE_SLOT:
                fitness_score -= 50
                
            # The Friday Freedom Penalty (Friday 13:00 - 15:00)
            if day == 4 and slot_of_day == 2:
                fitness_score -= 500
                
            # Batch Back-to-Back Logic
            if getattr(course, 'is_batch', False):
                if course.base_code not in batch_tracker:
                    batch_tracker[course.base_code] = []
                batch_tracker[course.base_code].append(slot)

    # Evaluate Batches (Must be close together)
    for base_code, slots in batch_tracker.items():
        if len(slots) > 1:
            slots.sort()
            for i in range(len(slots)-1):
                # If they are not adjacent, penalize
                if slots[i+1] - slots[i] > 1:
                    fitness_score -= 80

    schedule.fitness = fitness_score
    schedule.clashes = clashes
    return schedule

def create_initial_population(courses, venues, timetable_type, exam_weeks=1):
    population = []
    is_exam = (timetable_type == "Exam Timetable")
    
    # Calculate dynamic slots based on weeks selected
    total_exam_slots = exam_weeks * 6 * 3 # Weeks * 6 Days * 3 Sessions
    
    working_courses = courses if is_exam else prepare_lecture_batches(courses, venues)
    
    if is_exam:
        valid_slots = list(range(total_exam_slots))
    else:
        valid_slots = [s for s in range(TOTAL_LECTURE_SLOTS) if s != FRIDAY_LATE_SLOT]
    
    for _ in range(POPULATION_SIZE):
        assignments = []
        for course in working_courses:
            chosen_venues = get_best_fit_venues(course, venues, timetable_type)
            
            is_universal = ("GST" in course.category.upper() or "FIC" in course.category.upper())
            if not is_exam and is_universal:
                chosen_slot = WEDNESDAY_LATE_SLOT
            else:
                chosen_slot = random.choice(valid_slots)
            
            assignments.append({
                'course': course,
                'venues': chosen_venues, 
                'slot': chosen_slot
            })
            
        new_schedule = Schedule(assignments)
        population.append(calculate_fitness(new_schedule, timetable_type))
        
    return population, working_courses

def evolve(population, courses, venues, timetable_type, exam_weeks=1):
    is_exam = (timetable_type == "Exam Timetable")
    total_exam_slots = exam_weeks * 6 * 3 
    
    if is_exam:
        valid_slots = list(range(total_exam_slots))
    else:
        valid_slots = [s for s in range(TOTAL_LECTURE_SLOTS) if s != FRIDAY_LATE_SLOT]

    population.sort(key=lambda x: x.fitness, reverse=True)
    new_population = []
    
    elite_count = int(POPULATION_SIZE * 0.1)
    new_population.extend(population[:elite_count])
    
    while len(new_population) < POPULATION_SIZE:
        parent1 = max(random.sample(population, 3), key=lambda x: x.fitness)
        parent2 = max(random.sample(population, 3), key=lambda x: x.fitness)
        
        split_point = random.randint(0, len(courses) - 1)
        child_assignments = parent1.assignments[:split_point] + parent2.assignments[split_point:]
        
        for assignment in child_assignments:
            if random.random() < MUTATION_RATE:
                is_unv = ("GST" in assignment['course'].category.upper() or "FIC" in assignment['course'].category.upper())
                if not is_exam and is_unv:
                    assignment['slot'] = WEDNESDAY_LATE_SLOT
                else:
                    assignment['slot'] = random.choice(valid_slots)
                    
            if random.random() < MUTATION_RATE:
                assignment['venues'] = get_best_fit_venues(assignment['course'], venues, timetable_type)
                    
        child = Schedule(child_assignments)
        new_population.append(calculate_fitness(child, timetable_type))
        
    return new_population

def generate_optimal_timetable(courses, venues, timetable_type, exam_weeks=1):
    if not courses or not venues:
        return None
        
    population, working_courses = create_initial_population(courses, venues, timetable_type, exam_weeks)
    
    for generation in range(GENERATIONS):
        population = evolve(population, working_courses, venues, timetable_type, exam_weeks)
        best_schedule = max(population, key=lambda x: x.fitness)
        
        if best_schedule.clashes == 0:
            break
            
    return max(population, key=lambda x: x.fitness)