#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2021/11/26 18:27
# @Author : 余少琪
# @Description: 动态表达式解析器
#
# 【文件作用】
# 这是框架中非常核心的一个模块。负责解析 YAML 用例中的各种动态表达式，
# 将其替换为实际的值。支持的表达式包括：
#
# 1. ${{function()}} —— 自定义函数调用
#    示例：${{random_int()}}、${{host()}}、${{get_phone()}}
#
# 2. $cache{key} —— 从缓存中读取数据
#    示例：$cache{auth_token}、$cache{int:userId}
#
# 3. $json(path)$ —— 从响应 JSON 中提取数据（SQL 中使用）
#    示例：$json($.data.id)$
#
# 【Java 对比说明】
# - 类似于 Java 中的模板引擎（如 Thymeleaf/FreeMarker）
# - getattr(Context(), func_name) 类似于 Java 的反射 Method.invoke()
# - re.sub 类似于 Java 的 Matcher.replaceAll()
import re
import datetime
import random
from datetime import date, timedelta, datetime
from jsonpath import jsonpath
from faker import Faker
from utils.logging_tool.log_control import ERROR


class Context:
    """
    上下文数据生成器 —— 提供各种动态函数供 YAML 用例调用

    这个类中的所有方法都可以通过 ${{方法名()}} 语法在 YAML 中调用。

    Java 类比：
    public class Context {
        private Faker faker = new Faker(new Locale("zh_CN"));

        public int randomInt() { return random.nextInt(5000); }
        public String getPhone() { return faker.phoneNumber().cellPhone(); }
        // ...
    }
    """
    def __init__(self):
        # Faker 是一个生成虚假数据的库（类似于 Java 的 java-faker）
        # locale='zh_CN' 表示生成中国格式的数据（中文姓名、中国手机号等）
        self.faker = Faker(locale='zh_CN')

    @classmethod
    def random_int(cls) -> int:
        """
        生成 0-5000 之间的随机整数

        YAML 调用方式：${{random_int()}}

        Returns:
            int: 随机整数
        """
        _data = random.randint(0, 5000)
        return _data

    def get_phone(self) -> int:
        """
        随机生成中国手机号码

        YAML 调用方式：${{get_phone()}}

        Returns:
            str: 手机号码
        """
        phone = self.faker.phone_number()
        return phone

    def get_id_number(self) -> int:
        """
        随机生成中国身份证号码

        YAML 调用方式：${{get_id_number()}}

        Returns:
            str: 身份证号码
        """
        id_number = self.faker.ssn()
        return id_number

    def get_female_name(self) -> str:
        """
        随机生成女性中文姓名

        YAML 调用方式：${{get_female_name()}}

        Returns:
            str: 女性姓名
        """
        female_name = self.faker.name_female()
        return female_name

    def get_male_name(self) -> str:
        """
        随机生成男性中文姓名

        YAML 调用方式：${{get_male_name()}}

        Returns:
            str: 男性姓名
        """
        male_name = self.faker.name_male()
        return male_name

    def get_email(self) -> str:
        """
        随机生成邮箱地址

        YAML 调用方式：${{get_email()}}

        Returns:
            str: 邮箱地址
        """
        email = self.faker.email()
        return email

    @classmethod
    def self_operated_id(cls):
        """
        返回自营店铺 ID（固定值）

        YAML 调用方式：${{self_operated_id()}}

        Returns:
            int: 自营店铺 ID（固定值 212）
        """
        operated_id = 212
        return operated_id

    @classmethod
    def get_time(cls) -> str:
        """
        获取当前时间（格式：YYYY-MM-DD HH:mm:ss）

        YAML 调用方式：${{get_time()}}

        Returns:
            str: 当前时间字符串
        """
        now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return now_time

    @classmethod
    def today_date(cls):
        """
        获取今日 0 点整的时间

        YAML 调用方式：${{today_date()}}

        Returns:
            str: 今日 0 点时间（格式：YYYY-MM-DD 00:00:00）
        """
        _today = date.today().strftime("%Y-%m-%d") + " 00:00:00"
        return str(_today)

    @classmethod
    def time_after_week(cls):
        """
        获取一周后 0 点整的时间

        YAML 调用方式：${{time_after_week()}}

        Returns:
            str: 一周后的时间（格式：YYYY-MM-DD 00:00:00）
        """
        _time_after_week = (date.today() + timedelta(days=+6)).strftime("%Y-%m-%d") + " 00:00:00"
        return _time_after_week

    @classmethod
    def host(cls) -> str:
        """
        获取配置中的主服务地址

        YAML 调用方式：${{host()}}

        Returns:
            str: 主服务地址（从 config.yaml 中读取）
        """
        from utils import config
        return config.host

    @classmethod
    def app_host(cls) -> str:
        """
        获取配置中的应用服务地址

        YAML 调用方式：${{app_host()}}

        Returns:
            str: 应用服务地址（从 config.yaml 中读取）
        """
        from utils import config
        return config.app_host


def sql_json(js_path, res):
    """
    从响应 JSON 中提取数据供 SQL 使用

    Args:
        js_path: JSONPath 表达式
        res: 响应 JSON 数据

    Returns:
        提取到的值

    Raises:
        ValueError: 如果 JSONPath 提取失败
    """
    _json_data = jsonpath(res, js_path)[0]
    if _json_data is False:
        raise ValueError(f"sql中的jsonpath获取失败 {res}, {js_path}")
    return jsonpath(res, js_path)[0]


