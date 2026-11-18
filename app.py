
from flask import Flask, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from html import escape

app = Flask(__name__)
app.secret_key = "b0678fbc10629df9bb08eea98b666e81783d017c427e7c112f276f869710c27c"

from functools import wraps

def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped_view


def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="Saniya@12",
        database="student_service_analytics",
        connection_timeout=5,
        use_pure=True
    )


@app.route("/", methods=["GET", "POST"])
def home():
    message = ""

    student_id = session.get("student_id")

    if not student_id or session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_name = session.get("student_name", "")

    if request.method == "POST":
        service_type = request.form.get("service_type", "").strip()
       
        department_mapping = {
            "Bonafide Certificate": "Student Administration",
            "Fee Payment Issue": "Accounts Department",
            "Exam Registration Issue": "Examination Cell",
            "ID Card Replacement": "ID Card Office",
            "Scholarship Enquiry": "Scholarship Section",
            "Fee Receipt": "Accounts Department",
            "Hall Ticket Issue": "Examination Cell",
        }

        department = department_mapping.get(service_type)


        if not service_type or not department:
            message = "Please fill in all the fields."
        else:
            connection = None
            cursor = None
            ticket_id = None

            try:
                connection = get_db_connection()
                if connection is None:
                    raise mysql.connector.Error("Database connection returned None.")

                cursor = connection.cursor()
                if cursor is None:
                    raise mysql.connector.Error("Database cursor could not be created.")

                cursor.execute(
                    "SELECT department_id FROM departments "
                    "WHERE department_name = %s",
                    (department,)
                )
                department_row = cursor.fetchone()

                if department_row is None:
                    message = "Department not found in the database."
                else:
                    cursor.execute(
                        """
                        SELECT request_id
                        FROM service_requests
                        WHERE student_id = %s
                        AND LOWER(service_type) = LOWER(%s)
                        AND status IN ('Pending', 'In Progress')
                        ORDER BY request_id DESC
                        LIMIT 1
                        """,
                        (student_id, service_type)
                    )

                    existing_request = cursor.fetchone()

                    if existing_request is not None:
                        message = (
                            f"You already have an open request for {service_type} "
                            f"(ticket #{existing_request[0]}). "
                            "Please check My Requests / Track Status."
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO service_requests
                            (student_id, student_name, service_type, department_id,
                            request_date, status)
                            VALUES (%s, %s, %s, %s, CURDATE(), %s)
                            """,
                            (
                                student_id,
                                student_name,
                                service_type,
                                department_row[0],
                                "Pending"
                            )
                        )
                        connection.commit()
                        ticket_id = cursor.lastrowid
                        return redirect(
                            url_for("confirmation", ticket_id=ticket_id)
                        )

            except mysql.connector.Error as error:
                if connection is not None:
                    connection.rollback()
                print("MySQL error:", error)
                message = "Could not save the request. Check the VS Code terminal."

            finally:
                if cursor is not None:
                    cursor.close()
                if connection is not None and connection.is_connected():
                    connection.close()

    message_html = escape(message)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Student Service Portal</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f1f5f9;
                padding: 40px 15px;
            }}
            .container {{
                max-width: 500px;
                margin: auto;
                background: white;
                padding: 28px;
                border-radius: 12px;
            }}
            h1 {{ color: #1e3a8a; }}
            label {{
                display: block;
                margin-top: 16px;
                font-weight: bold;
            }}
            input, select, button {{
                box-sizing: border-box;
                width: 100%;
                padding: 11px;
                margin-top: 7px;
                border-radius: 6px;
                border: 1px solid #cbd5e1;
            }}
            button {{
                margin-top: 22px;
                background: #1d4ed8;
                color: white;
                border: none;
                cursor: pointer;
            }}
            .message {{ color: #b91c1c; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Student Service Portal</h1>
            <p>Submit a request for a college service.</p>

            <form method="POST">
                <label>Service Type</label>
                <select name="service_type" required>
                    <option value="">Select a service</option>
                    <option>Bonafide Certificate</option>
                    <option>Fee Payment Issue</option>
                    <option>Exam Registration Issue</option>
                    <option>ID Card Replacement</option>
                    <option>Scholarship Enquiry</option>
                    <option>Fee Receipt</option>
                    <option>Hall Ticket Issue</option>
                </select>
                <button type="submit">Submit Request</button>
                </form>


            <p class="message">{message_html}</p>
            <p><a href="/my_requests">My Requests / Track Status</a></p>
            <p><a href="/logout">Logout</a></p>
        </div>
    </body>
    </html>
    """


@app.route("/confirmation/<int:ticket_id>")
def confirmation(ticket_id):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Request Confirmation</title>
    </head>
    <body style="font-family: Arial; padding: 40px;">
        <h1>Request Submitted Successfully!</h1>
        <p>Your ticket number is <strong>{ticket_id}</strong>.</p>
        <p>Your request has been saved in the database.</p>
        <a href="/">Submit another request</a>
    </body>
    </html>
    """


@app.route("/update_status", methods=["POST"])
@admin_required
def update_status():
    ticket_id = request.form.get("ticket_id", type=int)
    new_status = request.form.get("status", "")

    allowed_statuses = ["Pending", "In Progress", "Resolved"]

    if not ticket_id or new_status not in allowed_statuses:
        return "Invalid ticket number or status.", 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE service_requests
            SET status = %s,
                resolved_date = CASE
                    WHEN %s = 'Resolved' THEN CURDATE()
                    ELSE NULL
                END
            WHERE request_id = %s
            """,
            (new_status, new_status, ticket_id)
        )

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT request_id FROM service_requests "
                "WHERE request_id = %s",
                (ticket_id,)
            )
            if cursor.fetchone() is None:
                connection.rollback()
                return "Ticket not found.", 404

        connection.commit()

    except mysql.connector.Error as error:
        if connection is not None:
            connection.rollback()
        print("Status update error:", error)
        return "Could not update the ticket. Check the VS Code terminal.", 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    return redirect(url_for("admin"))



