from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


def get_database_connection():
    connection = sqlite3.connect("attendance.db")
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():
    selected_student_id = request.args.get("student_id")

    connection = get_database_connection()

    students = connection.execute(
        "SELECT * FROM students"
    ).fetchall()
    selected_student_name = None

    if selected_student_id:
        selected_student = connection.execute(
            "SELECT name FROM students WHERE id = ?",
            (selected_student_id,)
        ).fetchone()

        if selected_student:
            selected_student_name = selected_student["name"]

    subjects = connection.execute(
        "SELECT * FROM subjects"
    ).fetchall()

    attendance = connection.execute(
        """
        SELECT
            attendance.id,
            students.name AS student_name,
            subjects.name AS subject_name,
            attendance.classes_held,
            attendance.classes_attended
        FROM attendance
        JOIN students
            ON attendance.student_id = students.id
        JOIN subjects
            ON attendance.subject_id = subjects.id
        """
    ).fetchall()

    marks = connection.execute(
        """
        SELECT
            marks.id,
            students.name AS student_name,
            subjects.name AS subject_name,
            marks.marks_obtained,
            marks.total_marks
        FROM marks
        JOIN students
            ON marks.student_id = students.id
        JOIN subjects
            ON marks.subject_id = subjects.id
        """
    ).fetchall()

    # Calculate attendance for selected student
    if selected_student_id:
        total_held = connection.execute(
            """
            SELECT SUM(classes_held)
            FROM attendance
            WHERE student_id = ?
            """,
            (selected_student_id,)
        ).fetchone()[0] or 0

        total_attended = connection.execute(
            """
            SELECT SUM(classes_attended)
            FROM attendance
            WHERE student_id = ?
            """,
            (selected_student_id,)
        ).fetchone()[0] or 0
    else:
        total_held = 0
        total_attended = 0

    if total_held > 0:
        overall_attendance = (total_attended / total_held) * 100
    else:
        overall_attendance = 0

    # Calculate marks for selected student
    if selected_student_id:
        total_marks = connection.execute(
            """
            SELECT SUM(total_marks)
            FROM marks
            WHERE student_id = ?
            """,
            (selected_student_id,)
        ).fetchone()[0] or 0

        obtained_marks = connection.execute(
            """
            SELECT SUM(marks_obtained)
            FROM marks
            WHERE student_id = ?
            """,
            (selected_student_id,)
        ).fetchone()[0] or 0
    else:
        total_marks = 0
        obtained_marks = 0

    if total_marks > 0:
        overall_marks = (obtained_marks / total_marks) * 100
    else:
        overall_marks = 0

    # Get subject-wise performance for selected student
    subject_performance = []

    if selected_student_id:
        subject_performance = connection.execute(
            """
            SELECT
                subjects.name AS subject_name,

                COALESCE(
                    SUM(attendance.classes_attended) * 100.0 /
                    NULLIF(SUM(attendance.classes_held), 0),
                    0
                ) AS attendance_percentage,

                COALESCE(
                    SUM(marks.marks_obtained) * 100.0 /
                    NULLIF(SUM(marks.total_marks), 0),
                    0
                ) AS marks_percentage

            FROM subjects

            LEFT JOIN attendance
                ON subjects.id = attendance.subject_id
                AND attendance.student_id = ?

            LEFT JOIN marks
                ON subjects.id = marks.subject_id
                AND marks.student_id = ?

            GROUP BY subjects.id
            """,
            (selected_student_id, selected_student_id)
        ).fetchall()

    connection.close()

    return render_template(
        "index.html",
        students=students,
        subjects=subjects,
        attendance=attendance,
        marks=marks,
        overall_attendance=overall_attendance,
        overall_marks=overall_marks,
        selected_student_name=selected_student_name,
        subject_performance=subject_performance
    )

@app.route("/add-student", methods=["POST"])
def add_student():
    name = request.form["name"]
    email = request.form["email"]

    connection = get_database_connection()

    connection.execute(
        "INSERT INTO students (name, email) VALUES (?, ?)",
        (name, email)
    )

    connection.commit()
    connection.close()

    return redirect("/")


@app.route("/add-subject", methods=["POST"])
def add_subject():
    subject_name = request.form["subject_name"]

    connection = get_database_connection()

    connection.execute(
        "INSERT INTO subjects (name) VALUES (?)",
        (subject_name,)
    )

    connection.commit()
    connection.close()

    return redirect("/")
# =============================
# EDIT SUBJECT
# =============================

@app.route("/edit-subject/<int:subject_id>", methods=["POST"])
def edit_subject(subject_id):

    subject_name = request.form["subject_name"]

    connection = get_database_connection()

    connection.execute(
        """
        UPDATE subjects
        SET name = ?
        WHERE id = ?
        """,
        (subject_name, subject_id)
    )

    connection.commit()
    connection.close()

    return redirect("/")


# =============================
# DELETE SUBJECT
# =============================

