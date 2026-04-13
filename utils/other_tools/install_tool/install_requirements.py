#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2022/5/10 14:02
# @Author  : 余少琪
# @Email   : 1603453211@qq.com
# @Description: 依赖库自动安装工具
#
# 【文件作用】
# 检测 requirements.txt 是否发生了更新，如果有更新，自动执行 pip install 安装。
# 通过比对 requirements.txt 与 version_library_comparisons.txt 的内容来判断。
#
# 【工作流程】
# 1. 读取 version_library_comparisons.txt（上次记录的依赖版本）
# 2. 读取 requirements.txt（当前的依赖版本）
# 3. 比对两个文件内容
# 4. 如果不同，执行 pip install -r requirements.txt
# 5. 将最新的依赖版本写入 version_library_comparisons.txt
#
# 【Java 对比说明】
# 类似于 Maven/Gradle 的自动依赖更新检测，但 Python 中没有内置这样的检测机制
import os
import chardet
from common.setting import ensure_path_sep
from utils.logging_tool.log_control import INFO
from utils import config

# 确保 chardet 库已安装（用于检测文件编码）
os.system("pip3 install chardet")


class InstallRequirements:
    """
    自动识别并安装最新依赖库

    Java 类比：
    public class InstallRequirements {
        private String versionLibraryComparisonsPath;
        private String requirementsPath;
        private String mirrorUrl;

        public void textComparison() {
            if (!readVersionLibraryComparisons().equals(readRequirements())) {
                pipInstall();
                writeVersionLibraryComparisons(readRequirements());
            }
        }
    }
    """

    def __init__(self):
        """
        初始化依赖安装器

        设置：
        - 版本比对文件路径
        - requirements.txt 路径
        - pip 镜像源地址
        """
        self.version_library_comparisons_path = ensure_path_sep("\\utils\\other_tools\\install_tool\\") \
                                                + "version_library_comparisons.txt"
        self.requirements_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) \
                                 + os.sep + "requirements.txt"

        self.mirror_url = config.mirror_source
        # 初始化时，获取最新的版本库
        # os.system("pip freeze > {0}".format(self.requirements_path))

    def read_version_library_comparisons_txt(self):
        """
        读取版本比对默认文件的内容

        这个文件记录了上次安装依赖时的 requirements.txt 内容。

        Returns:
            str: 版本比对文件内容
        """
        with open(self.version_library_comparisons_path, 'r', encoding="utf-8") as file:
            return file.read().strip(' ')

    @classmethod
    def check_charset(cls, file_path):
        """
        检测文件的字符编码

        通过读取文件前 4 个字节，使用 chardet 库检测编码。

        Args:
            file_path: 文件路径

        Returns:
            str: 检测到的字符编码（如 'utf-8', 'ascii'）

        Java 类比：
        类似于 Java 中使用 juniversalchardet 检测文件编码
        """
        with open(file_path, "rb") as file:
            data = file.read(4)
            charset = chardet.detect(data)['encoding']
        return charset

    def read_requirements(self):
        """
        读取 requirements.txt 并清理 ANSI 转义序列

        有些情况下（如从终端导出），requirements.txt 中可能包含 ANSI 颜色代码
       （如 0m），这个方法会清理这些代码。

        Returns:
            str: 清理后的 requirements.txt 内容
        """
        file_data = ""
        with open(
                self.requirements_path,
                'r',
                encoding=self.check_charset(self.requirements_path)
        ) as file:

            for line in file:
                if "" in line:
                    line = line.replace("", "")
                file_data += line

        with open(
                self.requirements_path,
                "w",
                encoding=self.check_charset(self.requirements_path)
        ) as file:
            file.write(file_data)

        return file_data

    def text_comparison(self):
        """
        依赖库版本比对

        【执行流程】
        1. 读取上次记录的依赖版本
        2. 读取当前的依赖版本
        3. 比对两者是否一致
        4. 如果不一致，执行 pip install 并更新记录文件

        如果不一致，执行：
        - pip3 install -r requirements.txt
        - 将最新内容写入 version_library_comparisons.txt
        """
        read_version_library_comparisons_txt = self.read_version_library_comparisons_txt()
        read_requirements = self.read_requirements()
        if read_version_library_comparisons_txt == read_requirements:
            INFO.logger.info("程序中未检查到更新版本库，已为您跳过自动安装库")
        # 程序中如出现不同的文件，则安装
        else:
            INFO.logger.info("程序中检测到您更新了依赖库，已为您自动安装")
            os.system(f"pip3 install -r {self.requirements_path}")
            with open(self.version_library_comparisons_path, "w",
                      encoding=self.check_charset(self.requirements_path)) as file:
                file.write(read_requirements)


if __name__ == '__main__':
    InstallRequirements().text_comparison()