@app.route("/admin")
@admin_required
def admin():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # 1. Get all student requests
        cursor.execute("""
            SELECT
                sr.request_id,
                sr.student_name,
                sr.service_type,
                d.department_name,
                sr.request_date,
                sr.status
            FROM service_requests sr
            JOIN departments d
                ON sr.department_id = d.department_id
            ORDER BY sr.request_id DESC
        """)

        requests_data = cursor.fetchall()

        # 2. Calculate request status totals
        cursor.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(status = 'Pending'), 0),
                COALESCE(SUM(status = 'In Progress'), 0),
                COALESCE(SUM(status = 'Resolved'), 0)
            FROM service_requests
        """)

        counts = cursor.fetchone()
        total_count = counts[0]
        pending_count = counts[1]
        progress_count = counts[2]
        resolved_count = counts[3]

        # 3. Find open requests that are 7 or more days old
        cursor.execute("""
            SELECT
                sr.request_id,
                sr.student_name,
                sr.service_type,
                d.department_name,
                sr.request_date,
                DATEDIFF(CURDATE(), sr.request_date),
                sr.status
            FROM service_requests sr
            JOIN departments d
                ON sr.department_id = d.department_id
            WHERE sr.status IN ('Pending', 'In Progress')
              AND sr.request_date <= DATE_SUB(
                  CURDATE(), INTERVAL 7 DAY
              )
            ORDER BY sr.request_date ASC
        """)

        overdue_data = cursor.fetchall()

        # Department-wise workload and resolution analytics
        cursor.execute("""
            SELECT
                d.department_name,
                COUNT(sr.request_id),
                COALESCE(SUM(sr.status = 'Pending'), 0),
                COALESCE(SUM(sr.status = 'In Progress'), 0),
                COALESCE(SUM(sr.status = 'Resolved'), 0),
                ROUND(
                    AVG(
                        CASE
                            WHEN sr.status = 'Resolved'
                            AND sr.resolved_date IS NOT NULL
                            THEN DATEDIFF(
                                sr.resolved_date,
                                sr.request_date
                            )
                        END
                    ),
                    1
                )
            FROM departments d
            LEFT JOIN service_requests sr
                ON sr.department_id = d.department_id
            GROUP BY d.department_id, d.department_name
            ORDER BY COUNT(sr.request_id) DESC, d.department_name
        """)

        department_data = cursor.fetchall()

        # 4. Build the complete request table
        rows_html = ""

        for row in requests_data:
            ticket_id, student, service, department, request_date, status = row

            rows_html += f"""
            <tr>
                <td>{ticket_id}</td>
                <td>{escape(str(student))}</td>
                <td>{escape(str(service))}</td>
                <td>{escape(str(department))}</td>
                <td>{escape(str(request_date))}</td>
                <td>
                    <form method="POST" action="/update_status">
                        <input type="hidden" name="ticket_id"
                               value="{ticket_id}">

                        <select name="status" required>
                            <option value="Pending"
                                {"selected" if status == "Pending" else ""}>
                                Pending
                            </option>
                            <option value="In Progress"
                                {"selected" if status == "In Progress" else ""}>
                                In Progress
                            </option>
                            <option value="Resolved"
                                {"selected" if status == "Resolved" else ""}>
                                Resolved
                            </option>
                        </select>

                        <button type="submit">Update</button>
                    </form>
                </td>
            </tr>
            """

        # 5. Build the overdue requests table
        overdue_rows_html = ""

        for row in overdue_data:
            ticket_id, student, service, department, request_date, days_open, status = row

            overdue_rows_html += f"""
            <tr>
                <td>{ticket_id}</td>
                <td>{escape(str(student))}</td>
                <td>{escape(str(service))}</td>
                <td>{escape(str(department))}</td>
                <td>{escape(str(request_date))}</td>
                <td>{days_open} days</td>
                <td>{escape(str(status))}</td>
            </tr>
            """

        if not overdue_rows_html:
            overdue_rows_html = """
            <tr>
                <td colspan="7">
                    No open requests are overdue by 7 or more days.
                </td>
            </tr>
            """

        # Build department analytics table
        department_rows_html = ""

        for row in department_data:
            department_name, total, pending, in_progress, resolved, avg_days = row

            if avg_days is None:
                avg_display = "N/A"
            else:
                avg_display = f"{avg_days} days"

            department_rows_html += f"""
            <tr>
                <td>{escape(str(department_name))}</td>
                <td>{total}</td>
                <td>{pending}</td>
                <td>{in_progress}</td>
                <td>{resolved}</td>
                <td>{escape(avg_display)}</td>
            </tr>
            """

        # Build a chart comparing request statuses by department
        department_status_rows_html = ""

        max_department_total = max(
            (int(row[1] or 0) for row in department_data),
            default=1
        )
        if max_department_total < 1:
            max_department_total = 1

        for row in department_data:
            department_name, total, pending, in_progress, resolved, avg_days = row

            pending_value = int(pending or 0)
            progress_value = int(in_progress or 0)
            resolved_value = int(resolved or 0)

            pending_width = pending_value / max_department_total * 100
            progress_width = progress_value / max_department_total * 100
            resolved_width = resolved_value / max_department_total * 100

            pending_label = str(pending_value) if pending_value else ""
            progress_label = str(progress_value) if progress_value else ""
            resolved_label = str(resolved_value) if resolved_value else ""

            department_status_rows_html += f"""
            <div class="chart-row">
                <div class="chart-label">
                    {escape(str(department_name))}
                </div>

                <div class="stacked-bar">
                    <div class="bar-segment pending-bar"
                         style="width: {pending_width:.2f}%"
                         title="Pending: {pending_value}">
                        {pending_label}
                    </div>

                    <div class="bar-segment progress-bar"
                         style="width: {progress_width:.2f}%"
                         title="In Progress: {progress_value}">
                        {progress_label}
                    </div>

                    <div class="bar-segment resolved-bar"
                         style="width: {resolved_width:.2f}%"
                         title="Resolved: {resolved_value}">
                        {resolved_label}
                    </div>
                </div>

                <div class="chart-value">{int(total or 0)}</div>
            </div>
            """

        # Build a chart of average resolution time
        resolution_chart_rows_html = ""

        resolved_department_data = [
            (row[0], float(row[5]))
            for row in department_data
            if row[5] is not None
        ]

        max_average_days = max(
            (avg_days for department_name, avg_days in resolved_department_data),
            default=1.0
        )

        if max_average_days <= 0:
            max_average_days = 1.0

        for department_name, avg_days in resolved_department_data:
            bar_width = max(avg_days, 0) / max_average_days * 100

            resolution_chart_rows_html += f"""
            <div class="chart-row">
                <div class="chart-label">
                    {escape(str(department_name))}
                </div>

                <div class="resolution-track">
                    <div class="resolution-bar"
                         style="width: {bar_width:.2f}%">
                    </div>
                </div>

                <div class="chart-value">{avg_days:.1f} days</div>
            </div>
            """

        if not resolution_chart_rows_html:
            resolution_chart_rows_html = """
            <p class="note">
                No resolved requests with valid resolution dates yet.
            </p>
            """

        # 6. Display the dashboard
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Student Service Analytics Dashboard</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 25px;
                    background: #f1f5f9;
                    color: #1e293b;
                }}

                h1, h2 {{
                    color: #1e3a8a;
                }}

                .cards {{
                    display: grid;
                    grid-template-columns: repeat(
                        auto-fit, minmax(150px, 1fr)
                    );
                    gap: 15px;
                    margin: 20px 0;
                }}

                .card {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 5px #00000010;
                }}

                .card h3 {{
                    margin-top: 0;
                    font-size: 15px;
                    color: #475569;
                }}

                .number {{
                    font-size: 30px;
                    font-weight: bold;
                }}

                .table-container {{
                    overflow-x: auto;
                    background: white;
                    padding: 15px;
                    margin-bottom: 30px;
                    border-radius: 10px;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}

                th, td {{
                    padding: 12px;
                    border-bottom: 1px solid #e2e8f0;
                    text-align: left;
                }}

                th {{
                    background: #1d4ed8;
                    color: white;
                }}

                select, button {{
                    padding: 8px;
                    margin: 3px;
                }}

                button {{
                    background: #1d4ed8;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }}

                
                .chart-panel {{
                    background: white;
                    padding: 15px;
                    margin-bottom: 25px;
                    border-radius: 10px;
                    overflow-x: auto;
                }}

                .chart-panel h3 {{
                    margin-top: 0;
                    color: #334155;
                }}

                .chart-row {{
                    display: grid;
                    grid-template-columns: 190px minmax(180px, 1fr) 90px;
                    gap: 12px;
                    align-items: center;
                    margin: 12px 0;
                    min-width: 570px;
                }}

                .chart-label {{
                    font-size: 14px;
                    overflow-wrap: anywhere;
                }}

                .stacked-bar,
                .resolution-track {{
                    display: flex;
                    width: 100%;
                    height: 28px;
                    background: #e2e8f0;
                    border-radius: 6px;
                    overflow: hidden;
                }}

                .bar-segment {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                    white-space: nowrap;
                }}

                .pending-bar {{
                    background: #d97706;
                }}

                .progress-bar {{
                    background: #2563eb;
                }}

                .resolved-bar {{
                    background: #16a34a;
                }}

                .chart-value {{
                    text-align: right;
                    font-size: 13px;
                    font-weight: bold;
                    white-space: nowrap;
                }}

                .chart-legend {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 16px;
                    margin: 12px 0;
                    font-size: 13px;
                }}

                .chart-legend span {{
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                }}

                .legend-swatch {{
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 3px;
                }}

                .pending-color {{
                    background: #d97706;
                }}

                .progress-color {{
                    background: #2563eb;
                }}

                .resolved-color {{
                    background: #16a34a;
                }}

                .resolution-bar {{
                    height: 100%;
                    background: #0f766e;
                    border-radius: 6px;
                }}

            </style>
        </head>

        <body>
            <h1>Student Service and Delay Analytics</h1>
            <p>Admin Dashboard</p>

            <h2>Request Summary</h2>

            <div class="cards">
                <div class="card">
                    <h3>Total Requests</h3>
                    <div class="number">{total_count}</div>
                </div>

                <div class="card">
                    <h3>Pending</h3>
                    <div class="number">{pending_count}</div>
                </div>

                <div class="card">
                    <h3>In Progress</h3>
                    <div class="number">{progress_count}</div>
                </div>

                <div class="card">
                    <h3>Resolved</h3>
                    <div class="number">{resolved_count}</div>
                </div>
            </div>

            <h2>Department-wise Workload and Resolution Time</h2>

            <p class="note">
                Compare service requests and resolution performance across
                departments.
            </p>

            <div class="table-container">
                <table>
                    <tr>
                        <th>Department</th>
                        <th>Total Requests</th>
                        <th>Pending</th>
                        <th>In Progress</th>
                        <th>Resolved</th>
                        <th>Average Resolution Time</th>
                    </tr>
                    {department_rows_html}
                </table>
          
            </div>

            <div class="chart-panel">
                <h3>Requests by Department and Status</h3>

                <div class="chart-legend">
                    <span>
                        <i class="legend-swatch pending-color"></i>
                        Pending
                    </span>
                    <span>
                        <i class="legend-swatch progress-color"></i>
                        In Progress
                    </span>
                    <span>
                        <i class="legend-swatch resolved-color"></i>
                        Resolved
                    </span>
                </div>

                {department_status_rows_html}
            </div>

            <div class="chart-panel">
                <h3>Average Resolution Time by Department</h3>

                <p class="note">
                    Lower values indicate faster average resolution.
                    Only departments with valid resolution-time data
                    are shown.
                </p>

                {resolution_chart_rows_html}
            </div>
            <input
    type="text"
    id="overdueSearch"
    placeholder="Search by ticket, student, service, department or status..."
    oninput="filterOverdueRows()"
    style="width:100%; max-width:520px; padding:10px;
           margin:12px 0; border:1px solid #ccc;
           border-radius:8px;"
>
            <h2>Overdue Requests</h2>


            <p class="note">
                Open requests that have remained Pending or In Progress
                for 7 or more days.
            </p>

            <div class="table-container">
                <table id="overdueTable">
                    <tr>
                        <th>Ticket No.</th>
                        <th>Student</th>
                        <th>Service</th>
                        <th>Department</th>
                        <th>Request Date</th>
                        <th>Days Open</th>
                        <th>Status</th>
                    </tr>
                    {overdue_rows_html}
                </table>
            </div>

            <h2>All Student Requests</h2>
            <input
    type="text"
    id="requestSearch"
    placeholder="Search all requests by ticket, student, service, department or status..."
    oninput="filterRequestRows()"
    style="width:100%; max-width:520px; padding:10px;
           margin:12px 0; border:1px solid #ccc;
           border-radius:8px;"
>
            <p>Total requests displayed: {len(requests_data)}</p>

            <div class="table-container">
                <table id="allRequestsTable">
                    <tr>
                        <th>Ticket No.</th>
                        <th>Student</th>
                        <th>Service</th>
                        <th>Department</th>
                        <th>Request Date</th>
                        <th>Status / Update</th>
                    </tr>
                    {rows_html}
                </table>
            </div>

        
<p><a href="/admin_logout">Admin Logout</a></p>
<p><a href="/">Back to Student Portal</a></p>
<script>
function filterOverdueRows() {{
    const input = document.getElementById("overdueSearch");
    const filter = input.value.toLowerCase().trim();
    const table = document.getElementById("overdueTable");
    const rows = table.getElementsByTagName("tr");

    for (let i = 1; i < rows.length; i++) {{
        const rowText = rows[i].innerText.toLowerCase();

        rows[i].style.display =
            rowText.includes(filter) ? "" : "none";
    }}
}}
function filterRequestRows() {{
    const input = document.getElementById("requestSearch");
    const filter = input.value.toLowerCase().trim();
    const table = document.getElementById("allRequestsTable");
    const rows = table.getElementsByTagName("tr");

    for (let i = 1; i < rows.length; i++) {{
        const rowText = rows[i].innerText.toLowerCase();

        rows[i].style.display =
            rowText.includes(filter) ? "" : "none";
    }}
}}
</script>
</body>

        </html>
        """

    except mysql.connector.Error as error:
        print("Admin dashboard error:", error)
        return "Unable to load dashboard. Check the VS Code terminal.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()

