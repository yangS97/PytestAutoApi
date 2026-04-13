#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/4/7 17:53
# @Author : 余少琪
# @Description: Allure 报告步骤和附件工具
#
# 【文件作用】
# 提供在 Allure 报告中添加步骤和附件（附件、图片、文件）的方法。
#
# 【Allure 步骤概念】
# Allure 报告的测试用例可以包含多个步骤，每个步骤可以：
# 1. 有名称（如 "请求URL: /api/v1/user"）
# 2. 有附件（如请求体 JSON、响应体 JSON）
# 3. 有嵌套子步骤
#
# 【Java 对比说明】
# 类似于 Java Allure 的：
# @Step("Request URL: {0}")
# public void logRequest(String url, Object body) {
#     Allure.addAttachment("Request Body", new ByteArrayInputStream(...));
# }
import json
import allure
from utils.other_tools.models import AllureAttachmentType


def allure_step(step: str, var: str) -> None:
    """
    在 Allure 报告中添加一个带附件的步骤

    这个方法会在 Allure 报告中创建一个步骤，
    并将传入的数据以 JSON 格式附加为附件。

    Args:
        step: 步骤名称（如 "请求头: "、"请求数据: "）
        var: 附件内容（会被格式化为 JSON）

    效果示例：
    在 Allure 报告中显示：
    └─ 请求头:
        {"Content-Type": "application/json", "Authorization": "Bearer xxx"}

    Java 类比：
    @Step("{step}")
    public void allureStep(String step, Object var) {
        Allure.addAttachment(step, new ByteArrayInputStream(
            new ObjectMapper().writeValueAsString(var).getBytes()));
    }
    """
    with allure.step(step):
        allure.attach(
            # 将数据格式化为 JSON 字符串（中文不转义）
            json.dumps(str(var), ensure_ascii=False, indent=4),
            step,                          # 附件名称
            allure.attachment_type.JSON    # 附件类型
        )


def allure_attach(source: str, name: str, extension: str):
    """
    在 Allure 报告中添加文件附件

    用于在报告中附加图片、Excel 文件、文本文件等。
    典型使用场景：文件上传测试时，在报告中展示上传的文件预览。

    Args:
        source: 文件路径（绝对路径）
        name: 附件名称（文件名）
        extension: 附件的扩展名

    Java 类比：
    public void allureAttach(String source, String name, String extension) {
        Allure.addAttachment(name, new FileInputStream(source));
    }
    """
    # 获取文件扩展名并转为大写
    _name = name.split('.')[-1].upper()
    # 从 AllureAttachmentType 枚举中获取对应的附件类型
    _attachment_type = getattr(AllureAttachmentType, _name, None)

    allure.attach.file(
        source=source,
        name=name,
        # 如果枚举中不存在对应的类型，则使用 None
        attachment_type=_attachment_type if _attachment_type is None else _attachment_type.value,
        extension=extension
    )


def allure_step_no(step: str):
    """
    在 Allure 报告中添加一个无附件的简单步骤

    只显示步骤名称，不附加任何内容。
    用于记录简单的操作信息（如 "请求URL: /api/v1/user"）。

    Args:
        step: 步骤名称
    """
    with allure.step(step):
        pass
