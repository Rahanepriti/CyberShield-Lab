import sqlite3                  

connection = sqlite3.connect("users.db")

cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT ,
username TEXT NOT NULL,
email TEXT NOT NULL,
password TEXT NOT NULL
)
""")

cursor.execute("""
INSERT INTO users (username,email, password)
VALUES(?,?,?)
""" , ("Priti","priti@gmail.com","Password123"))

connection.commit()

connection.close()
print("User Inserted Successfully !")
