import json
import os

from django.conf import settings
from django.contrib.staticfiles.storage import ManifestFilesMixin, StaticFilesStorage
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage, SpooledTemporaryFile


class ManifestStaticFilesStorageFileSystem(ManifestFilesMixin, StaticFilesStorage):
    pass


class CustomS3Boto3Storage(S3Boto3Storage):
    """Custom S3 storage class to workaround a bug when using ManifestFilesMixin.

    See: https://github.com/jschneier/django-storages/issues/382
    """

    def _save_content(self, obj, content, parameters):
        content.seek(0, os.SEEK_SET)
        content_autoclose = SpooledTemporaryFile()
        content_autoclose.write(content.read())
        super()._save_content(obj, content_autoclose, parameters)
        if not content_autoclose.closed:
            content_autoclose.close()


class ManifestStaticFilesStorageS3(ManifestFilesMixin, CustomS3Boto3Storage):
    """Saves and looks up staticfiles.json in Project directory.

    See: https://stackoverflow.com/questions/50387587
    """

    manifest_location = os.path.abspath(settings.BASE_DIR)
    manifest_storage = FileSystemStorage(location=manifest_location)

    def read_manifest(self):
        try:
            with self.manifest_storage.open(self.manifest_name) as manifest:
                return manifest.read().decode("utf-8")
        except IOError:
            return None

    def save_manifest(self):
        payload = {"paths": self.hashed_files, "version": self.manifest_version}
        if self.manifest_storage.exists(self.manifest_name):
            self.manifest_storage.delete(self.manifest_name)
        contents = json.dumps(payload).encode("utf-8")
        self.manifest_storage._save(self.manifest_name, ContentFile(contents))
