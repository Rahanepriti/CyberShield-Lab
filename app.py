from PIL import Image
import uuid
import logging
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash , check_password_hash
from flask_jwt_extended import ( 
    JWTManager, 
    create_access_token, 
    jwt_required, 
    get_jwt_identity,
    get_jwt
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3 
import subprocess
import ipaddress
from werkzeug.exceptions import RequestEntityTooLarge
from flask import Flask , render_template, request ,session ,redirect,url_for ,jsonify
app = Flask(__name__)
import os
UPLOAD_FOLDER = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

logging.basicConfig(
    filename="logs/security.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app.secret_key ="cybershield-secret-key"
app.config["JWT_SECRET_KEY"] = "super-secret-jwt-key-change-this"
jwt = JWTManager(app)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Enable this only when using HTTPS
# app.config["SESSION_COOKIE_SECURE"] = True


csrf = CSRFProtect(app)

@app.route("/")
def home():

    if "username" in session:
        return redirect(url_for("soc_dashboard"))

    return redirect(url_for("login"))
    
@app.route("/about")
def about():
    return render_template("about.html")
    
@app.route("/contact")
def contact():
    return render_template("contact.html")
    
@csrf.exempt    
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    username = request.form["username"]
    password = request.form["password"]

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id , password, role, failed_attempts, locked_until
        FROM users
        WHERE username = ?
    """, (username,))

    user = cursor.fetchone()

    # User not found
    if not user:
        connection.close()
        logging.warning(f"LOGIN FAILED - Unknown User: {username}")
        return "❌ Invalid Username or Password"
        
        
    user_id = user[0]
    stored_password = user[1]
    role = user[2]
    failed_attempts = user[3]
    locked_until = user[4]

    # Check if account is locked
    if locked_until:
        unlock_time = datetime.fromisoformat(locked_until)

        if datetime.now() < unlock_time:
            connection.close()
            return f"🚫 Account locked until {unlock_time}"

    # Check password
    if check_password_hash(stored_password, password):

        # Reset failed attempts
        cursor.execute("""
            UPDATE users
            SET failed_attempts = 0,
                locked_until = NULL
            WHERE username = ?
        """, (username,))

        connection.commit()
        connection.close()

        session["user_id"] = user_id
        session["username"] = username
        session["role"] = role

        logging.info(f"LOGIN SUCCESS - User: {username}")

        return redirect(url_for("soc_dashboard"))

    # Wrong password
    failed_attempts += 1

    if failed_attempts >= 5:

        lock_time = datetime.now() + timedelta(minutes=15)

        cursor.execute("""
            UPDATE users
            SET failed_attempts = ?,
                locked_until = ?
            WHERE username = ?
        """, (
            failed_attempts,
            lock_time.isoformat(),
            username
        ))

        connection.commit()
        connection.close()

        logging.warning(f"ACCOUNT LOCKED - User: {username}")

        return "🚫 Account locked for 15 minutes."

    else:

        cursor.execute("""
            UPDATE users
            SET failed_attempts = ?
            WHERE username = ?
        """, (
            failed_attempts,
            username
        ))

        connection.commit()
        connection.close()

        logging.warning(f"LOGIN FAILED - User: {username}")

        return f"❌ Invalid Username or Password ({failed_attempts}/5 attempts)"
        
@csrf.exempt 
@app.route("/api/login", methods=["POST"])
@limiter.limit("2 per minute")
def api_login():

    username = request.json.get("username")
    password = request.json.get("password")

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT password, role
        FROM users
        WHERE username = ?
    """, (username,))

    user = cursor.fetchone()

    connection.close()

    if not user:
        return jsonify({
            "success": False,
            "message": "Invalid username or password"
        }), 401

    if not check_password_hash(user[0], password):
        return jsonify({
            "success": False,
            "message": "Invalid username or password"
        }), 401

    access_token = create_access_token(
         identity=username,
         additional_claims={
            "role": user[1]
         }
    )

    return jsonify({
        "access_token": access_token
    }), 200
    
        
    
@csrf.exempt    
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    hashed_password = generate_password_hash(password)
    
    if not username or not email or not password:
        return "All fields are required !"

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO users (username, email, password ,role)
        VALUES (?, ?, ?,?)
    """, (username, email, hashed_password, "user"))

    connection.commit()
    connection.close()

    return "✅ Registration Successful!"
    
    
@app.route("/profile")
def profile():

    if "username" not in session:
        return redirect(url_for("login"))

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT email FROM users WHERE username=?",
        (session["username"],)
    )

    email = cursor.fetchone()[0]

    connection.close()

    return render_template(
        "profile.html",
        username=session["username"],
        email=email
    )
    
    
@app.route("/update-email", methods=["POST"])
def update_email():

    if "username" not in session:
        return redirect(url_for("login"))

    new_email = request.form["email"]

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE users
        SET email=?
        WHERE username=?
        """,
        (new_email, session["username"])
    )

    connection.commit()
    connection.close()

    return redirect(url_for("profile"))
    
@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )
    
    
@app.route("/soc-dashboard")
def soc_dashboard():

    if "username" not in session:
        return redirect(url_for("login"))

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Count uploaded files
    upload_folder = "uploads"

    if os.path.exists(upload_folder):
        total_uploads = len(os.listdir(upload_folder))
    else:
        total_uploads = 0

    connection.close()

    logs = []

    success_logins = 0
    failed_logins = 0

    try:
        with open("logs/security.log", "r") as file:

            logs = file.readlines()

            for line in logs:

                if "LOGIN SUCCESS" in line:
                    success_logins += 1

                if "LOGIN FAILED" in line:
                    failed_logins += 1

            logs = logs[-20:]
            logs.reverse()

    except FileNotFoundError:

        logs = ["No logs found."]

    return render_template(
        "soc_dashboard.html",
        total_users=total_users,
        total_uploads=total_uploads,
        success_logins=success_logins,
        failed_logins=failed_logins,
        logs=logs
    )
    
