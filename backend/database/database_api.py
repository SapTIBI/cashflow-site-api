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
            cursor.execute(get_account_query, (login, password))
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
            cursor.execute(create_account_query, (name, login, hash_password))
            account_id = cursor.fetchone().get('id')
            conn.commit()
    except Error as e:
        conn.rollback()
        raise DatabaseError('Database Error!')
    return account_id


def create_wallet_account(account_id, data):
    data['account_id'] = account_id
    create_wallet_account_query = sql.SQL(
    """
        INSERT INTO public.wallet ({keys})
        VALUES ({values})
        RETURNING 
            id as wallet_id,
            title as wallet_title,
            balance as wallet_balance,
            description as wallet_description;
    """
    ).format(keys=sql.SQL(', ').join(sql.Identifier(key) for key in data.keys()),
             values=sql.SQL(', ').join(sql.Placeholder(key) for key in data.keys()))
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(create_wallet_account_query, data)
            wallet = cursor.fetchone()
            conn.commit()
    except Error as e:
        conn.rollback()
        raise DatabaseError('Database Error!')
    return wallet


def delete_wallet_account(account_id, wallet_id):
    delete_wallet_account_query = sql.SQL(
    """
        DELETE FROM public.wallet
        WHERE id = %s AND account_id = %s
        RETURNING id;
    """
    )
    deleted_rows  = 0
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(delete_wallet_account_query, (wallet_id, account_id))
            deleted_rows  = cursor.rowcount
            conn.commit()
    except Error as e:
        conn.rollback()
        raise DatabaseError('Database Error!')
    return deleted_rows

def update_wallet_account(account_id, wallet_id, data):
    update_wallet_account_query = sql.SQL(
    """
        UPDATE public.wallet
        SET {data} 
        WHERE id = {id} AND account_id = {account_id}
        RETURNING 
            id as wallet_id,
            title as wallet_title,
            balance as wallet_balance,
            description as wallet_description;
    """)
    wallet_information = None
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            dynamic_query = update_wallet_account_query.format(
                                    data=sql.SQL(', ').join(
                                        sql.Composed([sql.Identifier(k), sql.SQL(" = "), sql.Placeholder(k)]) for k in data.keys()
                                    ),
                                    id=sql.Placeholder('id'),
                                    account_id=sql.Placeholder('account_id')
            )   
            data['id'] = wallet_id
            data['account_id'] = account_id
            cursor.execute(dynamic_query, data)
            wallet_information  = cursor.fetchone()
            conn.commit()
    except Error as e:
        conn.rollback()
        raise DatabaseError('Database Error!')
    return wallet_information


def get_wallet_account(account_id, wallet_id):
    get_wallet_account_query = sql.SQL(
    """
        SELECT 
        wl.id as wallet_id,
        wl.balance as wallet_balance,
        wl.title as wallet_title,
        wl.description as wallet_description
        FROM wallet wl
        WHERE wl.id = %s AND wl.account_id = %s LIMIT 1;
    """)
    wallet_information = None
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(get_wallet_account_query, (wallet_id, account_id))
            wallet_information  = cursor.fetchone()
            conn.commit()
    except Error as e:
        conn.rollback()
        raise DatabaseError('Database Error!')
    return wallet_information