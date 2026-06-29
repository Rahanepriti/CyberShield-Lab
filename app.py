from werkzeug.security import generate_password_hash , check_password_hash
import sqlite3 
from flask import Flask , render_template, request ,session ,redirect,url_for
app = Flask(__name__)
app.secret_key ="cybershield-secret-key"

@app.route("/")
def home():
    return render_template("index.html")
    
@app.route("/about")
def about():
    return render_template("about.html")
    
@app.route("/contact")
def contact():
    return render_template("contact.html")
    
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html") 
        
    username = request.form["username"]
    password = request.form["password"]
    
    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT password FROM users WHERE username = ?",
        (username,)
    )

    user = cursor.fetchone()
    print("User from DB :" ,user)
    print("Entered Password :" ,password)

    connection.close()
    print("Password Match :",check_password_hash(user[0],password) if user else "NO User Found")
    if user and check_password_hash(user[0], password):
        session["username"] = username
        return redirect(url_for("dashboard"))

    return "❌ Invalid Username or Password"
    
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
        INSERT INTO users (username, email, password)
        VALUES (?, ?, ?)
    """, (username, email, hashed_password))

    connection.commit()
    connection.close()

    return "✅ Registration Successful!"
    
    
@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )
    
    

@app.route("/logout")
def logout():

    session.pop("username", None)

    return redirect(url_for("login")) 
if __name__ == "__main__":
    app.run(debug=True)
