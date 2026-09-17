import pyodbc
from config_db import DB_CONNECTION_STRING

try:
    conn = pyodbc.connect(DB_CONNECTION_STRING, autocommit=True)
    cur = conn.cursor()
    cur.execute("SELECT @@SERVERNAME, DB_NAME(), SUSER_NAME()")
    row = cur.fetchone()
    print(f"Сервер:       {row[0]}")
    print(f"База:         {row[1]}")
    print(f"Пользователь: {row[2]}")
    conn.close()
    print("✅ Подключение работает")
except Exception as e:
    print(f"❌ Ошибка: {e}")