def sql_regular(value, res=None):
    """
    解析 SQL 语句中的 JSON 数据引用

    在 SQL 中可以使用 $json(path)$ 语法引用响应 JSON 中的数据。
    这个方法会将这些引用替换为实际的值。

    Args:
        value: SQL 语句（可能包含 $json()$ 引用）
        res: 响应 JSON 数据（用于 JSONPath 提取）

    Returns:
        str: 替换后的 SQL 语句

    示例：
    DELETE FROM user WHERE id = $json($.data.id)$
    -> DELETE FROM user WHERE id = 123
    """
    # 正则匹配所有的 $json(...) 表达式
    sql_json_list = re.findall(r"\$json\((.*?)\)\$", value)

    for i in sql_json_list:
        # 构建正则表达式模式（转义特殊字符）
        pattern = re.compile(r'\$json\(' + i.replace('$', "\$").replace('[', '\[') + r'\)\$')
        # 提取 JSON 数据
        key = str(sql_json(i, res))
        # 替换 SQL 中的表达式为实际值
        value = re.sub(pattern, key, value, count=1)

    return value


def cache_regular(value):
    """
    通过正则解析 YAML 用例中的缓存引用

    在 YAML 用例中可以使用 $cache{key} 语法引用之前存储的缓存数据。
    这个方法会将这些引用替换为实际的值。

    Args:
        value: 任意字符串（可能包含 $cache{key} 引用）

    Returns:
        str: 替换后的字符串

    示例：
    url: "$cache{host}/api/v1/user"
    -> url: "https://api.example.com/api/v1/user"

    类型前缀支持：
    $cache{int:userId} -> 按 int 类型读取缓存
    $cache{bool:isRun} -> 按 bool 类型读取缓存
    $cache{list:ids}   -> 按 list 类型读取缓存
    """
    from utils.cache_process.cache_control import CacheHandler

    # 正则匹配所有的 $cache{...} 表达式
    regular_dates = re.findall(r"\$cache\{(.*?)\}", value)

    # 遍历每个缓存引用
    for regular_data in regular_dates:
        # 检查是否有类型前缀（int:, bool:, list:, dict:, tuple:, float:）
        value_types = ['int:', 'bool:', 'list:', 'dict:', 'tuple:', 'float:']
        if any(i in regular_data for i in value_types) is True:
            # 提取类型和数据名
            value_types = regular_data.split(":")[0]
            regular_data = regular_data.split(":")[1]
            pattern = re.compile(r'\'\$cache\{' + value_types.split(":")[0] + ":" + regular_data + r'\}\'')
        else:
            # 没有类型前缀
            pattern = re.compile(
                r'\$cache\{' + regular_data.replace('$', "\$").replace('[', '\[') + r'\}'
            )
        try:
            # 从缓存中读取数据
            cache_data = CacheHandler.get_cache(regular_data)
            # 替换引用为实际值
            value = re.sub(pattern, str(cache_data), value)
        except Exception:
            pass  # 如果缓存中不存在，保持原值不变
    return value


def regular(target):
    """
    动态表达式解析主入口

    解析 ${{function()}} 格式的表达式，调用 Context 类中对应的方法，
    将返回值替换到原位置。

    【解析流程】
    1. 正则匹配所有的 ${{...}} 表达式
    2. 提取方法名和参数
    3. 通过反射调用 Context 类中的对应方法
    4. 将返回值替换到原字符串中
    5. 循环直到没有更多表达式

    Args:
        target: 需要解析的字符串

    Returns:
        str: 解析后的字符串

    示例：
    "${{host()}}/api/v1/user?page=${{random_int()}}"
    -> "https://api.example.com/api/v1/user?page=1234"

    Java 类比：
    public String resolvePlaceholders(String target) {
        Pattern pattern = Pattern.compile("\\$\\{(.*?)\\}");
        Matcher matcher = pattern.matcher(target);
        while (matcher.find()) {
            String methodName = matcher.group(1).split("\\(")[0];
            Method method = Context.class.getMethod(methodName);
            String value = method.invoke(context).toString();
            target = target.replace(matcher.group(), value);
        }
        return target;
    }
    """
    try:
        regular_pattern = r'\${{(.*?)}}'
        while re.findall(regular_pattern, target):
            key = re.search(regular_pattern, target).group(1)
            # 检查是否有类型前缀
            value_types = ['int:', 'bool:', 'list:', 'dict:', 'tuple:', 'float:']
            if any(i in key for i in value_types) is True:
                # 有类型前缀：解析类型后的方法名和参数
                func_name = key.split(":")[1].split("(")[0]
                value_name = key.split(":")[1].split("(")[1][:-1]
                if value_name == "":
                    value_data = getattr(Context(), func_name)()
                else:
                    value_data = getattr(Context(), func_name)(*value_name.split(","))
                # 替换带引号的表达式（如 '${{random_int()}}' -> 123）
                regular_int_pattern = r'\'\${{(.*?)}}\''
                target = re.sub(regular_int_pattern, str(value_data), target, 1)
            else:
                # 没有类型前缀：直接解析方法名和参数
                func_name = key.split("(")[0]
                value_name = key.split("(")[1][:-1]
                if value_name == "":
                    value_data = getattr(Context(), func_name)()
                else:
                    value_data = getattr(Context(), func_name)(*value_name.split(","))
                target = re.sub(regular_pattern, str(value_data), target, 1)
        return target

    except AttributeError:
        ERROR.logger.error("未找到对应的替换的数据, 请检查数据是否正确 %s", target)
        raise


if __name__ == '__main__':
    a = "${{host()}} aaa"
    b = regular(a)
