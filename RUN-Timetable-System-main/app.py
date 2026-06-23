import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from io import BytesIO
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import init_db, engine, Course, Venue
from genetic_algorithm import generate_optimal_timetable

# 1. Initialize the database
init_db()

# 2. Helper Function: The RUN Course Auto-Extractor
def extract_course_details(course_code):
    """Extracts Dept, Level, and Semester from a code like 'CMP 401'"""
    try:
        parts = course_code.strip().split()
        dept = parts[0].upper()       # e.g., 'CMP'
        number = parts[1]             # e.g., '401'
        
        level = int(number[0]) * 100  # e.g., 4 * 100 = 400
        semester = 1 if int(number[-1]) % 2 != 0 else 2 # Odd=1, Even=2
        
        return dept, level, semester
    except Exception as e:
        return None, None, None

# 3. Configure the Streamlit Page
st.set_page_config(page_title="RUN Timetable Generator", layout="wide")

# PWA manifest and service worker registration
components.html(
    """
    <link rel="manifest" href="/app/static/manifest.json">
    <meta name="theme-color" content="#020381">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <script>
      if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
          navigator.serviceWorker.register('/app/static/sw.js')
            .then(function(reg) { console.log('Service worker registered:', reg); })
            .catch(function(err) { console.warn('SW registration failed:', err); });
        });
      }
    </script>
    """,
    height=0,
)

st.title("🎓 RUN Automated Timetable System")
st.markdown("---")

# Navigation
st.sidebar.header("Navigation")
menu = st.sidebar.radio("Go to:", ["Dashboard", "Import Data", "Generate Timetable"])

# Fetch live database stats
with Session(engine) as session:
    total_courses = session.query(Course).count()
    total_venues = session.query(Venue).count()

# PAGE: DASHBOARD
if menu == "Dashboard":
    st.subheader("System Overview")
    st.success("Database is live and connected.")
    
    col1, col2 = st.columns(2)
    col1.metric("Total Courses in Database", total_courses)
    col2.metric("Total Venues in Database", total_venues)
    
    # Quick view of data if it exists
    if total_courses > 0:
        st.write("### Recent Courses")
        with Session(engine) as db_session:
            courses_df = pd.read_sql(db_session.query(Course).statement, db_session.bind)
            st.dataframe(courses_df.drop(columns=['id']).tail()) # Hide ID column, show latest

