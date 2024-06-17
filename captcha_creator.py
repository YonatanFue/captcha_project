from image_transformer import ImageTransformer
from random import choice as rngchoice
from io import BytesIO
from PIL import Image
from util import *
import threading
import base64
import os


# all letters and numbers
characters = os.listdir(r'C:\yonatan\.CodingP3.10\..Projects\.Captcha\characters')


class Captcha:
    def __init__(self):
        self.image = None
        self.answer = ""
        self.rot_chars = [None, None, None, None, None, None, None, None]


charactertoimagedict = {}  # seperate everything except the name, caps sensitive
for characterpath in characters:
    letter = characterpath.split(".")[0]
    letter = letter.split("cap")[0]
    charactertoimagedict[letter] = load_image("characters\\" + str(characterpath))


# for threads
def rotate_letter(charimage, captcha, index, lock):
    cur_image = charimage

    it = ImageTransformer(cur_image)
    rotated_img = it.rotate_along_axis(xang=ran(-40, 40), yang=ran(-40, 40), zang=ran(-60, 60))

    lock.acquire()
    captcha.rot_chars[index] = rotated_img
    lock.release()


# main function
def create_captcha(lvl):
    lock = threading.Lock()
    captchacl = Captcha()

    threads = []
    for i in range(8):  # each letter rotated simultaneously
        # random (key,value) tuple
        random_pair = rngchoice(list(charactertoimagedict.items()))
        random_key, random_value = random_pair

        captchacl.answer += random_key

        threads.append(threading.Thread(target=rotate_letter, args=(random_value, captchacl, i, lock)))
        threads[i].start()

    width, height = 700, 350

    captchacl.image = Image.new('RGB', (width, height), color="white")  # canvas

    [thr.join() for thr in threads]  # wait for all rotated

    char_x_offset = 0
    char_y_offset = ran(int(height * 0.12), int(height * 0.6))
    # converting nd numpy array from rotator and pasting each character on final captcha, including offsets for spacing
    for npimg in captchacl.rot_chars:
        img = Image.fromarray(cv2.cvtColor(npimg, cv2.COLOR_BGR2RGB))
        captchacl.image.paste(img, (char_x_offset, char_y_offset, img.width + char_x_offset, img.height + char_y_offset))
        char_x_offset += img.width
        char_y_offset = ran(int(height * 0.12), int(height * 0.6))

    for i in range(lvl**2):
        captchacl.image = draw_squiggly_line(captchacl.image)

    buffered = BytesIO()
    captchacl.image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return img_str, captchacl.answer
