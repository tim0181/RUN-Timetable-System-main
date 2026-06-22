import csv
import random

# --- CONFIGURATION ---
NUM_COURSES = 1400
NUM_VENUES = 200
NUM_LECTURERS = 500

DEPARTMENTS = ['CMP', 'LAW', 'BUS', 'ACC', 'ECN', 'POL', 'PSY', 'MTH', 'PHY', 'MCB', 'BCH', 'ENG', 'GST', 'FIC']
VENUE_TYPES = ['Lecture Hall', 'Laboratory', 'Studio']
COURSE_TITLES = ['Introduction to', 'Advanced', 'Principles of', 'Applied', 'Fundamentals of', 'Modern']

def generate_venues():
    print(f"Generating {NUM_VENUES} venues...")
    with open('large_venues.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Venue Name', 'Capacity', 'Venue Type', 'Allowed Prefixes'])
        
        for i in range(1, NUM_VENUES + 1):
            name = f"RunHall {i:03d}"
            # Heavily weight smaller rooms, with a few massive auditoriums
            capacity = random.choices(
                [60, 100, 150, 250, 500, 800, 1500], 
                weights=[30, 30, 20, 10, 5, 3, 2]
            )[0]
            
            v_type = random.choice(VENUE_TYPES)
            
            if capacity >= 500:
                prefixes = "ALL"
            else:
                # Assign 1 to 3 random departments to a room
                deps = random.sample(DEPARTMENTS, k=random.randint(1, 3))
                prefixes = ", ".join(deps)
                
            writer.writerow([name, capacity, v_type, prefixes])

def generate_courses_and_lecturers():
    print(f"Generating {NUM_COURSES} courses and mapping {NUM_LECTURERS} lecturers...")
    
    # 1. Create Lecturers
    lecturers = [f"Dr. Lecturer_{i}" for i in range(1, NUM_LECTURERS + 1)]
    
    # 2. Generate Courses and allocate lecturers
    with open('large_courses.csv', 'w', newline='', encoding='utf-8') as fc, \
         open('large_lecturer_allocations.csv', 'w', newline='', encoding='utf-8') as fl:
        
        c_writer = csv.writer(fc)
        c_writer.writerow(['Department', 'Course Code', 'Title', 'Level', 'Students', 'Category'])
        
        l_writer = csv.writer(fl)
        l_writer.writerow(['Course Code', 'Lecturer'])
        
        generated_codes = set()
        
        for i in range(NUM_COURSES):
            dept = random.choice(DEPARTMENTS)
            level = random.choice([100, 200, 300, 400, 500])
            
            # Ensure unique course codes
            while True:
                code_num = random.randint(101, 599)
                course_code = f"{dept} {code_num}"
                if course_code not in generated_codes:
                    generated_codes.add(course_code)
                    break
            
            title = f"{random.choice(COURSE_TITLES)} {dept}"
            
            # GSTs/FICs have massive student counts, regular courses have 20-200
            if dept in ['GST', 'FIC']:
                students = random.randint(500, 1200)
                category = 'Universal'
            else:
                students = random.randint(20, 200)
                category = 'Departmental'
                
            c_writer.writerow([dept, course_code, title, level, students, category])
            
            # Assign a random lecturer to this course
            assigned_lecturer = random.choice(lecturers)
            l_writer.writerow([course_code, assigned_lecturer])

if __name__ == "__main__":
    generate_venues()
    generate_courses_and_lecturers()
    print("✅ Successfully generated large_courses.csv, large_venues.csv, and large_lecturer_allocations.csv!")