from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


def get_database_connection():
    connection = sqlite3.connect("attendance.db")
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():
    connection = get_database_connection()

    students = connection.execute(
        "SELECT * FROM students"
    ).fetchall()

    connection.close()

    return render_template("index.html", students=students)


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


if __name__ == "__main__":
    app.run(debug=True)