@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""

    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        password = request.form.get("password", "")

        if not student_name or not roll_number or not password:
            message = "Please fill in every field."
        elif len(password) < 6:
            message = "Password must contain at least 6 characters."
        else:
            connection = None
            cursor = None

            try:
                connection = get_db_connection()
                cursor = connection.cursor()

                cursor.execute(
                    "SELECT student_id FROM students "
                    "WHERE roll_number = %s",
                    (roll_number,)
                )

                if cursor.fetchone():
                    message = "This roll number is already registered."
                else:
                    password_hash = generate_password_hash(password)

                    cursor.execute(
                        "INSERT INTO students "
                        "(roll_number, student_name, password_hash) "
                        "VALUES (%s, %s, %s)",
                        (roll_number, student_name, password_hash)
                    )

                    connection.commit()
                    return redirect(url_for("student_login"))

            except Exception as error:
                if connection:
                    connection.rollback()
                print("Registration error:", error)
                message = "Registration failed. Check the terminal for details."

            finally:
                if cursor:
                    cursor.close()
                if connection and connection.is_connected():
                    connection.close()

    return """
    <h2>Student Registration</h2>
    <p style="color:red;">""" + escape(message) + """</p>
    <form method="POST">
        <label>Full name</label><br>
        <input name="student_name" required><br><br>

        <label>College roll number</label><br>
        <input name="roll_number" required><br><br>

        <label>Password (minimum 6 characters)</label><br>
        <input type="password" name="password" required minlength="6"><br><br>

        <button type="submit">Register</button>
    </form>
    <p>Already registered? <a href="/login">Student Login</a></p>
    """

