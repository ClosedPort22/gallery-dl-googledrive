# -*- coding: utf-8 -*-

"""Extractors for Dropbox"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, exception
from gallery_dl.cache import cache


class DropboxShareExtractor(Extractor):
    """Extractor for shared Dropbox files and folders"""
    category = "dropbox"
    subcategory = "share"
    directory_fmt = ("{category}", "{path[0]:?//}", "{path[1]:?//}",
                     "{path[2]:?//}", "{path[3:]:J - /}")
    filename_fmt = (
        "{share_token[secureHash]|share_token[linkKey]}{filename:?_//}."
        "{extension}")
    archive_fmt = "{share_token[linkKey]}_{share_token[secureHash]}"
    cookiedomain = ".dropbox.com"
    root = "https://www.dropbox.com"
    pattern = (r"(?:https?://)?(?:www\.)?dropbox\.com/s"
               r"(?:h/([0-9a-z]+)/([0-9a-zA-Z\-_]+)(/[^?#&]+)?|/([0-9a-z]+))")
    test = (
        # /s/ file
        ("https://www.dropbox.com/s/bkyoamgqop7kpio/data.txt", {
            "count": 1,
            "pattern": "/sharing/fetch_user_content_link$",
            "keyword": {"share_token": {
                "linkKey"   : "bkyoamgqop7kpio",
                "secureHash": None,
            }},
            "content": "b31735ac7a09c30491f7c3e7069db7798f9c92c4",
        }),
        # /sh/ file
        ("https://www.dropbox.com/sh/jj1fzcilzq5k8mf/AADUxHrQYsUzHbziKkEBxc_ca"
         "/000-CITESTE%20-%20READ%20%21%21%21.txt?dl=0", {
             "count": 1,
             "pattern": "/sharing/fetch_user_content_link$",
             "keyword": {"share_token": {
                 "linkKey"   : "jj1fzcilzq5k8mf",
                 "secureHash": "AADUxHrQYsUzHbziKkEBxc_ca",
             }},
             "content": "ec85f71291ea39748fe69e8f1c8b504beaa46e9a",
         }),
        # folder
        ("https://www.dropbox.com/sh/6dwvd4l0fka2jju/"
         "AADDIWyKVs6uQ0YjYYRtP6Xya?dl=0", {
             "count": 3,
             "pattern": "/sharing/fetch_user_content_link$",
             "keyword": {
                 "date"     : "type:datetime",
                 "extension": "re:txt|mdmp",
                 "filename" : str,
                 "filesize" : int,
                 "path"     : ["CyberLink"],
             }
         }),
        # 404 file
        ("https://www.dropbox.com/s/foobar123456789", {
            "content": "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # empty
        }),
        # 404 folder
        ("https://www.dropbox.com/sh/foobar123456789/"
         "AADUxHrQYsUzHbziKkEBxc_ca", {
             "content": "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # empty
         }),
        # subfolder
        ("https://www.dropbox.com/sh/bwjmb40klp8pj2t/"
         "AACgqigq8Jwwio0mgEKgrr2Wa?dl=0", {
             "count": 2,
             "pattern": "/sharing/fetch_user_content_link$",
             "keyword": {"path": ["Hacknet Save backup", "Disk_1"]},
             "content": "15feabe8e776daad90dc781c7d122852ea266b49",
         }),
        # 'folder' not in response ('{}')
        ("https://www.dropbox.com/sh/d4j7iqvmlc1lc1r/jC6LvcSKqT/"
         "afrojack_presskit_2014.zip", {
             "count": 1
         }),

        # sub_path
        ("https://www.dropbox.com/sh/9olujy823al5trq/"
         "AAA4RuSe6yhY6sMMxg8DNneaa/Fotos%20Obra?dl=0", {
             "count": 5,  # no zipping
             "keyword": {"path": ["Fotos Obra"]},
         }),
        # empty folder
        ("https://www.dropbox.com/sh/a1mg7fhjsaudrsl/"
         "AAAkxX7szMwDisIkBeNKYASea/Mechanical/Chassis Assy/"
         "2D Drawings?dl=0", {
             "count": 0,
             "keyword": "3244d71b9f0a5f43dd9c41bfaee97355c27b9a7c",
         }),
        ("https://www.dropbox.com/sh/bwjmb40klp8pj2t/"
         "AAC_25FuKfruJwoD6Sw2ZEbYa/foo/bar?dl=0"),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.key = match.group(1) or match.group(4)
        self.secure_hash = match.group(2)
        path = match.group(3)
        if path:
            self.path = text.unquote(path.strip("/")).split("/")
            self.base = []
        else:
            self.path = []
            self.base = None
        self.api = DropboxWebAPI(self)

    def items(self):
        # https://dl.dropbox.com/s/{key}/[arbitrary filename]
        # https://dl.dropbox.com/sh/{key}/{hash}/[correct filename only]
        # https://dl.dropbox.com/sh/{key}/{hash}/[does not work for folders]
        if self.secure_hash:
            try:
                yield from self.files(self.secure_hash)
                return
            except exception.NotFoundError:
                pass
        data = {
            "extension"  : "",
            "share_token": {
                "linkKey"   : self.key,
                "secureHash": self.secure_hash,
            },
            "path": (),
        }
        yield Message.Directory, data
        yield self.commit(self.url, data)

    def commit(self, url, data):
        post_data = {
            "is_xhr": "true",
            "t"  : self.api.token,
            "url": url,
        }

        def _validate(response):
            # * declared inside 'commit' to be able to access 'data'
            # * delegate URL extraction to the downloader to be able to
            #   save 1 API request per file when skipping downloaded files
            if "filename" in response.headers.get("content-disposition", ""):
                return True
            if "text/plain" not in response.headers.get("content-type", ""):
                return False
            url = response.text
            if url[:8] != "https://":
                print(url)
                return False
            del data["_http_method"]
            del data["_http_data"]
            return url

        data.update({
            "_http_validate": _validate,
            "_http_method": "POST",
            "_http_data"  : post_data,
        })
        return \
            Message.Url, self.root + "/sharing/fetch_user_content_link", data

    @staticmethod
    def prepare(file):
        """Adjust the content of a file object"""
        file["filesize"] = file.pop("bytes")
        file["date"] = text.parse_timestamp(file["ts"])
        text.nameext_from_url(file["filename"], file)

    def files(self, secure_hash):
        """Recursively yield files in a folder"""
        folders = []
        parent_data, items = \
            self.api.folder_content(self.key, secure_hash, "/".join(self.path))
        if self.base is None:
            self.base = [parent_data["filename"]]
        folder_data = {"parent": parent_data,
                       "path": self.base + self.path}
        yield Message.Directory, folder_data
        for item in items:
            if item["is_dir"] or item["is_symlink"]:  # ?
                folders.append(item)
                continue
            self.prepare(item)
            item.update(folder_data)
            yield self.commit(item["shared_link_info"]["url"], item)

        for folder in folders:
            self.path.append(folder["filename"])
            yield from self.files(folder["share_token"]["secureHash"])
            self.path.pop()


class DropboxWebAPI():
    """Interface for Dropbox web API"""

    API_ROOT = "https://www.dropbox.com"

    def __init__(self, extractor):
        self.request = extractor.request
        self.cookiejar = extractor.session.cookies
        cookiedomain = extractor.cookiedomain

        self.token = token = self._fetch_token()
        self.cookiejar.set("t", token, domain=cookiedomain)

    @cache(maxage=365*86400)
    def _fetch_token(self):
        self.request(self.API_ROOT, method="HEAD")
        return self.cookiejar["t"]

    def folder_content(self, link_key, secure_hash, sub_path=""):
        """Return a tuple of (folder_info, folder_content)"""
        result = self._folder_content_impl(link_key, secure_hash, sub_path)
        return next(result), result

    def _folder_content_impl(self, link_key, secure_hash, sub_path):
        strings = ("share_permission", "share_token", "shared_link_info")
        data = {
            "link_key"   : link_key,
            "link_type"  : "s",
            "secure_hash": secure_hash,
            "sub_path"   : sub_path,
        }
        folder = None
        voucher = None
        while True:
            data["voucher"] = voucher

            response = self._call(
                "/list_shared_link_folder_entries", data, notfound="folder")
            if folder is None:
                folder = response.get("folder")
                if not folder:
                    raise exception.NotFoundError("folder")
                for s in strings:
                    folder[s] = response["folder_" + s]
                yield folder
            entries = response["entries"]
            for s in strings:
                for entry, metadata in zip(entries, response[s + "s"]):
                    entry[s] = metadata
            yield from entries

            if not response["has_more_entries"]:
                break
            voucher = response.get("next_request_voucher")

    def _call(self, endpoint, data, **kwargs):
        data.update({"is_xhr": "true", "t": self.token})
        return self.request(self.API_ROOT + endpoint, data=data,
                            method="POST", **kwargs).json()
