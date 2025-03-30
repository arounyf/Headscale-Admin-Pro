from flask_sqlalchemy import  SQLAlchemy
from sqlalchemy import event
db = SQLAlchemy()

def enable_sqlite_foreign_keys(db_engine):
    @event.listens_for(db_engine, 'connect')
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()


