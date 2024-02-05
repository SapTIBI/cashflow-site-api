from psycopg2 import connect, sql, extras, Error
from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USERNAME


class DatabaseError(Exception):
    pass

def get_database_connection():
    connection = connect(database=DB_NAME,
                        user=DB_USERNAME,
                        password=DB_PASSWORD,
                        host=DB_HOST,
                        port=DB_PORT)
    return connection


def get_account_by_id(id):
    get_account_query = sql.SQL("""
        SELECT 
        ac.id as account_id,
        ac.name as account_name, 
        ac.login as account_login,
        ac.password as account_password
        FROM account ac
        WHERE ac.id = %s LIMIT 1;
    """)
    account = None
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(get_account_query, (id, ))
            account = cursor.fetchone()
    except Error as e:
        raise DatabaseError('Database Error!')
    return account
    

def get_account_by_login(login):
    get_account_query = sql.SQL(
    """
        SELECT 
        ac.id as account_id,
        ac.name as account_name,
        ac.login as account_login,
        ac.password as account_password
        FROM account ac
        WHERE ac.login = %s LIMIT 1;
    """)
    account = None
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(get_account_query, (login, ))
            account = cursor.fetchone()
    except Error as e:
        raise DatabaseError('Database Error!')
    return account


def get_account_by_login_and_password(login, password):
    get_account_query = sql.SQL(
    """
        SELECT 
        ac.id as account_id,
        ac.name as account_name,
        ac.login as account_login,
        ac.password as account_password
        FROM account ac
        WHERE ac.login = %s AND ac.password = %s LIMIT 1;
    """)
    account = None
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(get_account_query, (login, password, ))
            account = cursor.fetchone()
    except Error as e:
        raise DatabaseError('Database Error!')
    return account


def login_new_account(name, login, hash_password):
    create_account_query = sql.SQL(
    """
        INSERT INTO account (name, login, password)
        VALUES (%s, %s, %s)
        RETURNING id;
    """)
    account_id = None
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(create_account_query, (name, login, hash_password, ))
            account_id = cursor.fetchone().get('id')
            conn.commit()
    except Error as e:
        conn.rollback()
        raise DatabaseError('Database Error!')
    return account_id
