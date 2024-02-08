import psycopg2
from psycopg2 import sql, extras, Error
from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USERNAME
from werkzeug.security import check_password_hash, generate_password_hash



class DatabaseError(Exception):
    """Ошибка, возникающая при работе с БД"""
    pass

class DuplicatedInformationError(DatabaseError):
    """Ошибка, возникающая при попытке создания сущности с уже существующими похожими данными"""
    pass

class IncorrectCredentialsError(DatabaseError):
    """Ошибка, возникающая если сущность с такими данными не существует"""
    pass

class NoResultDataError(DatabaseError):
    """Ошибка, возникающая если сущность с такими данными не существует"""
    pass


def get_database_connection():
    connection = psycopg2.connect(database=DB_NAME,
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


def get_account_by_credentials(account_credentials):
    print(account_credentials)
    get_account_query = sql.SQL(
    """
        SELECT 
        ac.id as account_id,
        ac.name as account_name,
        ac.login as account_login,
        ac.password as account_password
        FROM account ac
        WHERE ac.login = %s;
    """)
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(get_account_query, (account_credentials.get('login'), ))
            account = cursor.fetchone()
            print(account)
            if not account:
                raise IncorrectCredentialsError('Incorrect account login!')
            if not check_password_hash(account.get('account_password'), account_credentials.get('password')):
                raise IncorrectCredentialsError('Incorrect account password!')
            del account['account_password']
    except Error as e:
        print(e)
        raise DatabaseError('Database Error!')
    return account


def login_new_account(account_data):
    create_account_query = sql.SQL(
    """
        INSERT INTO account (name, login, password)
        VALUES (%s, %s, %s)
        RETURNING 
            id as account_id,
            name as account_name,
            login as account_login;
    """)
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            name = account_data.get('name')
            login = account_data.get('login')
            hashed_password = generate_password_hash(account_data.get('password'))
            cursor.execute(create_account_query, (name, login, hashed_password))
            account = cursor.fetchone()
            conn.commit()
    except psycopg2.errors.UniqueViolation as e:
        conn.rollback()
        raise DuplicatedInformationError('Account with this login already exist!')
    except Error as e:
        conn.rollback()
        raise DatabaseError('Database Error!')
    return account


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
    wallet = None
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
    if not deleted_rows:
        raise NoResultDataError('Wallets not found')
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
    except Error as e:
        raise DatabaseError('Database Error!')
    if not wallet_information:
        raise NoResultDataError('Wallets not found')
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
    except Error as e:
        raise DatabaseError('Database Error!')
    if not wallet_information:
        raise NoResultDataError('Wallets not found')
    return wallet_information


def get_wallets_account(account_id):
    get_wallets_account_query = sql.SQL(
    """
        SELECT 
        wl.id as wallet_id,
        wl.balance as wallet_balance,
        wl.title as wallet_title,
        wl.description as wallet_description
        FROM wallet wl
        WHERE wl.account_id = %s;
    """)
    wallets_information = None
    try:
        with get_database_connection() as conn, conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(get_wallets_account_query, (account_id,  ))
            wallets_information  = cursor.fetchall()
    except Error as e:
        raise DatabaseError('Database Error!')
    if not wallets_information:
        raise NoResultDataError('Wallets not found')
    return wallets_information