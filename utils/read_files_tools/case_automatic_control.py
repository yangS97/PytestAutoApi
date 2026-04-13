#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 13:22
# @Author : 余少琪
# @Description: YAML 用例自动生成 Python 测试代码
#
# 【文件作用】
# 将 data/ 目录下的 YAML 测试用例文件，自动转换为 test_case/ 目录下的
# Python pytest 测试代码。这是框架 "YAML 驱动" 核心机制的实现。
#
# 【工作流程】
# 1. 扫描 data/ 目录下所有的 .yaml/.yml 文件
# 2. 将 YAML 文件名转为 Python 文件名（如 login.yaml -> test_login.py）
# 3. 从 YAML 中读取 allure 报告标签（epic/feature/story）
# 4. 生成测试类名称（snake_case -> CamelCase）
# 5. 调用 write_testcase_file 写入 Python 文件
#
# 【Java 对比说明】
# - 类似于 Java 中通过代码生成器（如 MyBatis Generator）从数据库表结构
#   生成 Entity/Mapper 文件的过程
# - os.path 操作类似于 Java 的 java.nio.file.Paths
# - .capitalize() 类似于 Java 的 StringUtils.capitalize()
import os
from typing import Text, Dict
from common.setting import ensure_path_sep
from utils.read_files_tools.testcase_template import write_testcase_file
from utils.read_files_tools.yaml_control import GetYamlData
from utils.read_files_tools.get_all_files_path import get_all_files
from utils.other_tools.exceptions import ValueNotFoundError


