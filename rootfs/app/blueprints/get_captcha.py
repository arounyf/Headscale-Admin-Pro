from io import BytesIO
from random import choices
from captcha.image import ImageCaptcha
from typing import Tuple

def gen_captcha(content: str = "0123456789", length: int = 4) -> Tuple[str, BytesIO]:
    """
    生成验证码文本和图片
    :param content: 验证码字符集
    :param length: 验证码长度
    :return: 验证码文本和图片的 BytesIO 对象
    """
    image = ImageCaptcha()
    captcha_text = "".join(choices(content, k=length))
    captcha_image = image.generate(captcha_text)  # 直接生成图片的 BytesIO 对象
    return captcha_text, captcha_image

def get_captcha_code_and_content(content: str = "0123456789", length: int = 4, image_format: str = "png") -> Tuple[str, bytes]:
    """
    获取验证码文本和图片的二进制内容
    :param content: 验证码字符集
    :param length: 验证码长度
    :param image_format: 图片格式（如 png、jpeg）
    :return: 验证码文本和图片的二进制内容
    """
    code, image_stream = gen_captcha(content, length)
    out = BytesIO()
    out.write(image_stream.read())  # 将生成的图片内容写入 BytesIO
    out.seek(0)
    return code, out.read()

if __name__ == "__main__":
    code, content = get_captcha_code_and_content(content="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", length=6)
    print(f"Captcha Code: {code}")
    print(f"Captcha Content (binary): {content[:20]}...")  # 打印前 20 个字节