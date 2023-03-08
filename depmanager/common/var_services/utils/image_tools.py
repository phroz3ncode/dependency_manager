import os

from PIL import Image


def write_image_data(filedir: str, file_path: str, image_data: Image.Image):
    os.makedirs(filedir, exist_ok=True)
    image_data.save(file_path)
