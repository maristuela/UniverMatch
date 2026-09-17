# config.py


# config.py

# --- SQL Server ---
DB_DRIVER = "ODBC Driver 17 for SQL Server"     # или "ODBC Driver 18 for SQL Server"
DB_SERVER = r"localhost\MyDB"                    # экземпляр MyDB
DB_NAME = "UniverMatchDB"                             # имя вашей БД

# Windows-аутентификация (без логина/пароля)
DB_CONNECTION_STRING = (
    f"DRIVER={{{DB_DRIVER}}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    "Trusted_Connection=yes;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

# DB_DRIVER = "ODBC Driver 17 for SQL Server"
# DB_SERVER = "localhost\MyDB"           # или "localhost\\SQLEXPRESS"
# DB_NAME = "UniverMatchDB"
# DB_USER = "sa"                    # ваш логин
# DB_PASSWORD = "Stumaria2005!"
#
# DB_CONNECTION_STRING = (
#     f"DRIVER={{{DB_DRIVER}}};"
#     f"SERVER={DB_SERVER};"
#     f"DATABASE={DB_NAME};"
#     "Trusted_Connection=yes;"
#     "TrustServerCertificate=yes;"
# )