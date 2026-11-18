import mysql.connector
from mysql.connector import Error

def register_request(connection):
    print("\n--- REGISTER NEW SERVICE REQUEST ---")

    student_name = input("Enter student name: ").strip()
    service_type = input("Enter service type: ").strip()

    if not student_name or not service_type:
        print("Student name and service type cannot be empty.")
        return

    print("\nAvailable departments:")
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT department_id, department_name
            FROM departments
            ORDER BY department_id
        """)

        departments = cursor.fetchall()

        for department in departments:
            print(
                f"{department['department_id']}. "
                f"{department['department_name']}"
            )

        try:
            department_id = int(input("Choose department number: "))
        except ValueError:
            print("Please enter a valid department number.")
            return

        valid_ids = [d["department_id"] for d in departments]

        if department_id not in valid_ids:
            print("Invalid department selection.")
            return

        cursor.execute("""
            INSERT INTO service_requests
                (student_name, service_type, department_id, request_date, status)
            VALUES (%s, %s, %s, CURDATE(), 'Pending')
        """, (student_name, service_type, department_id))

        connection.commit()
        print("Request registered successfully!")
        print("New ticket number:", cursor.lastrowid)

    except Error as error:
        connection.rollback()
        print("Could not register request:", error)

    finally:
        cursor.close()

def update_request_status(connection):
    print("\n--- UPDATE REQUEST STATUS ---")

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT request_id, student_name, service_type, status
            FROM service_requests
            ORDER BY request_id DESC
        """)

        requests = cursor.fetchall()

        if not requests:
            print("No service requests found.")
            return

        print("\nAvailable requests:")

        for request in requests:
            print(
                f"Ticket #{request['request_id']} | "
                f"{request['student_name']} | "
                f"{request['service_type']} | "
                f"Status: {request['status']}"
            )

        try:
            request_id = int(input("\nEnter ticket number to update: "))
        except ValueError:
            print("Please enter a valid ticket number.")
            return

        cursor.execute("""
            SELECT request_id
            FROM service_requests
            WHERE request_id = %s
        """, (request_id,))

        if cursor.fetchone() is None:
            print("Ticket number not found.")
            return

        print("\nChoose the new status:")
        print("1. Pending")
        print("2. In Progress")
        print("3. Resolved")

        status_choice = input("Enter your choice: ").strip()

        status_options = {
            "1": "Pending",
            "2": "In Progress",
            "3": "Resolved"
        }

        if status_choice not in status_options:
            print("Invalid status choice.")
            return

        new_status = status_options[status_choice]

        if new_status == "Resolved":
            cursor.execute("""
                UPDATE service_requests
                SET status = %s,
                    resolved_date = COALESCE(resolved_date, CURDATE())
                WHERE request_id = %s
            """, (new_status, request_id))
        else:
            cursor.execute("""
                UPDATE service_requests
                SET status = %s,
                    resolved_date = NULL
                WHERE request_id = %s
            """, (new_status, request_id))

        connection.commit()

        print(f"Ticket #{request_id} updated successfully!")
        print("New status:", new_status)

    except Error as error:
        connection.rollback()
        print("Could not update request:", error)

    finally:
        cursor.close()

def show_overdue_requests(connection):
    print("\n--- OVERDUE REQUEST ANALYSIS ---")

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                sr.request_id,
                sr.student_name,
                sr.service_type,
                d.department_name,
                sr.status,
                DATEDIFF(CURDATE(), sr.request_date) AS days_open
            FROM service_requests sr
            JOIN departments d
                ON sr.department_id = d.department_id
            WHERE sr.status != 'Resolved'
              AND DATEDIFF(CURDATE(), sr.request_date) >= 7
            ORDER BY days_open DESC
        """)

        requests = cursor.fetchall()

        if not requests:
            print("No requests have been open for 7 or more days.")
            return

        print("Requests open for 7 or more days:\n")

        for request in requests:
            print(
                f"Ticket #{request['request_id']} | "
                f"{request['student_name']} | "
                f"{request['service_type']} | "
                f"{request['department_name']} | "
                f"{request['status']} | "
                f"Open for {request['days_open']} days"
            )

        print(f"\nTotal overdue requests: {len(requests)}")

    except Error as error:
        print("Could not generate overdue report:", error)

    finally:
        cursor.close()

def show_department_performance(connection):
    print("\n--- DEPARTMENT PERFORMANCE ANALYSIS ---")

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                d.department_name,
                COUNT(sr.request_id) AS total_requests,
                SUM(
                    CASE
                        WHEN sr.status IN ('Pending', 'In Progress')
                        THEN 1
                        ELSE 0
                    END
                ) AS open_requests,
                SUM(
                    CASE
                        WHEN sr.status = 'Resolved'
                        THEN 1
                        ELSE 0
                    END
                ) AS resolved_requests,
                ROUND(
                    AVG(
                        CASE
                            WHEN sr.status = 'Resolved'
                            THEN DATEDIFF(
                                sr.resolved_date,
                                sr.request_date
                            )
                            ELSE NULL
                        END
                    ), 2
                ) AS avg_resolution_days
            FROM departments d
            LEFT JOIN service_requests sr
                ON d.department_id = sr.department_id
            GROUP BY d.department_id, d.department_name
            ORDER BY open_requests DESC,
                     avg_resolution_days DESC
        """)

        departments = cursor.fetchall()

        print("\nDepartments ranked by open requests:\n")

        for rank, department in enumerate(departments, start=1):
            average = department["avg_resolution_days"]

            if average is None:
                average_text = "N/A"
            else:
                average_text = f"{average} days"

            print(
                f"{rank}. {department['department_name']} | "
                f"Total requests: {department['total_requests']} | "
                f"Open: {department['open_requests']} | "
                f"Resolved: {department['resolved_requests']} | "
                f"Average resolution: {average_text}"
            )

    except Error as error:
        print("Could not generate department report:", error)

    finally:
        cursor.close()

