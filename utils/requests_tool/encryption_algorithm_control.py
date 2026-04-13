#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2022/5/23 21:27
# @Author  : 余少琪
# @Email   : 1603453211@qq.com
# @Description: 加密算法工具类
#
# 【文件作用】
# 提供各种常用的加密算法，供接口测试中使用。
# 支持的加密算法：
# - MD5
# - SHA1
# - HMAC-SHA256
# - DES
# - 装饰器形式的 MD5 批量加密（对请求体所有字段进行 MD5）
#
# 【Java 对比说明】
# 类似于 Java 中的 DigestUtils / MessageDigest：
# String md5 = DigestUtils.md5Hex(value);
# String sha1 = DigestUtils.sha1Hex(value);
# String hmac = HmacUtils.hmacSha256Hex(key, data);
import hashlib
from hashlib import sha256
import hmac
from typing import Text
import binascii
from pyDes import des, ECB, PAD_PKCS5


def hmac_sha256_encrypt(key, data):
    """
    HMAC-SHA256 加密算法

    HMAC 是一种使用密码学哈希函数和密钥的消息认证码算法。
    比单纯的 SHA256 更安全，因为加入了密钥。

    Args:
        key: 密钥
        data: 待加密数据

    Returns:
        str: 加密后的十六进制字符串

    Java 类比：
    String hmacSha256 = new HmacUtils(HmacAlgorithms.HMAC_SHA_256, key).hmacHex(data);
    """
    _key = key.encode('utf8')
    _data = data.encode('utf8')
    encrypt_data = hmac.new(_key, _data, digestmod=sha256).hexdigest()
    return encrypt_data


def md5_encryption(value):
    """
    MD5 加密

    MD5 是一种不可逆的哈希算法，常用于密码存储、文件校验等场景。

    Args:
        value: 待加密的值

    Returns:
        str: 32位十六进制 MD5 哈希值

    Java 类比：
    String md5 = DigestUtils.md5Hex(value.toString());
    """
    str_md5 = hashlib.md5(str(value).encode(encoding='utf-8')).hexdigest()
    return str_md5


def sha1_secret_str(_str: Text):
    """
    SHA1 加密算法

    SHA1 比 MD5 更安全（160位输出 vs 128位），但现在也被认为不够安全，
    推荐使用 SHA256。

    Args:
        _str: 待加密的字符串

    Returns:
        str: 十六进制 SHA1 哈希值

    Java 类比：
    String sha1 = DigestUtils.sha1Hex(str);
    """
    encrypts = hashlib.sha1(_str.encode('utf-8')).hexdigest()
    return encrypts


def des_encrypt(_str):
    """
    DES 对称加密

    DES 是一种对称加密算法，加密和解密使用相同的密钥。
    返回 16 进制编码的加密结果。

    Args:
        _str: 待加密的字符串

    Returns:
        bytes: 16进制编码的加密结果

    注意：
    - 密钥硬编码为 'PASSWORD'，实际使用应该从配置中读取
    - DES 已被认为不够安全，推荐使用 AES

    Java 类比：
    Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
    SecretKey key = new SecretKeySpec("PASSWORD".getBytes(), "DES");
    cipher.init(Cipher.ENCRYPT_MODE, key);
    byte[] encrypted = cipher.encrypt(str.getBytes());
    return Hex.encodeHexString(encrypted);
    """
    # 密钥，自行修改
    _key = 'PASSWORD'
    secret_key = _key
    _iv = secret_key
    key = des(secret_key, ECB, _iv, pad=None, padmode=PAD_PKCS5)
    _encrypt = key.encrypt(_str, padmode=PAD_PKCS5)
    return binascii.b2a_hex(_encrypt)


def encryption(ency_type):
    """
    加密装饰器 —— 对请求体所有字段进行批量加密

    这是一个装饰器工厂，返回的装饰器会对被装饰函数的返回值中的
    body 字段的所有值进行指定类型的加密。

    Args:
        ency_type: 加密类型（目前只支持 "md5"）

    Returns:
        装饰器函数

    使用示例：
    @encryption("md5")
    def http_request(self):
        # 返回的 response.body 中的所有值都会被 MD5 加密
        return response

    Java 类比：
    类似于 AOP 切面，在方法返回后修改返回值：
    @Around("execution(* RequestControl.httpRequest(..))")
    public Object encryptResponse(ProceedingJoinPoint pjp) {
        Object res = pjp.proceed();
        encryptBodyFields((ResponseData) res, "md5");
        return res;
    }
    """
    def decorator(func):
        def swapper(*args, **kwargs):
            res = func(*args, **kwargs)
            _data = res['body']
            if ency_type == "md5":
                def ency_value(data):
                    if data is not None:
                        for key, value in data.items():
                            if isinstance(value, dict):
                                # 递归处理嵌套字典
                                ency_value(data=value)
                            else:
                                data[key] = md5_encryption(value)
            else:
                raise ValueError("暂不支持该加密规则，如有需要，请联系管理员")
            ency_value(_data)
            return res

        return swapper

    return decorator
