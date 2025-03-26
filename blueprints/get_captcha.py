from io import BytesIO
from random import  choices
from captcha.image import ImageCaptcha
from PIL import Image

def gen_captcha(content="0123456789"):
    image = ImageCaptcha()
    captcha_text = "".join(choices(content,k=4))
    captcha_image = Image.open(image.generate(captcha_text))
    return captcha_text,captcha_image

def get_captcha_code_and_content():
    code,image = gen_captcha()
    out = BytesIO()
    image.save(out,"png")
    out.seek(0)
    content = out.read()
    return code,content

if __name__=="__main__":
    code,content = get_captcha_code_and_content()
    print(code,content)