#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2022/5/23 18:27
# @Author  : 余少琪
# @Description: JSONPath 动态替换引擎
#
# 【文件作用】
# 将 JSONPath 表达式转换为 Python 字典访问语法，
# 用于动态赋值操作。
#
# 【转换规则】
# JSONPath: $.data.id
# 转为: yaml_case['data']['id']
#
# JSONPath: $.data.items[0].name
# 转为: yaml_case['data']['items'][0]['name']
#
# 【为什么需要这个？】
# 框架通过 exec() 动态执行 Python 赋值语句来实现数据替换。
# 需要将用户写的 JSONPath 转为 Python 代码，这就是这个函数做的事情。
#
# 【Java 对比说明】
# 类似于 Java 中使用反射进行动态字段赋值：
# Field field = obj.getClass().getDeclaredField("data");
# field.set(obj, newValue);
#
# 但在 Python 中更简单，直接通过 exec() 执行字符串代码

def jsonpath_replace(change_data, key_name, data_switch=None):
    """
    将 JSONPath 表达式转为 Python 字典访问语法

    【转换流程】
    1. 输入：change_data = ['$', 'data', 'id']
             key_name = 'yaml_case'
    2. 遍历每个部分：
       - '$' -> 跳过（JSONPath 的根标记）
       - 'data' -> 追加 ['data']
       - 'id' -> 追加 ['id']
    3. 输出：yaml_case['data']['id']

    Args:
        change_data: JSONPath 分割后的列表
                     如：['$', 'data', 'id']
        key_name: Python 变量名（根对象）
                  如：'yaml_case'
        data_switch: 数据开关（已废弃，保留兼容性）

    Returns:
        str: Python 字典访问表达式

    示例：
    >>> jsonpath_replace(['$', 'data', 'id'], 'yaml_case')
    "yaml_case['data']['id']"

    >>> jsonpath_replace(['$', 'data', 'items', '[0]', 'name'], 'yaml_case')
    "yaml_case['data']['items'][0]['name']"

    Java 类比：
    类似于构建动态字段访问路径：
    String expression = keyName + "['" + String.join("']['", changeData) + "']";
    """
    _new_data = key_name + ''
    for i in change_data:
        if i == '$':
            # JSONPath 的根标记，跳过
            pass
        elif data_switch is None and i == "data":
            # 特殊情况：data 直接作为属性访问（已废弃逻辑）
            _new_data += '.data'
        elif i[0] == '[' and i[-1] == ']':
            # 数组索引：[0] -> [0]（保持原样，不加引号）
            _new_data += "[" + i[1:-1] + "]"
        else:
            # 字典键名：data -> ['data']
            _new_data += '[' + '"' + i + '"' + "]"
    return _new_data


if __name__ == '__main__':
    jsonpath_replace(change_data=['$', 'data', 'id'], key_name='self.__yaml_case')