@app.route("/delete-subject/<int:subject_id>")
def delete_subject(subject_id):

    connection = get_database_connection()

    # Delete attendance records for this subject
    connection.execute(
        "DELETE FROM attendance WHERE subject_id = ?",
        (subject_id,)
    )

    # Delete marks records for this subject
    connection.execute(
        "DELETE FROM marks WHERE subject_id = ?",
        (subject_id,)
    )

    # Delete the subject
    connection.execute(
        "DELETE FROM subjects WHERE id = ?",
        (subject_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/")



@app.route("/add-attendance", methods=["POST"])
def add_attendance():
    student_id = request.form["student_id"]
    subject_id = request.form["subject_id"]
    classes_held = int(request.form["classes_held"])
    classes_attended = int(request.form["classes_attended"])

    if classes_attended > classes_held:
        return "Classes attended cannot be greater than classes held."

    connection = get_database_connection()

    connection.execute(
        """
        INSERT INTO attendance
        (student_id, subject_id, classes_held, classes_attended)
        VALUES (?, ?, ?, ?)
        """,
        (
            student_id,
            subject_id,
            classes_held,
            classes_attended
        )
    )

    connection.commit()
    connection.close()

    return redirect("/")
# =============================
# EDIT ATTENDANCE
# =============================

@app.route("/edit-attendance/<int:attendance_id>", methods=["POST"])
def edit_attendance(attendance_id):

    student_id = request.form["student_id"]
    subject_id = request.form["subject_id"]

    classes_held = int(request.form["classes_held"])
    classes_attended = int(request.form["classes_attended"])

    if classes_attended > classes_held:
        return "Classes attended cannot be greater than classes held."

    connection = get_database_connection()

    connection.execute(
        """
        UPDATE attendance
        SET student_id = ?,
            subject_id = ?,
            classes_held = ?,
            classes_attended = ?
        WHERE id = ?
        """,
        (
            student_id,
            subject_id,
            classes_held,
            classes_attended,
            attendance_id
        )
    )

    connection.commit()
    connection.close()

    return redirect("/")


# =============================
# DELETE ATTENDANCE
# =============================

@app.route("/delete-attendance/<int:attendance_id>")
def delete_attendance(attendance_id):

    connection = get_database_connection()

    connection.execute(
        "DELETE FROM attendance WHERE id = ?",
        (attendance_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/")


@app.route("/add-marks", methods=["POST"])
def add_marks():
    student_id = request.form["student_id"]
    subject_id = request.form["subject_id"]
    marks_obtained = float(request.form["marks_obtained"])
    total_marks = float(request.form["total_marks"])

    if marks_obtained > total_marks:
        return "Marks obtained cannot be greater than total marks."

    connection = get_database_connection()

    connection.execute(
        """
        INSERT INTO marks
        (student_id, subject_id, marks_obtained, total_marks)
        VALUES (?, ?, ?, ?)
        """,
        
        (
            student_id,
            subject_id,
            marks_obtained,
            total_marks
        )
    )

    connection.commit()
    connection.close()

    return redirect("/")


# =============================
# EDIT MARKS
# =============================

@app.route("/edit-marks/<int:marks_id>", methods=["GET", "POST"])
def edit_marks(marks_id):

    connection = get_database_connection()

    # When the form is submitted
    if request.method == "POST":

        student_id = request.form.get("student_id")
        subject_id = request.form.get("subject_id")
        marks_obtained = request.form.get("marks_obtained")
        total_marks = request.form.get("total_marks")

        # Check that all fields were submitted
        if not student_id or not subject_id or not marks_obtained or not total_marks:
            connection.close()
            return "Please fill all fields."

        marks_obtained = float(marks_obtained)
        total_marks = float(total_marks)

        if marks_obtained > total_marks:
            connection.close()
            return "Marks obtained cannot be greater than total marks."

        connection.execute(
            """
            UPDATE marks
            SET student_id = ?,
                subject_id = ?,
                marks_obtained = ?,
                total_marks = ?
            WHERE id = ?
            """,
            (
                student_id,
                subject_id,
                marks_obtained,
                total_marks,
                marks_id
            )
        )

        connection.commit()
        connection.close()

        return redirect("/")

    # When Edit button is clicked
    students = connection.execute(
        "SELECT * FROM students"
    ).fetchall()

    subjects = connection.execute(
        "SELECT * FROM subjects"
    ).fetchall()

    mark = connection.execute(
        "SELECT * FROM marks WHERE id = ?",
        (marks_id,)
    ).fetchone()

    connection.close()

    return render_template(
        "edit_marks.html",
        mark=mark,
        students=students,
        subjects=subjects
    )


# =============================
# DELETE MARKS
# =============================

@app.route("/delete-marks/<int:marks_id>")
def delete_marks(marks_id):

    connection = get_database_connection()

    connection.execute(
        "DELETE FROM marks WHERE id = ?",
        (marks_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/")
# =============================
# EDIT STUDENT
# =============================

@app.route("/edit-student/<int:student_id>", methods=["POST"])
def edit_student(student_id):

    name = request.form["name"]
    email = request.form["email"]

    connection = get_database_connection()

    connection.execute(
        """
        UPDATE students
        SET name = ?, email = ?
        WHERE id = ?
        """,
        (name, email, student_id)
    )

    connection.commit()
    connection.close()

    return redirect("/")


# =============================
# DELETE STUDENT
# =============================

@app.route("/delete-student/<int:student_id>")
def delete_student(student_id):

    connection = get_database_connection()

    connection.execute(
        "DELETE FROM attendance WHERE student_id = ?",
        (student_id,)
    )

    connection.execute(
        "DELETE FROM marks WHERE student_id = ?",
        (student_id,)
    )

    connection.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/")


# =============================
# RUN APPLICATION
# =============================



if __name__ == "__main__":
    app.run(debug=True)