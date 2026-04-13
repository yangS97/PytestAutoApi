#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/22 13:45
# @Author : 余少琪
# @Description: MySQL 数据库操作封装
#
# 【文件作用】
# 封装 PyMySQL 数据库操作，支持：
# 1. MysqlDB 类：基础的数据库连接、查询、增删改
# 2. SetUpMySQL 类：处理前置 SQL（用例执行前的数据库操作）
# 3. AssertExecution 类：处理断言 SQL（用于数据库断言）
#
# 【类继承关系】
# MysqlDB（基类）
# ├── SetUpMySQL（前置 SQL 处理）
# └── AssertExecution（断言 SQL 处理）
#
# 【Java 对比说明】
# - pymysql.connect 类似于 Java 的 DriverManager.getConnection()
# - cursor 类似于 Java 的 Statement/PreparedStatement
# - __del__ 类似于 Java 的 close() 或 try-with-resources
from warnings import filterwarnings
import datetime
import decimal
import ast
import pymysql
from typing import List, Union, Text, Dict
from utils import config
from utils.logging_tool.log_control import ERROR
from utils.read_files_tools.regular_control import sql_regular, cache_regular
from utils.other_tools.exceptions import DataAcquisitionFailed, ValueTypeError

# 忽略 MySQL 告警信息（类似于 Java 的 Logger.setLevel(Level.OFF)）
filterwarnings("ignore", category=pymysql.Warning)


class MysqlDB:
    """
    MySQL 数据库基础操作封装

    核心职责：
    - 建立和关闭数据库连接
    - 执行查询 SQL（SELECT）
    - 执行增删改 SQL（INSERT/UPDATE/DELETE）
    - 处理特殊数据类型的转换

    Java 类比：
    public class MysqlDB {
        private Connection conn;
        private Statement cur;

        public MysqlDB() {
            this.conn = DriverManager.getConnection(...);
            this.cur = conn.createStatement();
        }

        public List<Map<String, Object>> query(String sql) { ... }
        public int execute(String sql) { ... }
    }
    """
    # 只在数据库开关开启时才初始化（类级别的条件判断）
    if config.mysql_db.switch:

        def __init__(self):
            """
            建立数据库连接

            Java 类比：
            Connection conn = DriverManager.getConnection(
                "jdbc:mysql://host:port/", user, password);
            Statement stmt = conn.createStatement();
            """
            try:
                # 建立数据库连接
                self.conn = pymysql.connect(
                    host=config.mysql_db.host,
                    user=config.mysql_db.user,
                    password=config.mysql_db.password,
                    port=config.mysql_db.port
                )

                # 使用 cursor 方法获取操作游标
                # cursor=pymysql.cursors.DictCursor 表示查询结果以字典形式返回
                # 类似于 Java 的 ResultSet 中通过列名取值
                self.cur = self.conn.cursor(cursor=pymysql.cursors.DictCursor)
            except AttributeError as error:
                ERROR.logger.error("数据库连接失败，失败原因 %s", error)

        def __del__(self):
            """
            析构方法 —— 对象销毁时自动关闭数据库连接

            类似于 Java 的：
            - try-with-resources 语句
            - 或 finally 块中的 conn.close()
            """
            try:
                # 关闭游标
                self.cur.close()
                # 关闭连接
                self.conn.close()
            except AttributeError as error:
                ERROR.logger.error("数据库连接失败，失败原因 %s", error)

        def query(self, sql, state="all"):
            """
            执行查询 SQL（SELECT）

            Args:
                sql: SQL 查询语句
                state: 查询模式
                       - "all": 查询全部（返回所有结果，默认值）
                       - 其他: 查询单条（返回第一条结果）

            Returns:
                - state="all": 返回所有查询结果（列表 of 字典）
                - state!= "all": 返回单条查询结果（字典）

            Java 类比：
            public List<Map<String, Object>> query(String sql) {
                ResultSet rs = stmt.executeQuery(sql);
                List<Map<String, Object>> results = new ArrayList<>();
                while (rs.next()) {
                    Map<String, Object> row = new HashMap<>();
                    // 填充 row
                    results.add(row);
                }
                return results;
            }
            """
            try:
                self.cur.execute(sql)

                if state == "all":
                    # 查询全部（fetchall 返回列表）
                    data = self.cur.fetchall()
                else:
                    # 查询单条（fetchone 返回单个字典）
                    data = self.cur.fetchone()
                return data
            except AttributeError as error_data:
                ERROR.logger.error("数据库连接失败，失败原因 %s", error_data)
                raise

        def execute(self, sql: Text):
            """
            执行增删改 SQL（INSERT/UPDATE/DELETE）

            Args:
                sql: SQL 语句

            Returns:
                int: 受影响的行数

            Java 类比：
            public int execute(String sql) {
                int rows = stmt.executeUpdate(sql);
                conn.commit();
                return rows;
            }
            """
            try:
                # 使用 execute 操作 SQL
                rows = self.cur.execute(sql)
                # 提交事务
                self.conn.commit()
                return rows
            except AttributeError as error:
                ERROR.logger.error("数据库连接失败，失败原因 %s", error)
                # 如果事务异常，则回滚数据
                self.conn.rollback()
                raise

        @classmethod
        def sql_data_handler(cls, query_data, data):
            """
            处理 SQL 查询结果中的特殊数据类型

            MySQL 返回的数据类型可能包含：
            - decimal.Decimal: 需要转为 float
            - datetime.datetime: 需要转为 str

            Args:
                query_data: 单条查询结果（字典）
                data: 数据池（累积合并的字典）

            Returns:
                Dict: 合并后的数据

            Java 类比：
            private Map<String, Object> handleSqlData(ResultSet rs, Map<String, Object> data) {
                for (String key : rs.getMetaData().getColumnNames()) {
                    Object value = rs.getObject(key);
                    if (value instanceof BigDecimal) {
                        data.put(key, ((BigDecimal) value).floatValue());
                    } else if (value instanceof Timestamp) {
                        data.put(key, value.toString());
                    }
                }
                return data;
            }
            """
            # 将 SQL 返回的所有内容全部放入对象中
            for key, value in query_data.items():
                if isinstance(value, decimal.Decimal):
                    data[key] = float(value)
                elif isinstance(value, datetime.datetime):
                    data[key] = str(value)
                else:
                    data[key] = value
            return data


