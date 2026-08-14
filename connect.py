import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="portfolio_tracker",
    user="postgres",
    password="Thejas12*"
)

print("Connected successfully!")
cursor = conn.cursor()

cursor.execute("SELECT * FROM stocks")

rows = cursor.fetchall()

for row in rows:
    print(row)

cursor.close()


conn.close()