import sqlite3 
connection = sqlite3.connect("users.db")
cursor = connection.cursor()

cursor.execute("SELECT * FROM users")

users = cursor.fetchall()

for user in users:
    print(user)
    
connection.close()