@app.route("/login", methods=["GET", "POST"])
def student_login():
    message = ""

    if request.method == "POST":
        roll_number = request.form.get("roll_number", "").strip()
        password = request.form.get("password", "")

        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                "SELECT student_id, student_name, password_hash "
                "FROM students "
                "WHERE roll_number = %s AND is_active = 1",
                (roll_number,)
            )

            student = cursor.fetchone()

            if student and check_password_hash(
                student["password_hash"], password
            ):
                session.clear()
                session["student_id"] = student["student_id"]
                session["student_name"] = student["student_name"]
                session["role"] = "student"

                return redirect(url_for("home"))

            message = "Invalid roll number or password."

        except Exception as error:
            print("Login error:", error)
            message = "Login failed. Check the terminal for details."

        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    return """
    <h2>Student Login</h2>
    <p style="color:red;">""" + escape(message) + """</p>
    <form method="POST">
        <label>College roll number</label><br>
        <input name="roll_number" required><br><br>

        <label>Password</label><br>
        <input type="password" name="password" required><br><br>

        <button type="submit">Login</button>
    </form>
    <p>New student? <a href="/register">Register here</a></p>
    """


@app.route("/my_requests")
def my_requests():
    if session.get("role") != "student" or not session.get("student_id"):
        return redirect(url_for("student_login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT request_id, service_type, status, request_date
            FROM service_requests
            WHERE student_id = %s
            ORDER BY request_id DESC
            """,
            (session["student_id"],)
        )

        requests_list = cursor.fetchall()

        rows = ""
        for item in requests_list:
            rows += (
                "<tr>"
                f"<td>{item['request_id']}</td>"
                f"<td>{escape(str(item['service_type']))}</td>"
                f"<td>{escape(str(item['request_date']))}</td>"
                f"<td>{escape(str(item['status']))}</td>"
                "</tr>"
            )

        if not rows:
            rows = '<tr><td colspan="4">No requests submitted yet.</td></tr>'

        return (
            "<h2>My Requests</h2>"
            f"<p>Welcome, {escape(session.get('student_name', 'Student'))}!</p>"
            "<table border='1' cellpadding='8'>"
            "<tr><th>Request ID</th><th>Service Type</th>"
            "<th>Request Date</th><th>Status</th></tr>"
            + rows +
            "</table>"
            "<p><a href='/'>Submit another request</a></p>"
            "<p><a href='/logout'>Logout</a></p>"   
        )

    except mysql.connector.Error as error:
        print("My Requests error:", error)
        return "Could not load your requests. Check the VS Code terminal.", 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    message = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT admin_id, username, password_hash
                FROM admins
                WHERE username = %s AND is_active = 1
                """,
                (username,)
            )
            admin = cursor.fetchone()

            if admin and check_password_hash(
                admin["password_hash"], password
            ):
                session.clear()
                session["admin_id"] = admin["admin_id"]
                session["admin_username"] = admin["username"]
                session["role"] = "admin"

                return redirect(url_for("admin"))

            message = "Invalid username or password."

        except mysql.connector.Error:
            message = "Unable to check login. Please try again."

        finally:
            cursor.close()
            connection.close()

    return """
    <h2>Admin Login</h2>
    <form method="POST">
        <label>Username:</label>
        <input type="text" name="username" required><br><br>

        <label>Password:</label>
        <input type="password" name="password" required><br><br>

        <button type="submit">Login</button>
    </form>
    <p style="color:red;">""" + escape(message) + """</p>
    """

@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("welcome"))

@app.route("/welcome")
def welcome():
    if session.get("role") == "student":
        navigation = """
        <p><a href="/">Student Portal</a></p>
        <p><a href="/my_requests">My Requests</a></p>
        <p><a href="/logout">Student Logout</a></p>
        """

    elif session.get("role") == "admin":
        navigation = """
        <p><a href="/admin">Admin Dashboard</a></p>
        <p><a href="/admin_logout">Admin Logout</a></p>
        """

    else:
        navigation = """
        <p><a href="/login">Student Login</a></p>
        <p><a href="/register">New Student? Register Here</a></p>
        <p><a href="/admin_login">Admin Login</a></p>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Student Service and Delay Analytics</title>
    </head>
    <body>
        <h1>Student Service and Delay Analytics</h1>
        <p>Welcome to the Student Service Portal.</p>
        <h2>Choose an Option</h2>
        {navigation}
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)
