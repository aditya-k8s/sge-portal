"""
Upload validation shared by the project file, bill and image forms.

Uploads previously reached disk with no size or type check at all: a client
could attach a 2 GB file, or an .html/.svg file that the browser would later
execute in the site's own origin when opened from the media URL.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

# Documents and drawings an engineering client would legitimately attach.
DOCUMENT_EXTENSIONS = {
    '.pdf', '.png', '.jpg', '.jpeg', '.webp', '.gif',
    '.dwg', '.dxf', '.step', '.stp', '.igs', '.iges', '.stl',
    '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.zip',
}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}


def _extension(filename):
    name = (filename or '').lower()
    dot = name.rfind('.')
    return name[dot:] if dot != -1 else ''


def _human_mb(num_bytes):
    return f'{num_bytes / (1024 * 1024):.1f} MB'


@deconstructible
class UploadValidator:
    """
    Reject uploads that are too large or of an unexpected type.

    Deconstructible so it can be attached to a model field without breaking
    migrations, though it is currently used from forms.
    """

    def __init__(self, allowed_extensions=None, max_mb=None):
        self.allowed_extensions = set(allowed_extensions or DOCUMENT_EXTENSIONS)
        self.max_mb = max_mb

    @property
    def limit_mb(self):
        if self.max_mb is not None:
            return self.max_mb
        return getattr(settings, 'MAX_UPLOAD_SIZE_MB', 10)

    def __call__(self, upload):
        if not upload:
            return upload

        size = getattr(upload, 'size', None)
        if size is not None and size > self.limit_mb * 1024 * 1024:
            raise ValidationError(
                f'That file is {_human_mb(size)}. The maximum is '
                f'{self.limit_mb} MB — please compress it or split it up.'
            )

        extension = _extension(getattr(upload, 'name', ''))
        if extension not in self.allowed_extensions:
            allowed = ', '.join(sorted(e.lstrip('.') for e in self.allowed_extensions))
            raise ValidationError(
                f'"{extension or "no extension"}" files are not accepted. '
                f'Allowed types: {allowed}.'
            )
        return upload

    def __eq__(self, other):
        return (
            isinstance(other, UploadValidator)
            and other.allowed_extensions == self.allowed_extensions
            and other.max_mb == self.max_mb
        )


validate_document_upload = UploadValidator(DOCUMENT_EXTENSIONS)
validate_image_upload = UploadValidator(IMAGE_EXTENSIONS, max_mb=5)
