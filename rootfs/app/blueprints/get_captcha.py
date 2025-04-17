from io import BytesIO
from random import choices
from captcha.image import ImageCaptcha
from typing import Tuple

 
def get_captcha_code_and_content(content: str = "0123456789", length: int = 4) -> Tuple[str, bytes]:
    image = ImageCaptcha()
    captcha_text = "".join(choices(content, k=length))
    image_stream = BytesIO()
    image.write(captcha_text, image_stream)  # 直接将图片写入 BytesIO
    return captcha_text, image_stream.getvalue()


if __name__ == "__main__":
    code, content = get_captcha_code_and_content(content="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", length=6)
    print(f"Captcha Code: {code}")
    print(f"Captcha Content (binary): {content[:20]}...")