@app.route("/users")
def view_users():

    if "username" not in session:
        return redirect(url_for("login"))
        
    if session["role"] != "admin":
        return "Access Denied ! Admins Only ."

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT username, email
        FROM users
    """)

    users = cursor.fetchall()

    connection.close()

    return render_template(
        "users.html",
        users=users
    )  
    
    
    
#API
@csrf.exempt
@app.route("/api/users", methods=["GET"])
@jwt_required()
def api_users():

    current_user = get_jwt_identity()
    claims = get_jwt()
    
    if claims["role"] != "admin":
       return jsonify({
          "message": "Access Denied"
       }), 403

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, username, email, role
        FROM users
    """)

    users = cursor.fetchall()

    connection.close()

    result = []

    for user in users:
        result.append({
            "id": user[0],
            "username": user[1],
            "email": user[2],
            "role": user[3]
        })

    return jsonify({
        "logged_in_as": current_user,
        "role": claims["role"],
        "users": result
    })


@app.route("/api/user/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user(user_id):

    current_user = get_jwt_identity()
    claims = get_jwt()

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    # Find logged-in user's ID
    cursor.execute("""
        SELECT id
        FROM users
        WHERE username = ?
    """, (current_user,))

    logged_in = cursor.fetchone()

    if not logged_in:
        connection.close()
        return jsonify({"message": "User not found"}), 404

    logged_in_id = logged_in[0]

    # If not admin, user can only access their own profile
    if claims["role"] != "admin" and logged_in_id != user_id:
        connection.close()
        return jsonify({
            "message": "Access Denied"
        }), 403

    cursor.execute("""
        SELECT id, username, email, role
        FROM users
        WHERE id = ?
    """, (user_id,))

    user = cursor.fetchone()

    connection.close()

    if not user:
        return jsonify({
            "message": "User not found"
        }), 404

    return jsonify({
        "id": user[0],
        "username": user[1],
        "email": user[2],
        "role": user[3]
    })

    
@csrf.exempt    
@app.route("/search-user", methods=["GET", "POST"])
def search_user():

    if request.method == "GET":
        return render_template("search_user.html")

    username = request.form["username"]

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute(
    """
    SELECT username, email, role
    FROM users
    WHERE username = ?
    """,
    (username,)
)


    users = cursor.fetchall()

    connection.close()

    return render_template("search_user.html", users=users)
    
    
    
@app.route("/messages", methods=["GET", "POST"])
def messages():

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    if request.method == "POST":

        username = session["username"]
        message = request.form["message"]

        cursor.execute("""
            INSERT INTO messages(username, message)
            VALUES (?, ?)
        """, (username, message))

        connection.commit()

    cursor.execute("""
        SELECT username, message
        FROM messages
        ORDER BY id DESC
    """)

    messages = cursor.fetchall()

    connection.close()

    return render_template("messages.html", messages=messages)
    
    
@app.route("/security-labs")
def security_labs():
    return render_template("security_labs.html")
    
    
    
@app.route("/user/<int:user_id>")
def view_user(user_id):
    
    if session["role"] != "admin" and session["user_id"] != user_id:
         return "🚫 Access Denied"

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, username, email, role
        FROM users
        WHERE id = ?
    """, (user_id,))

    user = cursor.fetchone()

    connection.close()

    return render_template("view_user.html", user=user)
    
def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )
    
   
@csrf.exempt  
@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "POST":

        file = request.files["file"]

        if not allowed_file(file.filename):
            return render_template(
               "upload.html",
               message="❌ Only JPG, JPEG and PNG files are allowed."
            )

        filename = secure_filename(file.filename)

        extension = filename.rsplit(".", 1)[1].lower()

        filename = f"{uuid.uuid4()}.{extension}"

        try:
            image = Image.open(file)
            image.verify()

        except Exception:
             return render_template(
                "upload.html",
                message="❌ Invalid image file."
             )

        file.seek(0)

        file.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )
        )

        return render_template(
            "upload.html",
            message="✅ File uploaded successfully."
       )

    return render_template("upload.html")
    
@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    return "❌ File size exceeds 2 MB.", 413
    
    

@app.route("/ping", methods=["GET", "POST"])
def ping():

    output = ""

    if request.method == "POST":

        ip = request.form["ip"]

        try:
            # Validate that the input is a valid IP address
            ipaddress.ip_address(ip)

            result = subprocess.run(
                ["ping", "-c", "2", ip],
                capture_output=True,
                text=True,
                check=False
            )

            output = result.stdout + result.stderr

        except ValueError:
            output = "❌ Invalid IP address."

    return render_template("ping.html", output=output)
    
    
    
@app.route("/api/profile")
def api_profile():

    if "username" not in session:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT username,email,role
        FROM users
        WHERE username = ?
    """,
    (session["username"],))

    user = cursor.fetchone()

    connection.close()

    return jsonify({

        "username": user[0],
        "email": user[1],
        "role": user[2]

    })


@app.route("/logout")
def logout():
  #logout logs
    username = session.get("username")
    logging.info(f"LOGOUT - User: {username}")
    #session end
    session.pop("username", None)

    return redirect(url_for("login")) 
    
@app.after_request
def add_security_headers(response):

    response.headers["X-Frame-Options"] = "DENY"

    response.headers["X-Content-Type-Options"] = "nosniff"

    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:;"
    )

    return response
if __name__ == "__main__":
    app.run(debug=True)