# PAGE: IMPORT DATA
elif menu == "Import Data":
    st.subheader("📥 Mass Import System")
    st.write("Upload your Excel or CSV file to populate the database.")
    
    # 1. The File Uploader
    uploaded_file = st.file_uploader("Upload Courses File (CSV or Excel)", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        # 2. Read the file into Pandas
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
                
            st.success("File read successfully! Here is a preview:")
            st.dataframe(df.head()) # Shows the first 5 rows so you can check it
            
            st.warning("⚠️ Make sure your columns match the expected names below before saving.")
            
            # 3. The Import Button
            if st.button("💾 Save Courses to Database", use_container_width=True):
                with st.spinner("Processing and Auto-Extracting details..."):
                    with Session(engine) as db_session:
                        success_count = 0
                        
                        for index, row in df.iterrows():
                            try:
                                # --- COLUMN MAPPING ---
                                # Change the text inside the brackets to match EXACTLY what your CSV headers are named!
                                # e.g., if your CSV header is "Course Code", use row['Course Code']
                                raw_code = str(row['Course Code']).strip()
                                raw_title = str(row['Course Title']).strip()
                                raw_dept = str(row['Department']).strip()
                                raw_students = int(row['Students'])
                                
                                # Category might not exist in your CSV, so we use .get() to default to "Core"
                                raw_category = str(row.get('Category', 'Core')).strip() 
                                
                                # --- SMART AUTO-EXTRACTION ---
                                # Splits "CMP 401" into "CMP" and "401"
                                parts = raw_code.split()
                                if len(parts) >= 2:
                                    num_part = parts[1] # Grabs the "401"
                                    
                                    # Level: Multiply the first digit by 100 (4 * 100 = 400L)
                                    calculated_level = int(num_part[0]) * 100 
                                    
                                    # Semester: If last digit is odd, it's 1st Sem. If even, 2nd Sem.
                                    calculated_semester = 1 if int(num_part[-1]) % 2 != 0 else 2
                                else:
                                    calculated_level = 100
                                    calculated_semester = 1
                                    
                                # Add this line to grab units (defaults to 3 if the column is missing)
                                raw_units = int(row.get('Units', 3)) 
                                
                                # --- SAVE TO DATABASE ---
                                existing_course = db_session.query(Course).filter(Course.course_code == raw_code).first()
                                if existing_course:
                                    existing_course.title = raw_title
                                    existing_course.units = raw_units
                                    existing_course.department = raw_dept
                                    existing_course.level = calculated_level
                                    existing_course.semester = calculated_semester
                                    existing_course.estimated_students = raw_students
                                    existing_course.category = raw_category
                                else:
                                    new_course = Course(
                                        course_code=raw_code,
                                        title=raw_title,
                                        units=raw_units,
                                        department=raw_dept,
                                        level=calculated_level,
                                        semester=calculated_semester,
                                        estimated_students=raw_students,
                                        category=raw_category
                                    )    
                                    db_session.add(new_course)
                                success_count += 1
                                
                            except Exception as e:
                                # If one row fails (e.g., missing data), it skips it and tells you which one failed
                                st.error(f"Error on row {index + 2} ({raw_code}): {e}")
                                
                        # Commit all the saved courses permanently!
                        db_session.commit()
                        st.success(f"✅ Masterful Execution! Successfully committed {success_count} courses to the database.")
                        
        except Exception as e:
            st.error(f"Could not read file: {e}")
      
    # VENUE IMPORT SECTION
    st.markdown("---")
    st.subheader("🏢 Mass Import Venues")
    st.write("Upload your Excel or CSV file to populate the venue database.")
    
    # We use a unique key here so Streamlit doesn't confuse it with the Course uploader
    venue_file = st.file_uploader("Upload Venues File (CSV or Excel)", type=["csv", "xlsx"], key="venue_uploader")
    
    if venue_file is not None:
        try:
            if venue_file.name.endswith('.csv'):
                v_df = pd.read_csv(venue_file)
            else:
                v_df = pd.read_excel(venue_file)
                
            st.success("Venue file read successfully! Here is a preview:")
            st.dataframe(v_df.head())
            
            if st.button("💾 Save Venues to Database", use_container_width=True):
                with st.spinner("Processing venue capacities and compartmentalization rules..."):
                    with Session(engine) as db_session:
                        venue_success_count = 0
                        
                        for index, row in v_df.iterrows():
                            try:
                                # --- EXACT COLUMN MAPPING ---
                                raw_venue_name = str(row['Venue Name']).strip()
                                raw_capacity = int(row['Capacity'])
                                raw_prefixes = str(row['Allowed Prefixes']).strip()
                                
                                # Add this line to grab venue type (defaults to 'Lecture Hall' if missing)
                                raw_type = str(row.get('Venue Type', 'Lecture Hall')).strip()
                                
                                # --- SAVE TO DATABASE ---
                                new_venue = Venue(
                                    name=raw_venue_name,
                                    capacity=raw_capacity,
                                    venue_type=raw_type,    # <--- THIS IS THE MISSING PIECE!
                                    allowed_prefixes=raw_prefixes
                                )
                                db_session.add(new_venue)
                                venue_success_count += 1
                                
                            except Exception as e:
                                st.error(f"Error on row {index + 2}: {e}")
                                
                        # Commit all venues
                        db_session.commit()
                        st.success(f"✅ Masterful Execution! Successfully committed {venue_success_count} venues to the database.")
                        
        except Exception as e:
            st.error(f"Could not read venue file: {e}")
    # DATABASE MANAGEMENT (DELETE DATA)
    st.markdown("---")
    st.subheader("🗑️ Database Management")
    colA, colB = st.columns(2)
    
    with colA:
        if st.button("🚨 Delete ALL Courses", use_container_width=True):
            with Session(engine) as db_session:
                db_session.query(Course).delete()
                db_session.commit()
                st.success("All courses have been wiped from the database.")
    
    with colB:
        if st.button("🚨 Delete ALL Venues", use_container_width=True):
            with Session(engine) as db_session:
                db_session.query(Venue).delete()
                db_session.commit()
                st.success("All venues have been wiped from the database.")
                
    # (OPTIONAL) LECTURER ALLOCATION IMPORT
    st.markdown("---")
    st.subheader("👨‍🏫 (Optional) Import Lecturer Allocations")
    st.write("Upload a file linking courses to lecturers to prevent double-booking.")
    
    lec_file = st.file_uploader("Upload Lecturer File (CSV/Excel) [Columns: Course Code, Lecturer]", type=["csv", "xlsx"], key="lec_uploader")
    
    if lec_file is not None:
        try:
            if lec_file.name.endswith('.csv'):
                l_df = pd.read_csv(lec_file)
            else:
                l_df = pd.read_excel(lec_file)
                
            st.dataframe(l_df.head())
            
            if st.button("💾 Map Lecturers to Courses", use_container_width=True):
                with st.spinner("Mapping lecturers to existing courses..."):
                    with Session(engine) as db_session:
                        mapped_count = 0
                        
                        for index, row in l_df.iterrows():
                            raw_code = str(row['Course Code']).strip()
                            raw_lecturer = str(row['Lecturer']).strip()
                            
                            # Find the course in the DB and update it
                            course_to_update = db_session.query(Course).filter(Course.course_code == raw_code).first()
                            
                            if course_to_update:
                                course_to_update.lecturer = raw_lecturer
                                mapped_count += 1
                                
                        db_session.commit()
                        st.success(f"✅ Successfully mapped lecturers to {mapped_count} courses!")
                        
        except Exception as e:
            st.error(f"Could not read lecturer file: {e}")

    # MANUAL ENTRY FORMS
    st.markdown("---")
    st.subheader("✍️ Manual Data Entry")
    
    tab1, tab2 = st.tabs(["Add Single Course", "Add Single Venue"])
    
    with tab1:
        with st.form("manual_course_form"):
            st.write("Enter details for a single course:")
            c_code = st.text_input("Course Code (e.g., CMP 401)")
            c_title = st.text_input("Course Title")
            c_dept = st.text_input("Department (e.g., CMP)")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                c_level = st.selectbox("Level", [100, 200, 300, 400, 500])
            with col2:
                c_semester = st.selectbox("Semester", [1, 2])
            with col3:
                c_units = st.number_input("Units", min_value=1, max_value=6, value=3)
                
            col4, col5, col6 = st.columns(3)
            with col4:
                c_students = st.number_input("Estimated Students", min_value=1, value=50)
            with col5:
                c_category = st.selectbox("Category", ["Core", "Elective", "Universal"])
            with col6:
                c_duration = st.number_input("Exam Duration (Hrs)", min_value=1, max_value=4, value=3)
                
            submit_course = st.form_submit_button("➕ Save Course")
            
            if submit_course and c_code and c_title:
                with Session(engine) as db_session:
                    new_course = Course(
                        course_code=c_code, title=c_title, department=c_dept,
                        level=c_level, semester=c_semester, units=c_units,
                        estimated_students=c_students, category=c_category,
                        duration=c_duration  # Uses the new duration column!
                    )
                    db_session.add(new_course)
                    db_session.commit()
                    st.success(f"Added {c_code} successfully!")

    with tab2:
        with st.form("manual_venue_form"):
            st.write("Enter details for a single venue:")
            v_name = st.text_input("Venue Name (e.g., BOJA Auditorium)")
            v_cap = st.number_input("Seating Capacity", min_value=10, value=100)
            v_type = st.selectbox("Venue Type", ["Lecture Hall", "Laboratory", "Studio"])
            v_pref = st.text_input("Allowed Prefixes (e.g., ALL or CMP, MTH)", value="ALL")
            
            submit_venue = st.form_submit_button("➕ Save Venue")
            
            if submit_venue and v_name:
                with Session(engine) as db_session:
                    new_venue = Venue(
                        name=v_name, capacity=v_cap, venue_type=v_type, allowed_prefixes=v_pref
                    )
                    db_session.add(new_venue)
                    db_session.commit()
                    st.success(f"Added {v_name} successfully!")

# PAGE: GENERATE TIMETABLE
# ==========================================
# PAGE: GENERATE TIMETABLE
# ==========================================
elif menu == "Generate Timetable":
    st.subheader("⚙️ Timetable Generation Engine")
    st.write("Configure your generation parameters below based on the uploaded session data.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        timetable_type = st.radio("Select Timetable Type:", ["Lecture Timetable", "Exam Timetable"])
    with col2:
        target_semester = st.radio("Select Semester:", ["1st Semester", "2nd Semester"])
    with col3:
        # Show week selector ONLY if it's an exam timetable!
        if timetable_type == "Exam Timetable":
            exam_weeks = st.number_input("Exam Period Duration (Weeks)", min_value=1, max_value=4, value=2)
        else:
            exam_weeks = 1 # Lectures don't use this, they are just a standard 1-week looping matrix
            st.info("Lectures generate on a standard 1-week recurring cycle.")
        
    st.markdown("---")
    sem_int = 1 if target_semester == "1st Semester" else 2
    
    with Session(engine) as db_session:
        target_courses = db_session.query(Course).filter(Course.semester == sem_int).all()
        all_venues = db_session.query(Venue).all()
        
        if len(target_courses) == 0 or len(all_venues) == 0:
            st.warning("⚠️ Missing Data: Ensure you have uploaded both Courses and Venues for this semester.")
        else:
            if 'generated_timetable' not in st.session_state:
                st.session_state.generated_timetable = None
                st.session_state.generated_timetable_type = None
                st.session_state.generated_timetable_semester = None
                st.session_state.generated_timetable_display_times = None

            if st.button(f"🚀 Generate {timetable_type}", use_container_width=True):
                with st.spinner("🧬 Generating timetable... Please wait."):
                    # Pass the exact number of weeks into the engine!
                    best_schedule = generate_optimal_timetable(target_courses, all_venues, timetable_type, exam_weeks)

                    if best_schedule:
                        st.success(f"🎉 Generated! (Clashes: {best_schedule.clashes}, Fitness Score: {best_schedule.fitness})")

                        table_data = []
                        exam_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                        lecture_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                        full_week_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

                        for assignment in best_schedule.assignments:
                            c = assignment['course']
                            v_list = assignment['venues']
                            slot = assignment['slot']
                            venue_names = ", ".join([v.name for v in v_list])

                            # 3. Dynamic Week & Day Translation
                            if timetable_type == "Exam Timetable":
                                day_index = slot // 3
                                week_num = (day_index // 6) + 1  # Calculates if it's Week 1, 2, 3, etc.
                                day_name = exam_days[day_index % len(exam_days)]
                                day_str = f"Week {week_num} - {day_name}"

                                session_idx = slot % 3
                                times = ["08:00 AM - 11:00 AM", "12:00 PM - 03:00 PM", "04:00 PM - 07:00 PM"]
                                time_str = times[session_idx]
                            else:
                                day_name = lecture_days[slot // 4]
                                day_str = day_name
                                session_idx = slot % 4
                                times = ["08:00 AM - 10:00 AM", "10:00 AM - 12:00 PM", "01:00 PM - 03:00 PM", "03:00 PM - 05:00 PM"]
                                time_str = times[session_idx]

                            table_data.append({
                                "Department": c.department,
                                "Course Code": c.course_code,
                                "Title": c.title,
                                "Level": c.level,
                                "Students": c.estimated_students,
                                "Day": day_str,
                                "Time": time_str,
                                "Allocated Venue(s)": venue_names
                            })

                        # 3. Display the final output
                        result_df = pd.DataFrame(table_data)

                        # Sort chronologically for better reading
                        day_order = {day: i for i, day in enumerate(full_week_order)}
                        result_df['Day_Name'] = result_df['Day'].apply(lambda x: x.split(' - ')[-1])
                        result_df['Day_Rank'] = result_df['Day_Name'].map(day_order)
                        result_df = result_df.sort_values(by=['Day_Rank', 'Time']).drop(columns=['Day_Rank', 'Day_Name'])

                        display_times = [
                            "08:00 AM - 11:00 AM",
                            "12:00 PM - 03:00 PM",
                            "04:00 PM - 07:00 PM"
                        ] if timetable_type == "Exam Timetable" else [
                            "08:00 AM - 10:00 AM",
                            "10:00 AM - 12:00 PM",
                            "01:00 PM - 03:00 PM",
                            "03:00 PM - 05:00 PM"
                        ]

                        st.session_state.generated_timetable = result_df
                        st.session_state.generated_timetable_type = timetable_type
                        st.session_state.generated_timetable_semester = target_semester
                        st.session_state.generated_timetable_display_times = display_times

            if st.session_state.generated_timetable is not None:
                if st.session_state.generated_timetable_type == timetable_type and st.session_state.generated_timetable_semester == target_semester:
                    result_df = st.session_state.generated_timetable
                    display_times = st.session_state.generated_timetable_display_times

                    level_options = ["All"] + sorted(result_df['Level'].unique().tolist())
                    selected_level = st.selectbox("Filter by Course Level", level_options, index=0)
                    if selected_level != "All":
                        filtered_df = result_df[result_df['Level'] == selected_level]
                    else:
                        filtered_df = result_df

                    if filtered_df.empty:
                        st.warning("No timetable entries match the selected level.")
                    else:
                        for department, dept_df in filtered_df.groupby('Department'):
                            dept_df = dept_df.copy()
                            dept_df['Course Details'] = dept_df.apply(
                                lambda row: f"{row['Course Code']} ({row['Title']})\n{row['Allocated Venue(s)']}",
                                axis=1
                            )
                            pivot = dept_df.pivot_table(
                                index='Day',
                                columns='Time',
                                values='Course Details',
                                aggfunc=' \n'.join,
                                fill_value=''
                            )
                            pivot = pivot.reindex(columns=display_times)
                            st.subheader(f"Department: {department}")
                            
                            # Build column config for a professional schedule grid
                            pivot = pivot.reset_index()
                            column_config = {
                                "Day": st.column_config.TextColumn("Day", width="medium", pinned=True),
                            }
                            for col in pivot.columns:
                                if col != "Day":
                                    column_config[col] = st.column_config.TextColumn(
                                        col,
                                        width="large",
                                        max_chars=120,
                                    )
                            
                            # Style the dataframe to highlight actual clash cells
                            def highlight_clashes(val):
                                val_str = str(val).strip()
                                if not val_str:
                                    return ''
                                if '\n' in val_str:
                                    courses = val_str.split('\n')
                                    venues_per_course = []
                                    for course in courses:
                                        lines = course.strip().split('\n')
                                        if len(lines) > 1:
                                            venues_per_course.append(lines[-1])
                                    all_venues = []
                                    for venue_info in venues_per_course:
                                        all_venues.extend([v.strip() for v in venue_info.split(',') if v.strip()])
                                    if len(all_venues) > len(set(all_venues)):
                                        return 'border: 3px solid red; background-color: #ffe6e6;'
                                return ''
                            
                            styled_pivot = pivot.style.map(highlight_clashes)
                            st.dataframe(
                                styled_pivot,
                                use_container_width=True,
                                hide_index=True,
                                column_config=column_config,
                            )

                            dept_csv = pivot.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label=f"📥 Download {department} Timetable as CSV",
                                data=dept_csv,
                                file_name=f"{timetable_type}_{target_semester}_{department}.csv",
                                mime="text/csv",
                                key=f"download_{department}"
                            )

                        excel_buffer = BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            for department, dept_df in filtered_df.groupby('Department'):
                                dept_df = dept_df.copy()
                                dept_df['Course Details'] = dept_df.apply(
                                    lambda row: f"{row['Course Code']} ({row['Title']})\n{row['Allocated Venue(s)']}",
                                    axis=1
                                )
                                pivot = dept_df.pivot_table(
                                    index='Day',
                                    columns='Time',
                                    values='Course Details',
                                    aggfunc=' \n'.join,
                                    fill_value=''
                                )
                                pivot = pivot.reindex(columns=display_times)
                                sheet_name = department[:31]
                                pivot.reset_index().to_excel(writer, sheet_name=sheet_name, index=False)
                        excel_buffer.seek(0)
                        st.download_button(
                            label="📥 Download Full Timetable as Excel",
                            data=excel_buffer,
                            file_name=f"{timetable_type}_{target_semester}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                else:
                    st.info("A timetable is stored for a previous configuration. Change back to the same timetable type and semester to continue filtering it, or regenerate for the current settings.")
        