from io import BytesIO
from random import choices
from captcha.image import ImageCaptcha
from typing import Tuple

def gen_captcha(content: str = "0123456789", length: int = 4) -> Tuple[str, BytesIO]:
    image = ImageCaptcha()
    captcha_text = "".join(choices(content, k=length))
    captcha_image = image.generate(captcha_text)  # 直接生成图片的 BytesIO 对象
    return captcha_text, captcha_image

def get_captcha_code_and_content(content: str = "0123456789", length: int = 4, image_format: str = "png") -> Tuple[str, bytes]:
    code, image_stream = gen_captcha(content, length)
    out = BytesIO()
    out.write(image_stream.getvalue())  # 确保完整写入流内容
    out.seek(0)
    return code, out.read()

if __name__ == "__main__":
    code, content = get_captcha_code_and_content(content="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", length=6)
    print(f"Captcha Code: {code}")
    print(f"Captcha Content (binary): {content[:20]}...")