class SetUpMySQL(MysqlDB):
    """
    前置 SQL 处理器

    在用例执行前，处理 setup_sql 中定义的 SQL 语句：
    - SELECT 语句：执行查询并将结果返回（用于后续断言）
    - INSERT/UPDATE/DELETE 语句：直接执行（用于准备测试数据）

    Java 类比：
    public class SetUpMySQL extends MysqlDB {
        public Map<String, Object> setupSqlData(List<String> sqlList) { ... }
    }
    """

    def setup_sql_data(self, sql: Union[List, None]) -> Dict:
        """
        处理前置请求 SQL

        【执行流程】
        1. 解析 SQL 列表
        2. 遍历每条 SQL：
           - SELECT 语句：执行查询并返回结果
           - 其他语句：直接执行（增删改）
        3. 将所有查询结果合并为一个字典返回

        Args:
            sql: SQL 语句列表

        Returns:
            Dict: 所有 SELECT 查询结果的合并

        Raises:
            DataAcquisitionFailed: 如果 SQL 查询失败（无结果返回）
        """
        sql = ast.literal_eval(cache_regular(str(sql)))
        try:
            data = {}
            if sql is not None:
                for i in sql:
                    # 判断 SQL 语句类型是否为查询
                    if i[0:6].upper() == 'SELECT':
                        # 执行查询并获取第一行结果
                        sql_date = self.query(sql=i)[0]
                        for key, value in sql_date.items():
                            data[key] = value
                    else:
                        # 执行增删改 SQL
                        self.execute(sql=i)
            return data
        except IndexError as exc:
            raise DataAcquisitionFailed("sql 数据查询失败，请检查setup_sql语句是否正确") from exc


class AssertExecution(MysqlDB):
    """
    断言 SQL 执行器

    专门用于处理数据库断言场景下的 SQL 查询：
    - 只支持 SELECT 语句（断言只需要查询数据）
    - 支持多条 SELECT 语句同时执行
    - 支持在 SQL 中引用接口响应数据（$json()$ 语法）

    Java 类比：
    public class AssertExecution extends MysqlDB {
        public Map<String, Object> assertExecution(List<String> sqlList, ResponseData resp) { ... }
    }
    """

    def assert_execution(self, sql: list, resp) -> dict:
        """
        执行断言 SQL

        【执行流程】
        1. 校验 SQL 数据类型必须是 list
        2. 校验 SQL 语句中不能包含增删改语句
        3. 遍历每条 SELECT 语句：
           - 解析 SQL 中的 JSON 引用（$json()$）
           - 执行查询
           - 处理特殊数据类型
           - 合并到结果字典中

        Args:
            sql: SQL 语句列表（只能是 SELECT）
            resp: 接口响应数据（用于解析 SQL 中的 JSON 引用）

        Returns:
            dict: 所有 SQL 查询结果的合并

        Raises:
            DataAcquisitionFailed: 如果查询失败或 SQL 类型不正确
            ValueTypeError: 如果传入的不是 list
        """
        try:
            if isinstance(sql, list):
                data = {}
                _sql_type = ['UPDATE', 'update', 'DELETE', 'delete', 'INSERT', 'insert']
                # 断言 SQL 不能包含增删改语句
                if any(i in sql for i in _sql_type) is False:
                    for i in sql:
                        # 判断 SQL 中是否有正则引用（$json()$），如果有则通过 JSONPath 提取相关数据
                        sql = sql_regular(i, resp)
                        if sql is not None:
                            # for 循环逐条处理断言 SQL
                            query_data = self.query(sql)[0]
                            data = self.sql_data_handler(query_data, data)
                        else:
                            raise DataAcquisitionFailed(f"该条sql未查询出任何数据, {sql}")
                else:
                    raise DataAcquisitionFailed("断言的 sql 必须是查询的 sql")
            else:
                raise ValueTypeError("sql数据类型不正确，接受的是list")
            return data
        except Exception as error_data:
            ERROR.logger.error("数据库连接失败，失败原因 %s", error_data)
            raise error_data


if __name__ == '__main__':
    a = MysqlDB()
    b = a.query(sql="select * from `test_obp_configure`.lottery_prize where activity_id = 3")
    print(b)
