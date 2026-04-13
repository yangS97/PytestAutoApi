# coding=utf-8
"""
    @project: pytest-auto-api2
    @Author：七月
    @file： address_detection.py
    @date：2022/11/9 11:42
    @blogs: https://blog.csdn.net/weixin_43865008
    @Description: 店铺地址校验工具
    @note: 这个文件是业务专用工具，用于检测店铺地址中的区/县 code 是否正确。
           不属于框架核心功能，可以忽略。
"""
from utils.mysql_tool.mysql_control import MysqlDB
import copy


class AddressDetection(MysqlDB):
    """
    店铺地址检测器 —— 校验数据库中店铺地址的区县 code 是否正确

    这个类是业务专用的工具，用于发现并修复店铺地址数据中的错误。
    不属于测试框架的核心功能。

    核心流程：
    1. 查询所有已上线且未删除的店铺
    2. 获取平台地址库中的省份 code
    3. 对比店铺地址的区县 code 与地址库中的 code 是否匹配
    4. 如果不匹配，输出修正建议
    """

    def get_shop_address_entity_str(self):
        """
        获取所有已经上线并且未删除的店铺地址

        过滤条件：
        - status = 2: 已上线
        - delete_flag = 0: 未删除
        - sub_shop_type > 300 且 sub_shop_type = 300（这个条件实际上永远为假）

        Returns:
            list: 店铺信息列表
        """
        shop_info = self.query("SELECT id, name, attribute, shop_type, sub_shop_type "
                               "FROM `test_obp_supplier`.`supplier_shop` "
                               "where status = 2 and delete_flag = 0 and sub_shop_type > 300 "
                               "and sub_shop_type = 300")
        return shop_info

    def get_logistics_address_library(self):
        """
        获取平台地址库中的省份 code

        Returns:
            dict: {code: name} 的映射（如 {"110000": "北京市"}）
        """
        code = self.query("select name, code from `test_obp_order`.`logistics_address_library` "
                          "where parent_code > 0")

        area_code = {}
        for i in code:
            area_code[i['code']] = i['name']
        return area_code

    def get_error_shop(self):
        """
        获取错误的店铺数据

        遍历所有店铺，检查其地址的区县 code 是否与平台地址库中的 code 匹配。
        如果不匹配，输出错误信息和修正建议。
        """
        # 获取区域 code
        get_logistics_address_library = self.get_logistics_address_library()
        num = 0
        for i in self.get_shop_address_entity_str():
            # 获取店铺地址
            shop_address_entity_str = eval(i['attribute'])['shopAddressEntityStr']

            if shop_address_entity_str['countiesName'] == get_logistics_address_library[str(shop_address_entity_str['countiesCode'])]:
                pass
            else:
                area_name = self.query(f"SELECT name, code FROM `test_obp_order`.`logistics_address_library`"
                           f" where parent_code = {shop_address_entity_str['cityCode']} and name = '{shop_address_entity_str['countiesName']}'")
                num += 1

                new_shop_address_entity_str = copy.deepcopy(shop_address_entity_str)
                new_shop_address_entity_str['countiesCode'] = area_name[0]['code']
                print(f"店铺名称: {i['name']}, 店铺id: {i['id']}, "
                      f"店铺地址：{shop_address_entity_str['cityName']}{shop_address_entity_str['provinceName']}{shop_address_entity_str['countiesName']}"
                      f"\n当前实际数据:{shop_address_entity_str}"
                      f"\n{shop_address_entity_str['countiesName']}的实际code码为 {area_name}"
                      f"\n更改后的数据： {new_shop_address_entity_str}")
                print("*" * 100)

        print(num)


AddressDetection().get_error_shop()
