
import mysql.connector
from werkzeug.security import generate_password_hash
from getpass import getpass

# Use the same MySQL connection details as your app.py.
# Replace YOUR_MYSQL_PASSWORD with your current local password.
connection = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="Saniya@12",
    database="student_service_analytics",
    use_pure=True
)

cursor = connection.cursor()

try:
    username = input("Admin username [admin]: ").strip() or "admin"
    new_password = getpass("Enter your new admin password: ")

    if not new_password:
        print("Password cannot be empty.")
    else:
        password_hash = generate_password_hash(new_password)

        cursor.execute(
            "SELECT admin_id FROM admins WHERE username = %s",
            (username,)
        )

        existing_admin = cursor.fetchone()

        if existing_admin:
            cursor.execute(
                "UPDATE admins SET password_hash = %s "
                "WHERE username = %s",
                (password_hash, username)
            )
            print("Existing admin password reset successfully!")
        else:
            cursor.execute(
                "INSERT INTO admins (username, password_hash) "
                "VALUES (%s, %s)",
                (username, password_hash)
            )
            print("New admin account created successfully!")

        connection.commit()
        print("Admin username:", username)
        print("Keep your new password somewhere safe.")

except mysql.connector.Error as error:
    connection.rollback()
    print("Database error:", error)

finally:
    cursor.close()
    connection.close()