def main():
    connection = None
    cursor = None

    try:
        # Connect to our project database
        connection = mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="Saniya@12",
            database="student_service_analytics",
            connection_timeout=5,
            use_pure=True
        )

        print("\n=== STUDENT SERVICE AND DELAY ANALYTICS ===")
        print("MySQL connection successful!\n")

        cursor = connection.cursor(dictionary=True)

        # 1. Retrieve service requests with department details
        cursor.execute("""
            SELECT
                s.request_id,
                s.student_name,
                s.service_type,
                d.department_name,
                s.request_date,
                s.resolved_date,
                s.status,
                DATEDIFF(
                    COALESCE(s.resolved_date, CURDATE()),
                    s.request_date
                ) AS days_elapsed
            FROM service_requests s
            JOIN departments d
                ON s.department_id = d.department_id
            ORDER BY s.request_date DESC
        """)

        requests = cursor.fetchall()

        print("--- SERVICE REQUESTS ---")

        if not requests:
            print("No service requests found.")
            print("We need to insert sample records into MySQL.")
        else:
            for item in requests:
                print(
                    f"Ticket #{item['request_id']} | "
                    f"{item['student_name']} | "
                    f"{item['service_type']} | "
                    f"{item['department_name']} | "
                    f"Status: {item['status']} | "
                    f"Days elapsed: {item['days_elapsed']}"
                )

        # 2. Count requests by status
        cursor.execute("""
            SELECT status, COUNT(*) AS total
            FROM service_requests
            GROUP BY status
            ORDER BY status
        """)

        print("\n--- REQUEST STATUS SUMMARY ---")

        status_summary = cursor.fetchall()

        if status_summary:
            for item in status_summary:
                print(f"{item['status']}: {item['total']}")
        else:
            print("No status data available.")

        # 3. Calculate average resolution time
        cursor.execute("""
            SELECT ROUND(
                AVG(DATEDIFF(resolved_date, request_date)), 2
            ) AS average_days
            FROM service_requests
            WHERE status = 'Resolved'
              AND resolved_date IS NOT NULL
        """)

        result = cursor.fetchone()

        print("\n--- DELAY ANALYSIS ---")

        if result["average_days"] is None:
            print("No resolved requests available for this calculation.")
        else:
            print(
                "Average resolution time: "
                f"{result['average_days']} days"
            )

        # 4. Find open requests at least 3 days old
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM service_requests
            WHERE status IN ('Pending', 'In Progress')
              AND request_date <= DATE_SUB(
                  CURDATE(), INTERVAL 3 DAY
              )
        """)

        delayed = cursor.fetchone()["total"]

        
        # 5. Department-wise analytics
        cursor.execute("""
            SELECT
                d.department_name,
                COUNT(s.request_id) AS total_requests,
                SUM(
                    CASE
                        WHEN s.status IN ('Pending', 'In Progress')
                        THEN 1
                        ELSE 0
                    END
                ) AS open_requests,
                SUM(
                    CASE
                        WHEN s.status = 'Resolved'
                        THEN 1
                        ELSE 0
                    END
                ) AS resolved_requests,
                ROUND(
                    AVG(
                        CASE
                            WHEN s.status = 'Resolved'
                             AND s.resolved_date IS NOT NULL
                            THEN DATEDIFF(
                                s.resolved_date,
                                s.request_date
                            )
                        END
                    ), 2
                ) AS avg_resolution_days
            FROM departments d
            LEFT JOIN service_requests s
                ON d.department_id = s.department_id
            GROUP BY
                d.department_id,
                d.department_name
            ORDER BY
                open_requests DESC,
                total_requests DESC,
                d.department_name
        """)

        department_summary = cursor.fetchall()

        print("\n--- DEPARTMENT-WISE ANALYTICS ---")

        for item in department_summary:
            average = item["avg_resolution_days"]

            if average is None:
                average_text = "N/A"
            else:
                average_text = f"{average} days"

            print(
                f"{item['department_name']} | "
                f"Total: {item['total_requests']} | "
                f"Open: {item['open_requests']} | "
                f"Resolved: {item['resolved_requests']} | "
                f"Average resolution: {average_text}"
            )

       
        print("\n--- PROJECT MENU ---")
        print("1. Register a new service request")
        print("2. Update request status")
        print("3. View overdue requests")
        print("4. View department performance")
        print("5. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            register_request(connection)
        elif choice == "2":
            update_request_status(connection)
        elif choice == "3":
            show_overdue_requests(connection)
        elif choice == "4":
            show_department_performance(connection)
        elif choice == "5":
            print("Exiting project.")
        else:
            print("Invalid choice.")


    except Error as error:
        print("\nA database error occurred:")
        print(error)

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()

        print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()


