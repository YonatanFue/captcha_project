from util import *
import numpy as np


class ImageTransformer:
    def __init__(self, image):
        self.image = image

        self.height = self.image.shape[0]
        self.width = self.image.shape[1]

        self.focal = 0

    def rotate_along_axis(self, xang=0, yang=0, zang=0):
        # radians
        rxang, ryang, rzang = get_rad(xang, yang, zang)

        # focal length on z axis
        diaglen = math.sqrt(self.height ** 2 + self.width ** 2)
        self.focal = diaglen / (2 * math.sin(rzang) if math.sin(rzang) != 0 else 1)

        mat = self.get_projection(rxang, ryang, rzang)

        rotated_image = cv2.warpPerspective(self.image.copy(), mat, (self.width, self.height))

        for row in rotated_image:  # replace all grayscale into white, since rotation leaves black bg
            for pixel in row:
                if pixel[0] == pixel[1] == pixel[2] != 255:
                    pixel[0] = 255
                    pixel[1] = 255
                    pixel[2] = 255

        return rotated_image

    def get_projection(self, xang, yang, zang):
        w = self.width
        h = self.height
        f = self.focal

        # into 3d, making center the center of rotation (-half)
        to3d = np.array([[1, 0, -w / 2],
                         [0, 1, -h / 2],
                         [0, 0, 1],
                         [0, 0, 1]])

        # X axis rotator
        xrotator = np.array([[1, 0, 0, 0],
                             [0, math.cos(xang), -math.sin(xang), 0],
                             [0, math.sin(xang), math.cos(xang), 0],
                             [0, 0, 0, 1.25]])

        # y axis rotator
        yrotator = np.array([[math.cos(yang), 0, -math.sin(yang), 0],
                             [0, 1, 0, 0],
                             [math.sin(yang), 0, math.cos(yang), 0],
                             [0, 0, 0, 1.25]])

        # z axis rotator
        zrotator = np.array([[math.cos(zang), -math.sin(zang), 0, 0],
                             [math.sin(zang), math.cos(zang), 0, 0],
                             [0, 0, 1, 0],
                             [0, 0, 0, 1.25]])

        # composed rotation matrix with (xrotator, yrotator, zrotator)
        allrotators = np.dot(np.dot(xrotator, yrotator), zrotator)

        # translation matrix - give depth
        translation = np.array([[1, 0, 0, 0],
                                [0, 1, 0, 0],
                                [0, 0, 1, f],
                                [0, 0, 0, 1]])

        # returning 3d image back to 2d
        to2d = np.array([[f, 0, w / 2, 0],
                         [0, f, h / 2, 0],
                         [0, 0, 1, 0]])

        # multiplication of all matrices: into3d * allrotators, then * translation, then * into2d
        return np.dot(to2d, np.dot(translation, np.dot(allrotators, to3d)))
