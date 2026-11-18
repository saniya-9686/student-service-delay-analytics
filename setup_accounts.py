
import mysql.connector
from werkzeug.security import generate_password_hash
from getpass import getpass

DB_NAME = "student_service_analytics"


def main():
    # Collect credentials for the initial demo accounts.
    print("=== Student Service Portal: Account Setup ===")

    roll_number = input(
        "Demo student roll number [MCA001]: "
    ).strip() or "MCA001"

    student_name = input(
        "Student name [Demo Student]: "
    ).strip() or "Demo Student"

    student_password = getpass(
        "Set a password for the student account: "
    )

    admin_username = input(
        "Admin username [admin]: "
    ).strip() or "admin"

    admin_password = getpass(
        "Set a password for the admin account: "
    )

    if not student_password or not admin_password:
        print("Passwords cannot be empty. Run the setup again.")
        return

    connection = None
    cursor = None

    try:
        connection = mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="Saniya@12",
            database=DB_NAME,
            connection_timeout=5,
            use_pure=True
        )

        cursor = connection.cursor()

        # Create the registered students table.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INT AUTO_INCREMENT PRIMARY KEY,
                roll_number VARCHAR(50) NOT NULL UNIQUE,
                student_name VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create the administrators table.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                admin_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Link future requests to a student account.
        cursor.execute(
            "SHOW COLUMNS FROM service_requests LIKE 'student_id'"
        )

        if cursor.fetchone() is None:
            cursor.execute("""
                ALTER TABLE service_requests
                ADD COLUMN student_id INT NULL
            """)

        # Add a foreign key without changing old tickets.
        cursor.execute("""
            SELECT CONSTRAINT_NAME
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = %s
              AND TABLE_NAME = 'service_requests'
              AND CONSTRAINT_NAME = 'fk_service_requests_student'
        """, (DB_NAME,))

        if cursor.fetchone() is None:
            cursor.execute("""
                ALTER TABLE service_requests
                ADD CONSTRAINT fk_service_requests_student
                FOREIGN KEY (student_id)
                REFERENCES students(student_id)
                ON DELETE SET NULL
            """)

        # Create the student account if it doesn't already exist.
        cursor.execute(
            "SELECT student_id FROM students WHERE roll_number = %s",
            (roll_number,)
        )

        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO students
                    (roll_number, student_name, password_hash)
                VALUES (%s, %s, %s)
            """, (
                roll_number,
                student_name,
                generate_password_hash(student_password)
            ))
            print("Student account created.")
        else:
            print("That student account already exists; it was not changed.")

        # Create the admin account if it doesn't already exist.
        cursor.execute(
            "SELECT admin_id FROM admins WHERE username = %s",
            (admin_username,)
        )

        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO admins (username, password_hash)
                VALUES (%s, %s)
            """, (
                admin_username,
                generate_password_hash(admin_password)
            ))
            print("Admin account created.")
        else:
            print("That admin account already exists; it was not changed.")

        connection.commit()

        print("\nAccount setup completed successfully!")
        print("Student roll number:", roll_number)
        print("Admin username:", admin_username)
        print("Your passwords are stored as hashes in MySQL.")
        print("Existing requests have not been deleted.")

    except mysql.connector.Error as error:
        if connection is not None:
            connection.rollback()
        print("Database setup error:", error)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()