class TestCaseAutomaticGeneration:
    """
    测试用例自动生成引擎

    职责：将 YAML 文件路径和元数据转换为 Python 测试文件的各个组成部分

    Java 类比：
    public class TestCaseAutomaticGeneration {
        public String getCaseDatePath() { ... }
        public String getCasePath() { ... }
        // ...
    }
    """

    @staticmethod
    def case_date_path() -> Text:
        """
        返回 YAML 用例数据目录的绝对路径

        Returns:
            str: data/ 目录的绝对路径

        示例：/Users/ys/PyCharmProject/PytestAutoApi/data
        """
        return ensure_path_sep("\\data")

    @staticmethod
    def case_path() -> Text:
        """
        返回生成的 Python 测试代码存放目录的绝对路径

        Returns:
            str: test_case/ 目录的绝对路径

        示例：/Users/ys/PyCharmProject/PytestAutoApi/test_case
        """
        return ensure_path_sep("\\test_case")

    def file_name(self, file: Text) -> Text:
        """
        将 YAML 文件路径转换为相对 Python 文件路径

        转换规则：
        - 去掉 data/ 前缀路径
        - 将 .yaml/.yml 后缀改为 .py

        Args:
            file: YAML 文件的绝对路径
                  如: /Users/ys/PytestAutoApi/data/Login/login.yaml

        Returns:
            str: 相对的 Python 文件路径
                 如: /Login/test_login.py（注意还没有 test_ 前缀）

        Java 类比：
        String yamlPath = file.substring(caseDatePath.length());
        return yamlPath.replace(".yaml", ".py").replace(".yml", ".py");
        """
        i = len(self.case_date_path())
        yaml_path = file[i:]
        file_name = None
        # 路径转换：将 .yaml/.yml 后缀改为 .py
        if '.yaml' in yaml_path:
            file_name = yaml_path.replace('.yaml', '.py')
        elif '.yml' in yaml_path:
            file_name = yaml_path.replace('.yml', '.py')
        return file_name

    def get_case_path(self, file_path: Text) -> tuple:
        """
        生成完整的测试用例文件路径和文件名

        在 file_name 的基础上：
        - 添加 test_ 前缀（pytest 要求测试文件必须以 test_ 开头）
        - 拼接完整的绝对路径

        Args:
            file_path: YAML 用例的绝对路径

        Returns:
            tuple: (完整绝对路径, 文件名)
            示例: ('/Users/.../test_case/Login/test_login.py', 'test_login.py')

        Java 类比：
        返回一个 Path 对象和文件名的元组：
        return new Tuple<>(Paths.get(testCasePath, "test_" + fileName), "test_" + fileName);
        """
        # 通过 os.sep（系统路径分隔符）分割路径，获取文件名部分
        path = self.file_name(file_path).split(os.sep)
        # 添加 test_ 前缀（pytest 的命名约定）
        case_name = path[-1] = path[-1].replace(path[-1], "test_" + path[-1])
        new_name = os.sep.join(path)
        return ensure_path_sep("\\test_case" + new_name), case_name

    def get_test_class_title(self, file_path: Text) -> Text:
        """
        自动生成 Python 测试类名称

        转换规则：snake_case -> CamelCase（PascalCase）
        示例：sup_apply_list -> SupApplyList

        Args:
            file_path: YAML 用例路径

        Returns:
            str: CamelCase 格式的类名

        Java 类比：
        // 类似于将 sup_apply_list 转为 SupApplyList
        String className = Arrays.stream(fileName.split("_"))
            .map(StringUtils::capitalize)
            .collect(Collectors.joining());
        """
        # 提取文件名称（去掉 .py 后缀）
        _file_name = os.path.split(self.file_name(file_path))[1][:-3]
        _name = _file_name.split("_")
        _name_len = len(_name)
        # 将每个部分首字母大写
        for i in range(_name_len):
            _name[i] = _name[i].capitalize()
        _class_name = "".join(_name)

        return _class_name

    @staticmethod
    def error_message(param_name, file_path):
        """
        生成用例参数缺失的错误提示信息

        Args:
            param_name: 缺失的参数名称（如 "allureEpic"）
            file_path: 用例文件路径

        Returns:
            str: 格式化的错误提示信息
        """
        msg = f"用例中未找到 {param_name} 参数值，请检查新增的用例中是否填写对应的参数内容" \
              "如已填写，可能是 yaml 参数缩进不正确\n" \
              f"用例路径: {file_path}"
        return msg

    def func_title(self, file_path: Text) -> Text:
        """
        生成测试函数名称

        从 YAML 文件名中提取函数名部分（去掉 .py 后缀）

        Args:
            file_path: YAML 用例路径

        Returns:
            str: 测试函数名称

        示例：login.yaml -> login
        """
        _file_name = os.path.split(self.file_name(file_path))[1][:-3]
        return _file_name

    @staticmethod
    def allure_epic(case_data: Dict, file_path) -> Text:
        """
        提取 Allure 报告的 Epic 标签

        Allure 报告层级结构：Epic > Feature > Story
        - Epic: 最大粒度的分类，通常代表一个大的业务领域或项目
        - Feature: 功能模块级别
        - Story: 具体测试功能点

        从 YAML 的 case_common.allureEpic 字段中读取

        Args:
            case_data: YAML 文件解析后的字典数据
            file_path: 用例路径（用于错误提示）

        Returns:
            str: Epic 名称

        Java 类比：
        @Epic("用户管理")  // Allure 报告的注解
        """
        try:
            return case_data['case_common']['allureEpic']
        except KeyError as exc:
            raise ValueNotFoundError(TestCaseAutomaticGeneration.error_message(
                param_name="allureEpic",
                file_path=file_path
            )) from exc

    @staticmethod
    def allure_feature(case_data: Dict, file_path) -> Text:
        """
        提取 Allure 报告的 Feature 标签

        从 YAML 的 case_common.allureFeature 字段中读取

        Java 类比：
        @Feature("登录模块")
        """
        try:
            return case_data['case_common']['allureFeature']
        except KeyError as exc:
            raise ValueNotFoundError(TestCaseAutomaticGeneration.error_message(
                param_name="allureFeature",
                file_path=file_path
            )) from exc

    @staticmethod
    def allure_story(case_data: Dict, file_path) -> Text:
        """
        提取 Allure 报告的 Story 标签

        从 YAML 的 case_common.allureStory 字段中读取

        Java 类比：
        @Story("密码登录测试")
        """
        try:
            return case_data['case_common']['allureStory']
        except KeyError as exc:
            raise ValueNotFoundError(TestCaseAutomaticGeneration.error_message(
                param_name="allureStory",
                file_path=file_path
            )) from exc

    def mk_dir(self, file_path: Text) -> None:
        """
        检查并创建测试代码输出目录

        如果 test_case/ 下的子目录不存在（如 test_case/Login/），
        则自动创建该目录。

        Args:
            file_path: YAML 用例的绝对路径

        Java 类比：
        Files.createDirectories(Paths.get(caseDirPath));  // Java 7+ NIO
        """
        _case_dir_path = os.path.split(self.get_case_path(file_path)[0])[0]
        if not os.path.exists(_case_dir_path):
            os.makedirs(_case_dir_path)

    @staticmethod
    def case_ids(test_case):
        """
        获取 YAML 文件中所有用例的 ID 列表

        遍历 YAML 文件的所有键（除了 case_common），
        这些键就是各个测试用例的唯一标识。

        Args:
            test_case: YAML 文件解析后的字典

        Returns:
            list: 所有用例 ID 的列表

        示例 YAML：
        case_common:         <- 这个会被跳过
          allureEpic: "xxx"
        login_001:           <- 这个会被加入列表
          url: "/api/login"
        login_002:           <- 这个会被加入列表
          url: "/api/login"

        返回：['login_001', 'login_002']
        """
        ids = []
        for k, v in test_case.items():
            if k != "case_common":
                ids.append(k)
        return ids

    def yaml_path(self, file_path: Text) -> Text:
        """
        生成动态 YAML 文件相对路径

        处理业务分层场景：当 data/ 下有多个子目录时，
        生成正确的相对路径供生成的 Python 代码引用。

        Args:
            file_path: YAML 文件的绝对路径

        Returns:
            str: 相对路径（统一使用 / 分隔符，跨平台兼容）

        示例：/Users/.../data/Login/login.yaml -> Login/login.yaml
        """
        i = len(self.case_date_path())
        # 兼容 Linux 和 Windows 操作路径
        yaml_path = file_path[i:].replace("\\", "/")
        return yaml_path

    def get_case_automatic(self) -> None:
        """
        主执行方法：扫描所有 YAML 文件并自动生成 Python 测试代码

        【执行流程】
        1. 获取 data/ 目录下所有的 .yaml/.yml 文件路径
        2. 遍历每个文件（排除代理拦截的 proxy_data.yaml）
        3. 创建对应的输出目录
        4. 读取 YAML 数据
        5. 提取用例 ID 列表
        6. 调用 write_testcase_file 生成 Python 测试文件

        Java 类比：
        类似于代码生成器的主方法：
        public void generateAllTestCases() {
            List<String> yamlFiles = scanYamlFiles();
            for (String file : yamlFiles) {
                if (!file.contains("proxy_data")) {
                    createOutputDirectory(file);
                    Map<String, Object> yamlData = loadYaml(file);
                    writeTestCaseFile(extractMetaData(yamlData));
                }
            }
        }
        """
        # 获取 data/ 目录下所有的 YAML 文件路径
        file_path = get_all_files(file_path=ensure_path_sep("\\data"), yaml_data_switch=True)

        for file in file_path:
            # 排除代理拦截生成的 YAML 文件（不为其生成测试代码）
            if 'proxy_data.yaml' not in file:
                # 确保输出目录存在
                self.mk_dir(file)
                # 读取 YAML 文件数据
                yaml_case_process = GetYamlData(file).get_yaml_data()
                # 获取用例 ID 列表
                self.case_ids(yaml_case_process)
                # 生成 Python 测试文件
                write_testcase_file(
                    allure_epic=self.allure_epic(case_data=yaml_case_process, file_path=file),
                    allure_feature=self.allure_feature(yaml_case_process, file_path=file),
                    class_title=self.get_test_class_title(file),
                    func_title=self.func_title(file),
                    case_path=self.get_case_path(file)[0],
                    case_ids=self.case_ids(yaml_case_process),
                    file_name=self.get_case_path(file)[1],
                    allure_story=self.allure_story(case_data=yaml_case_process, file_path=file)
                )


if __name__ == '__main__':
    TestCaseAutomaticGeneration().get_case_automatic()
