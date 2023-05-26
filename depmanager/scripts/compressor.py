# import os
# from io import BytesIO
#
# from PIL import Image
#
# from depmanager.common.shared.enums import MEGABYTE
# from depmanager.common.var_services.enums import Ext
#
# file_path = "E:\\Downloads\\vam\\Custom\\Atom\\Person\\Textures"
#
#
# def _compress_image_if_possible(filepath: str, allow_4k_scaling=False, allow_large_updates=True):
#     def _downsample_image_if_possible(img: Image, allow_4k_scaling=False) -> tuple[Image, bool]:
#         desired = None
#         if img.height >= 8000 and img.width >= 8000:
#             desired = (4096, 4096)
#         elif allow_4k_scaling and img.height >= 4000 and img.width >= 4000:
#             desired = (2048, 2048)
#
#         if desired:
#             return img.resize(desired, Image.LANCZOS), True
#         return img, False
#
#     def _write_image_to_buffer(img: Image, img_format: str, quality=95):
#         return buffer
#
#     original_size = os.stat(filepath).st_size / MEGABYTE
#     with open(filepath, "rb") as f:
#         original_img = Image.open(f)
#
#         image_format = original_img.format
#         if original_img.height != original_img.width:
#             return None
#
#         img_downsampled, is_downsampled = _downsample_image_if_possible(original_img, allow_4k_scaling=allow_4k_scaling)
#         if not is_downsampled and original_size < 5.0:
#             return None
#
#         # Try to store the image at 95 quality
#         try:
#             buffer = BytesIO()
#             img_downsampled.save(buffer, image_format, quality=95, optimize=True)
#             buffer_size = buffer.getbuffer().nbytes / MEGABYTE
#             ratio = buffer_size / original_size
#             if ratio < 0.8:
#                 return buffer
#             # Give up and return the original image
#             return None
#
#         except ValueError:
#             return None
#
#
# for root, _, files in os.walk(file_path):
#     print(root)
#     for file in files:
#         if os.path.splitext(file)[-1] in (Ext.JPG):
#             img_path = os.path.join(root, file)
#             img_out = _compress_image_if_possible(img_path)
#             if img_out is not None:
#                 print(f"Updating {img_path}")
#                 with open(img_path, "wb") as f:
#                     f.write(img_out.getvalue())
