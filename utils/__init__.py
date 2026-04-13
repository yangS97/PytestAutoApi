"""
utils 包的初始化文件 —— 全局配置加载器

【核心作用】
当任何代码 import utils 或 from utils import config 时，
这个文件会自动执行，将 config.yaml 加载为一个全局 Config 对象。

【执行流程】
1. 通过 GetYamlData 读取 config.yaml 文件
2. 将 YAML 数据解析为 Python 字典
3. 使用 Config(**_data) 将字典转换为 Pydantic 模型对象
4. 其他模块通过 from utils import config 直接使用这个全局配置对象

【Java 对比说明】
- 这类似于 Java 中的静态初始化块（static { }）
- Config(**_data) 中的 ** 是 Python 的字典解包操作符
  类似于将字典的键值对作为构造函数的命名参数传入
  Java 类比：new ObjectMapper().convertValue(dataMap, Config.class)
- 单例模式：这个 config 对象在整个程序生命周期中只会被创建一次
"""

from utils.read_files_tools.yaml_control import GetYamlData
from common.setting import ensure_path_sep
from utils.other_tools.models import Config


# 步骤 1：读取 config.yaml 文件
# ensure_path_sep("\\common\\config.yaml") 将相对路径转为当前系统的绝对路径
# GetYamlData(...).get_yaml_data() 解析 YAML 文件内容为 Python 字典
_data = GetYamlData(ensure_path_sep("\\common\\config.yaml")).get_yaml_data()

# 步骤 2：将字典数据转为 Pydantic Config 对象
# **_data 是字典解包操作，将字典的键值对作为关键字参数传递给 Config 构造函数
# 例如：如果 _data = {"project_name": "test", "env": "dev"}
#       等价于 Config(project_name="test", env="dev")
config = Config(**_data)


