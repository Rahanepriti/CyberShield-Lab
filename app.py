from flask import Flask , render_template, request
app = Flask(__name__)

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
    
    return f"""
    Username: {username}<br>
    Password: {password}
    """
    
if __name__ == "__main__":
    app.run(debug=True)
