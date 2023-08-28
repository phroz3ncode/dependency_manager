from zipfile import ZIP_DEFLATED
from zipfile import ZIP_STORED
from zipfile import ZipFile


class ZipRead:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.zip_file = None

    def __enter__(self) -> ZipFile:
        # noinspection PyArgumentList
        self.zip_file = ZipFile(self.file_path, mode="r", metadata_encoding="UTF-8")
        return self.zip_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.zip_file:
            self.zip_file.close()


class ZipWrite:
    def __init__(self, file_path: str, compress: bool = True):
        self.file_path = file_path
        self.compress = compress
        self.zip_file = None

    def __enter__(self) -> ZipFile:
        if self.compress:
            self.zip_file = ZipFile(self.file_path, mode="w", compression=ZIP_DEFLATED)
        else:
            self.zip_file = ZipFile(self.file_path, mode="w", compression=ZIP_STORED)
        return self.zip_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.zip_file:
            self.zip_file.close()


class ZipReadInto:
    def __init__(self, read_path: str, write_path: str, compress=True):
        self.read_path = read_path
        self.write_path = write_path
        self.compress = compress
        self.zf_read = None
        self.zf_write = None

    def __enter__(self) -> (ZipFile, ZipFile):
        # noinspection PyArgumentList
        self.zf_read = ZipFile(self.read_path, mode="r", metadata_encoding="UTF-8")

        if self.compress:
            self.zf_write = ZipFile(self.write_path, mode="w", compression=ZIP_DEFLATED)
        else:
            self.zf_write = ZipFile(self.write_path, mode="w", compression=ZIP_STORED)
        return self.zf_read, self.zf_write

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.zf_read:
            self.zf_read.close()
        if self.zf_write:
            self.zf_write.close()
