# -*- coding:utf-8 -*-
import sqlite3
import traceback
import config_loader

# 直接从配置文件导入数据库 URI
DATABASE = config_loader.DATABASE_URI


class SqliteDB(object):

    def __init__(self, database=DATABASE, isolation_level='', ignore_exc=False):
        self.database = database
        self.isolation_level = isolation_level
        self.ignore_exc = ignore_exc
        self.connection = None
        self.cursor = None

    def __enter__(self):
        try:
            self.connection = sqlite3.connect(database=self.database, isolation_level=self.isolation_level)
            self.cursor = self.connection.cursor()
            self.cursor.row_factory = sqlite3.Row  # 设置返回类似字典的对象
            # 开启外键约束
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            return self.cursor
        except Exception as ex:
            traceback.print_exc()
            raise ex

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if not exc_type is None:
                self.connection.rollback()
                return self.ignore_exc
            else:
                self.connection.commit()
        except Exception as ex:
            traceback.print_exc()
            raise ex
        finally:
            self.cursor.close()
            self.connection.close()