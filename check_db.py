import mysql.connector
from mysql.connector import errorcode

config = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',
}

db_name = 'student_management'

try:
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    
    try:
        cursor.execute(f"CREATE DATABASE {db_name}")
        print(f"Database {db_name} created successfully.")
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_DB_CREATE_EXISTS:
            print(f"Database {db_name} already exists.")
        else:
            print(f"Failed creating database: {err}")
            exit(1)
    
    cnx.close()
    print("MySQL connection and database setup verified.")

except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)
    exit(1)
