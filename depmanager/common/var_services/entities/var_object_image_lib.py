import io
import os
from collections import defaultdict
from io import BytesIO
from os import path
from typing import Optional
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

import imagequant
import PIL
from PIL import Image
from PIL import UnidentifiedImageError

from depmanager.common.shared.cached_property import cached_property
from depmanager.common.shared.enums import MEGABYTE
from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.shared.tools import are_substrings_in_str
from depmanager.common.var_services.enums import IMAGE_LIB_DIR
from depmanager.common.var_services.enums import TEMP_VAR_NAME
from depmanager.common.var_services.enums import Ext
from depmanager.common.var_services.utils.var_type import VarType
from depmanager.common.var_services.var_config import IMAGE_RESOURCE_DIR

PIL.Image.MAX_IMAGE_PIXELS = 225000000


def _downsample_image_if_possible(img: Image, allow_4k_scaling=False) -> tuple[Image, bool]:
    desired = None
    if img.height > 4096 and img.width > 4096:
        desired = (4096, 4096)
    if allow_4k_scaling and img.height >= 4000 and img.width >= 4000:
        desired = (2048, 2048)

    if desired:
        return img.resize(desired, Image.LANCZOS), True
    return img, False


class VarObjectImageLib:
    contains: dict[str, bool]
    dependencies: list[str]
    var_type: VarType

    file_path: str
    directory: str
    sub_directory: str
    clean_name: str
    package_name: str
    namelist: list[str]
    infolist: list[tuple[str, int]]
    files: defaultdict[str, set[str]]

    DEPTH_IMAGES = ["_N", "_G", "_S", "norm", "Norm", "NORM", "gloss", "Gloss", "GLOSS", "spec", "Spec", "SPEC"]

    @cached_property
    def image_directory(self) -> str:
        return os.path.join(IMAGE_LIB_DIR, self.sub_directory)

    @cached_property
    def image_name(self) -> str:
        return os.path.join(self.image_directory, f"{self.clean_name}")

    @cached_property
    def is_compressible(self) -> bool:
        compressible_jpg = [
            item for item in self.infolist if path.splitext(item[0])[1] == Ext.JPG and item[1] > MEGABYTE
        ]
        compressible_png = [
            item for item in self.infolist if path.splitext(item[0])[1] == Ext.PNG and item[1] > 5 * MEGABYTE
        ]
        return len(compressible_jpg) > 0 or len(compressible_png) > 0

    @cached_property
    def clothing_image_files(self) -> list[str]:
        files = []
        for file in self.namelist:
            file_parts = path.splitext(file)
            if file_parts[1].lower() in (Ext.JPG, Ext.PNG, Ext.TIF) and "clothing" in file.lower():
                files.append(file)
        return files

    @cached_property
    def removable_image_files(self) -> list[str]:
        files = []
        for file in self.namelist:
            file_parts = path.splitext(file)
            if file_parts[1].lower() == Ext.PSD:
                files.append(file)
        return files

    @cached_property
    def texture_image_files(self) -> list[str]:
        files = []
        for file in self.namelist:
            file_parts = path.splitext(file)
            if file_parts[1].lower() in (Ext.JPG, Ext.PNG, Ext.TIF) and "clothing" not in file.lower():
                files.append(file)
        return files

    def _write_image_to_buffer(self, img: Image, img_format: str, always_optimize=False):
        buffer = BytesIO()
        if img_format == "PNG":
            if always_optimize or self._should_quantize_image(img):
                img = imagequant.quantize_pil_image(
                    img,
                    dithering_level=1.0,  # from 0.0 to 1.0
                    max_colors=256,  # from 1 to 256
                )
            img.save(buffer, img_format)
        elif img_format in ("TIF", "TIFF"):
            img.save(buffer, img_format, compression="jpeg", quality=95, optimize=True)
        else:
            img.save(buffer, img_format, quality=95, optimize=True)
        return buffer

    @staticmethod
    def _should_quantize_image(img: Image):
        colors = img.getcolors(maxcolors=100000)
        if colors is None:
            return False

        # Check if quantization could be a good option
        colors = sorted(colors, reverse=True)
        primary_colors = sum(c[0] for c in colors[:256])
        all_colors = sum(c[0] for c in colors)
        if len(colors) <= 256:
            return True
        # Else if dominant pixels make up most of the image
        if (primary_colors / all_colors) > 0.5:
            return True

        return False

    def _compress_image_if_possible(self, img_data: bytes, img_filename: str, png_only=False):
        original_img_data = BytesIO(img_data)
        original_img = Image.open(original_img_data)
        original_image_size = original_img_data.getbuffer().nbytes
        original_image_format = original_img.format

        # Only process PNGs
        if png_only and original_image_format != "PNG":
            return None

        # Do not process non-square images, these can have issues rescaling
        if original_img.height != original_img.width:
            return None

        # Depth images don't need many colors
        image_is_for_depth_only = are_substrings_in_str(img_filename, self.DEPTH_IMAGES)
        # Non-texture images don't need as high a resolution in some cases
        image_is_not_texture = img_filename not in self.texture_image_files
        # Small images are less then 3MB
        image_is_small = original_image_size < (2 * MEGABYTE)

        # Only do 4k->2k scaling for depth and non-texture images
        allow_4k_scaling = image_is_not_texture and image_is_for_depth_only and not png_only

        img_downsampled, is_downsampled = _downsample_image_if_possible(original_img, allow_4k_scaling=allow_4k_scaling)
        if not is_downsampled and image_is_small:
            return None

        # Try to store the image at 95 quality
        try:
            img_out = self._write_image_to_buffer(
                img_downsampled, original_image_format, always_optimize=image_is_for_depth_only
            )
            ratio = img_out.getbuffer().nbytes / original_image_size
            if ratio < 0.8:
                return img_out
            # Give up and return the original image
            return None

        except ValueError:
            return None

    def compress(self, png_only=False):
        # print(f"\nCOMPRESSING: {self.file_path}")
        pre_stat_mb = os.stat(self.file_path).st_size / MEGABYTE
        image_bytes_pre = 0
        image_bytes_post = 0
        images_updated = False
        temp_file = path.join(self.directory, TEMP_VAR_NAME)
        with ZipFile(temp_file, "w", ZIP_DEFLATED) as zf_dest:
            with ZipFile(self.file_path, "r") as zf_src:
                progress = ProgressBar(len(zf_src.infolist()), description=f"COMPRESSING: {self.clean_name}")
                for item in zf_src.infolist():
                    progress.inc()
                    if item.filename in self.removable_image_files:
                        print(f"REMOVED {self.clean_name}: {item.filename}")
                        continue
                    if item.filename in self.clothing_image_files or item.filename in self.texture_image_files:
                        try:
                            image_data = zf_src.read(item.filename)
                            image_data_size = io.BytesIO(image_data).getbuffer().nbytes
                            image_bytes_pre += image_data_size

                            image_write = self._compress_image_if_possible(image_data, item.filename, png_only=png_only)
                            if image_write is not None:
                                image_bytes_post += image_write.getbuffer().nbytes
                                images_updated = True
                                print(f"UPDATED {self.clean_name}: {item.filename}")
                                zf_dest.writestr(item.filename, image_write.getvalue(), ZIP_DEFLATED)
                            else:
                                image_bytes_post += image_data_size
                                zf_dest.writestr(item.filename, zf_src.read(item.filename), ZIP_DEFLATED)
                        except UnidentifiedImageError:
                            zf_dest.writestr(item.filename, zf_src.read(item.filename), ZIP_DEFLATED)
                    else:
                        zf_dest.writestr(item.filename, zf_src.read(item.filename), ZIP_DEFLATED)

        print("")
        if images_updated:
            post_stat_mb = os.stat(temp_file).st_size / MEGABYTE
            savings_raw = pre_stat_mb - post_stat_mb
            savings_ratio = post_stat_mb / pre_stat_mb
            image_ratio = image_bytes_post / image_bytes_pre
            # If we saved more than 10MB, or the compressed size decreased by 20% or the uncompressed size
            # of the images decreased by 40% then it is worth keeping the compression
            if savings_raw >= 10 or savings_ratio <= 0.8 or image_ratio <= 0.6:
                print(f"{self.clean_name} SPACE SAVED: {savings_raw}MB, {savings_ratio}ZR, {image_ratio}IR")
                os.remove(self.file_path)
                os.rename(temp_file, self.file_path)
                return pre_stat_mb - post_stat_mb
            print(
                f"{self.clean_name} INSUFFICIENT SAVINGS: {savings_raw:.2f}MB, {savings_ratio:.2f}ZR, {image_ratio:.2f}IR"
            )
        os.remove(temp_file)
        return 0

    def get_image(self, image_name, image_format) -> Image.Image:
        try:
            with ZipFile(self.file_path, "r") as zf_src:
                image_data = zf_src.read(f"{image_name}{image_format}")
        except KeyError:
            with ZipFile(self.file_path, "r") as zf_src:
                image_data = zf_src.read(f"{image_name}{image_format.upper()}")

        stream = BytesIO(image_data)
        img = Image.open(stream)
        if img.height != 400 and img.width != 400:
            img = img.resize((400, 400), Image.LANCZOS)

        if isinstance(img.info.get("transparency"), bytes):
            img = img.convert("RGBA")
        img = img.convert("RGB")
        return img

    def extract_identity_image_data(self) -> Optional[Image.Image]:
        files = self.files
        identities = None
        source_image_format = Ext.JPG
        if self.var_type.type in self.var_type.types_with_json:
            if len(files["saves"] & files["images"]) > 0:
                identities = files["saves"] & files["images"]
            elif len(files["appearance"] & files["images"]) > 0:
                identities = files["appearance"] & files["images"]

        if identities is None:
            if len(files["clothing"] & files["images"]) > 0:
                identities = files["clothing"] & files["images"]
            elif len(files["clothing_vap"] & files["images"]) > 0:
                identities = files["clothing_vap"] & files["images"]
            elif len(files["hair"] & files["images"]) > 0:
                identities = files["hair"] & files["images"]
            elif len(files["hair_vap"] & files["images"]) > 0:
                identities = files["hair_vap"] & files["images"]
            elif len(files["images"]) > 0:
                identities = files["images"]
            elif len(files["images_png"]) > 0:
                identities = files["images_png"]
                source_image_format = Ext.PNG
            elif self.var_type.type in self.var_type.types_with_default_image:
                identities = None
            else:
                return None

        if identities is None:
            image_data = self.extract_default_image_data(self.var_type.type)
        else:
            if len(identities) == 1:
                identity = identities.pop()
            else:
                identity = self.get_best_image(identities)
            image_data = self.get_image(identity, source_image_format)
        return image_data

    def get_best_image(self, identities):
        matches = [ident for ident in identities if path.basename(ident) == self.package_name]
        if len(matches) >= 1:
            return matches[0]

        # Try and not use weird images if possible
        ignores = ["_N", "_G", "_S", "norm", "Norm", "NORM", "gloss", "Gloss", "GLOSS", "spec", "Spec", "SPEC"]
        clean_identities = [ident for ident in identities if all(ig not in path.basename(ident) for ig in ignores)]
        clean_identities = sorted(clean_identities)
        if len(clean_identities) == 0:
            return sorted(identities)[0]

        # Try to prioritize the best descriptive images when possible
        priorities = [
            "outfit",
            "dress",
            "gown",
            "sweater",
            "top",
            "shirt",
            "suit",
            "jacket",
            "vest",
            "skirt",
            "bra",
            "pants",
            "bottom",
            "lower",
            "face",
            "torso",
        ]
        for priority in priorities:
            matches = [ident for ident in clean_identities if priority in str.lower(path.basename(ident))]
            if len(matches) == len(clean_identities):
                continue
            if len(matches) >= 1:
                return matches[0]

        return clean_identities[0]

    def extract_default_image_data(self, default_type):
        if default_type == VarType.ASSET:
            return Image.open(path.join(IMAGE_RESOURCE_DIR, "unity.jpg")).convert("RGB")
        if default_type == VarType.MORPH:
            return Image.open(path.join(IMAGE_RESOURCE_DIR, "morph.jpg")).convert("RGB")
        if default_type == VarType.PLUGIN:
            return Image.open(path.join(IMAGE_RESOURCE_DIR, "plugin.jpg")).convert("RGB")
        if default_type == VarType.SOUND:
            return Image.open(path.join(IMAGE_RESOURCE_DIR, "sound.jpg")).convert("RGB")
        if default_type == VarType.UNITY:
            return Image.open(path.join(IMAGE_RESOURCE_DIR, "unity.jpg")).convert("RGB")
        raise ValueError("Type does not support default image data")
