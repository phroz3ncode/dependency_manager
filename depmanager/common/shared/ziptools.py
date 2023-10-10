from typing import Optional
from zipfile import ZIP_DEFLATED
from zipfile import ZIP_STORED
from zipfile import ZipFile


class ZipObj:
    zip_file: Optional[ZipFile]

    def __init__(self, file_path: str, compress: bool = True):
        self.file_path = file_path
        self.compress = compress
        self.zip_file = None

    # noinspection PyArgumentList
    # pylint: disable=consider-using-with
    def read(self):
        if not self.zip_file:
            self.zip_file = ZipFile(self.file_path, mode="r")

    def write(self):
        if not self.zip_file:
            if self.compress:
                self.zip_file = ZipFile(self.file_path, mode="w", compression=ZIP_DEFLATED)
            else:
                self.zip_file = ZipFile(self.file_path, mode="w", compression=ZIP_STORED)

    def close(self):
        if self.zip_file:
            self.zip_file.close()
            self.zip_file = None


class ZipRead:
    def __init__(self, file_path: str):
        self.zip = ZipObj(file_path)

    def __enter__(self) -> ZipFile:
        self.zip.read()
        return self.zip.zip_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.zip.close()


class ZipWrite:
    def __init__(self, file_path: str, compress: bool = True):
        self.zip = ZipObj(file_path, compress=compress)

    def __enter__(self) -> ZipFile:
        self.zip.write()
        return self.zip.zip_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.zip.close()


class ZipReadInto:
    zip_read: ZipObj
    zip_write: ZipObj

    def __init__(self, read_path: str, write_path: str, compress=True):
        self.zip_read = ZipObj(read_path)
        self.zip_write = ZipObj(write_path, compress=compress)

    def __enter__(self) -> (ZipFile, ZipFile):
        self.zip_read.read()
        self.zip_write.write()
        return self.zip_read.zip_file, self.zip_write.zip_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.zip_read.close()
        self.zip_write.close()
