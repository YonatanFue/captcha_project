from random import randint as ran
import math
import cv2


def load_image(img_path):
    return cv2.imread(img_path)


def save_image(img_path, img):
    cv2.imwrite(img_path, img)


def get_rad(theta, phi, gamma):
    return (math.radians(theta),
            math.radians(phi),
            math.radians(gamma))


def draw_squiggly_line(captcha):
    mwidth, mheight = captcha.size  # size tuple

    xcoord = ran(5, 60)
    ycoord = ran(70, mheight - 70)

    linewidth = int(math.sqrt(ran(1, 10)))  # 50%-2, 30%-1, 20%-3

    turnstr = 0
    current_angle = ran(-30, 30)  # 0 -> right size, makes movement calc easier
    framecounter = 0

    while xcoord < 0.95 * mwidth and 5 < ycoord < mheight - 5:
        for i in range(linewidth):
            for j in range(linewidth):
                captcha.putpixel((round(xcoord) - 1 + 1*i, round(ycoord) - 1 + 1*j), (0, 0, 0))

        ycoord += math.sin(math.radians(current_angle))
        xcoord += math.cos(math.radians(current_angle))

        if framecounter % 50 == 0:
            current_angle = round(current_angle)

            odds = (90 + current_angle) / 180  # closer to going vertical, more odds to switch side. avoid going back and lower odds of hitting edges
            rng = ran(1, 9)

            if rng/10 > odds:  # positive roll
                if current_angle >= 0:  # both positive
                    turnstr = ran(1, 90 - int(current_angle))

                else:  # negative current angle
                    turnstr = ran(-int(current_angle), max(-int(2 * current_angle), 30)) + 1

            else:  # negative roll
                if current_angle <= 0:  # both negative
                    turnstr = -ran(1, 90 + int(current_angle)) - 1

                else:  # positive current angle
                    turnstr = -ran(int(current_angle), max(int(2 * current_angle), 30)) - 1

        current_angle += (turnstr / 50)

        framecounter += 1

    return captcha
