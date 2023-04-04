# -*- coding: utf-8 -*-

"""Extractors for Mediafire"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, exception
import itertools


BASE_PATTERN = r"(?:https?://)?(?:www\.)?mediafire\.com"


class MediafireExtractor(Extractor):
    """Base class for Mediafire extractors"""
    category = "mediafire"
    filename_fmt = "{quickkey}.{extension}"
    archive_fmt = "{quickkey}"
    root = "https://www.mediafire.com"

    def url_data_from_id(self, id):
        """Get URL and data from file ID"""
        url = "{}/download/{}".format(self.root, id)
        data = {"quickkey": id, "extension": "", "_http_validate": _validate}

        return url, data


# delegate url extraction to the downloader to be able to skip already
# downloaded files without making any requests
def _validate(response):
    # direct download
    if "content-disposition" in response.headers:
        return True
    # download response content
    txt = response.text
    url = text.extr(txt, "window.location.href", ";").strip(" ='") or \
        text.extr(text.extr(
            txt, '<a class="input popsok"', "</a>"), 'href="', '"')
    if url:
        return url
    return False  # return True to save response as file


class MediafireFileExtractor(MediafireExtractor):
    """Extractor for Mediafire files"""
    subcategory = "file"
    pattern = BASE_PATTERN + \
        r"/(?:download(?:\.php\?|/)|file(?:_premium)?/|\?)([0-9a-z]+)"
    test = (
        # direct download
        ("http://www.mediafire.com/file/ise1i57s4dfkgc8", {
            "count": 1,
            "pattern": r"^https://www\.mediafire\.com/download/",
            "keyword": {"quickkey": "ise1i57s4dfkgc8", "extension": ""},
        }),
        # redirects to webpage
        ("https://www.mediafire.com/download/kt9z2284k2sg8ay", {
            "count": 1,
            "pattern": r"^https://www\.mediafire\.com/download/",
            "content": "9c21def0d0906b4db9fdf673e6026b8ee9772d4f",
        }),
        # 404
        ("https://www.mediafire.com/download/foobar123456789", {
            "count": 1,
            "content": "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # empty
        }),

        ("https://www.mediafire.com/?u79eqi2we39k343"),
        ("https://www.mediafire.com/file_premium/foobar123456789"),
        ("http://www.mediafire.com/download.php?u79eqi2we39k343"),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.id = match.group(1)

    def items(self):
        url, data = self.url_data_from_id(self.id)

        yield Message.Directory, data
        yield Message.Url, url, data


class MediafireFolderExtractor(MediafireExtractor):
    """Extractor for Mediafire folders"""
    subcategory = "folder"
    directory_fmt = ("{category}", "{path[0]:?//}", "{path[1]:?//}",
                     "{path[2]:?//}", "{path[3:]:J - /}")
    filename_fmt = "{quickkey}_{filename}.{extension}"
    pattern = BASE_PATTERN + r"/folder/([0-9a-z]+)"
    test = (
        # flat
        ("https://www.mediafire.com/folder/w396pruckzoxt", {
            "pattern": MediafireFileExtractor.pattern,
            "count": 2,
            "keyword": {
                "date"     : "type:datetime",
                "extension": "pdf",
                "filename" : "re:^LIHKG_",
                "filesize" : int,
                "path"     : list,
            },
        }),
        # request metadata for base folder
        ("https://www.mediafire.com/folder/w1sa3pkoo1we2", {
            "options": (("metadata", True),),
            "count": 6,
            "keyword": {
                "parent": {"name": "Johnny Reb III"},
                "path"  : ["Johnny Reb III"],
            },
        }),
        # nested folder
        ("https://www.mediafire.com/folder/9a6a91cgbd7m8", {
            "count": 36,
        }),
        # prefer native URL
        ("https://www.mediafire.com/folder/ka4p1kju36qcq/Newgen+Faces", {
            "pattern": "/file_premium/",
            "count": ">= 1",
        }),

        # not found (400 Bad Request)
        ("https://www.mediafire.com/folder/foobar123456789", {
            "options": (("metadata", True),),
            "exception": exception.HttpError,
        }),
        ("https://www.mediafire.com/folder/foobar123456789", {
            "exception": exception.HttpError,
        }),
    )

    def __init__(self, match):
        MediafireExtractor.__init__(self, match)
        self.id = match.group(1)
        self.api = MediafireWebAPI(self)
        self.path = []

    @staticmethod
    def prepare(file):
        """Adjust the content of a file or folder object"""
        file["date"] = text.parse_datetime(
            file["created_utc"], "%Y-%m-%dT%H:%M:%S%z")
        if "filename" in file:
            text.nameext_from_url(file["filename"], file)
        if "size" in file:
            file["filesize"] = text.parse_int(file.pop("size"))

    def metadata(self):
        if not self.config("metadata", False):
            return {"folderkey": self.id}
        data = self.api.folder_info(self.id)
        self.prepare(data)
        return data

    def items(self):
        yield from self.files(self.id, self.metadata())

    def files(self, id, parent_data):
        """Recursively yield files in a folder"""
        self.path.append(parent_data.get("name") or parent_data["folderkey"])

        folder_data = {"parent": parent_data, "path": self.path.copy()}
        yield Message.Directory, folder_data

        for file in self.api.folder_content(id, "files"):
            self.prepare(file)
            url, data = self.url_data_from_id(file["quickkey"])
            data.update(folder_data)
            data.update(file)

            try:
                native_url = data["links"]["normal_download"]
            except KeyError:
                native_url = ""
            yield Message.Url, native_url or url, data

        for folder in self.api.folder_content(id, "folders"):
            self.prepare(folder)
            yield from self.files(folder["folderkey"], folder)

        self.path.pop()


class MediafireWebAPI():
    """Interface for Mediafire web API"""

    PAGINATION_PARAMS = {
        "filter"  : "all",
        "order_by": "name",
        "order_direction": "asc",
        "version" : "1.5",
    }

    def __init__(self, extractor):
        self.request = extractor.request

    def folder_info(self, folder_key, recursive=True, details=True):
        """Return folder info"""
        if not isinstance(folder_key, str):
            # assume iterable
            folder_key = ",".join(folder_key)
        params = {
            "recursive" : "yes" if recursive else "no",
            "details"   : "yes" if details else "no",
            "folder_key": folder_key,
        }
        response = self._call("/folder/get_info.php", params, method="POST")
        return response.get("folder_info") or response["folder_infos"]

    def folder_content(self, folder_key, content_type):
        """Yield folder content (files or subfolders)"""
        return self._pagination(
            "/folder/get_content.php", "folder_content", content_type,
            {"content_type": content_type, "folder_key": folder_key})

    def _pagination(self, endpoint, key1, key2, params):
        params.update(self.PAGINATION_PARAMS)
        for cn in itertools.count(1):
            params["chunk"] = cn
            chunk = self._call(endpoint, params)
            yield from chunk[key1][key2]
            more = chunk[key1].get("more_chunks")
            if more == "no" or not more:
                break

    def _call(self, endpoint, params, **kwargs):
        """Call an API endpoint"""
        params["response_format"] = "json"
        url = "https://www.mediafire.com/api/1.4" + endpoint
        return self.request(url, params=params, **kwargs).json()["response"]
