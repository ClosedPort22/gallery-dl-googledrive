# -*- coding: utf-8 -*-

"""Extractors for Yandex Disk"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import util, text, exception


class YandexdiskShareExtractor(Extractor):
    """Extractor for shared Yandex Disk files and folders"""
    category = "yandexdisk"
    subcategory = "share"
    directory_fmt = ("{category}", "{path[0]:?//}", "{path[1]:?//}",
                     "{path[2]:?//}", "{path[3:]:J - /}")
    archive_fmt = "{resource_id}_{revision}"
    # must use disk.yandex.ru instead of .net to get 'newSk'
    root = "https://disk.yandex.ru"
    pattern = (r"(?:https?://)?(?:disk\.yandex\.(?:net|com(?:\.tr)?|ru|ua|kz)"
               r"|yadi\.sk|yadisk\.cc)"
               r"/(?:d/[0-9a-zA-Z-_]+/?(.+|$)?|public/?\?hash=(.+))")
    test = (
        # hash
        ("https://disk.yandex.ru/public/?hash="
         "AcMOq31fi2Ph2wt2s1exDfTSxsaU6aQ3De5KYrs1k3%2bZKRLZPkyO5LKfYt%2beIN4M"
         "q%2fJ6bpmRyOJonT3VoXnDag%3d%3d", {
             "count": 1,
             "pattern": r"^https://downloader\.disk\.yandex\.ru/disk/",
             "content": "c977e9ba1d6a9dcbf7eb48f6ca8192c7c10b9d5f",
         }),
        # short URL
        ("https://disk.yandex.ru/d/2mfSDE5PSv77tA", {
            "count": 1,
            "pattern": r"^https://downloader\.disk\.yandex\.ru/disk/",
            "keyword": {
                "date"        : "type:datetime",
                "date_created": "type:datetime",
                "extension"   : "rar",
                "filename"    : "BAAR - Прощение - SINGLE (2014)",
            },
        }),
        # folder
        ("https://disk.yandex.ru/d/pUkOIfxY5R_DEA", {
            "count": 1,
            "pattern": r"^https://downloader\.disk\.yandex\.ru/disk/",
            "keyword": {"path": ["01.Брендбук ВПН"]},
        }),
        ("https://disk.yandex.ru/d/pUkOIfxY5R_DEA/", {
            "count": 1,
            "keyword": {"path": ["01.Брендбук ВПН"]},
        }),
        ("https://disk.yandex.com/public?hash="
         "guv8LQMJRVXrlf16SXqWFjfWp%2B4Ml463jyCMFjkFvfVHoO8KIWrVCV0PR2XsFBQqq"
         "%2FJ6bpmRyOJonT3VoXnDag%3D%3D", {
             "count": 15,
         }),
        # subfolder
        ("https://disk.yandex.com/d/DCXoxtp5f236ag/%D0%A2%D0%9C-19-9-1%20%D0"
         "%9C%D0%94%D0%9A%2002.01.%20", {
             "count": 6,
             "keyword": {"path": ["ТМ-19-9-1 МДК 02.01. "]},
         }),
        ("https://disk.yandex.com/public?hash="
         "guv8LQMJRVXrlf16SXqWFjfWp%2B4Ml463jyCMFjkFvfVHoO8KIWrVCV0PR2XsFBQqq"
         "%2FJ6bpmRyOJonT3VoXnDag%3D%3D%3A%2F%D0%A2%D0%9C-19-9-1%2B%D0%9C%D0"
         "%94%D0%9A%2B02.01.%2B", {
             "count": 6,
         }),
        # 404
        ("https://disk.yandex.ru/d/fooOIfxY5R_DEA", {
            "exception": exception.NotFoundError,
        }),
        ("https://disk.yandex.com/public?hash=guv8LQMJRVXrlf16SXqWFjfWp", {
            "exception": exception.NotFoundError,
        }),

        ("https://disk.yandex.com.tr/d/2mfSDE5PSv77tA"),
        ("https://yadi.sk/d/2mfSDE5PSv77tA"),
        ("https://yadisk.cc/d/2mfSDE5PSv77tA"),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        raw_path = match.group(1)
        if raw_path is not None:
            self.hash = None
            path = text.unquote(raw_path)
        else:
            self.hash, _, path = text.unquote(match.group(2)).partition(":")
            # XXX: how exactly are plus signs in folder names handled?
            path = text.unquote(path.replace("+", " "))
        if path:
            self.path = path.strip("/").split("/")
            self.base = []
        else:
            self.path = []
            self.base = None

    @staticmethod
    def prepare(file):
        """Adjust the content of a file or folder object"""
        file["date"] = text.parse_datetime(
            file["modified"], "%Y-%m-%dT%H:%M:%S%z")
        file["date_created"] = text.parse_datetime(
            file["created"], "%Y-%m-%dT%H:%M:%S%z")
        if file["type"] == "file":
            text.nameext_from_url(file["name"], file)

    def items(self):
        self.api = YandexdiskWebAPI(self)
        self.sk = "y" + util.generate_token(16)

        if not self.hash:
            url = "{}/{}".format(self.root, self.url.split("/", 3)[3])
            response = self.request(url, notfound="file or folder")
            self.hash = text.extr(response.text, '"hash":"', '"')

        yield from self.files()

    def commit(self, data):
        # declared inside 'commit' to be able to access 'data'
        post_data = {"hash": self.hash, "sk": self.sk}

        def _retry(response):
            if "disposition" in response.url:
                # if for whatever reason file["file"] fails, prepare to
                # use "/public/api/download-url"
                data.update({
                    "_http_method" : "POST",
                    "_http_headers": {"Content-Type": "text/plain"},
                    "_http_data"   : util.json_dumps(post_data),
                })
                return False
            # handle 'sk'
            if response.status_code != 400:
                return False
            obj = response.json()
            # 'sk' is associated with cookies
            if not obj.get("wrongSk"):
                print(response.text)
                return False
            new_sk = obj.get("newSk")
            if not new_sk:
                print(response.text)
                return False
            post_data["sk"] = self.sk = new_sk
            data["_http_data"] = util.json_dumps(post_data)
            return True

        def _validate(response):
            if "filename" in response.headers.get("content-disposition", ""):
                return True
            if "json" not in response.headers.get("content-type", ""):
                return False
            obj = response.json()
            if obj.get("statusCode") != 200:
                print(response.text)
                return False
            del data["_http_method"]
            del data["_http_headers"]
            del data["_http_data"]
            return obj["data"]["url"]

        data.update({
            "_fallback"     : (self.root + "/public/api/download-url",),
            "_http_validate": _validate,
            "_http_retry"   : _retry,
        })
        # this approach is more complex than getting sk from webpage,
        # but requesting the API endpoint instead of the webpage
        # may help avoid CAPTCHAs
        return Message.Url, data["file"], data

    def files(self):
        """Recursively yield files in the folder"""
        parent_data, items = \
            self.api.folder_content(self.hash, "/" + "/".join(self.path))

        self.prepare(parent_data)
        if parent_data["type"] == "file":
            del parent_data["total"]
            parent_data["path"] = ()  # overwrite "/"
            yield Message.Directory, parent_data
            yield self.commit(parent_data)
            next(items, None)  # exhaust the generator
            return

        if self.base is None:
            self.base = [parent_data["name"]]
        folder_data = {"parent": parent_data, "path": self.base + self.path}
        yield Message.Directory, folder_data

        folders = []
        for item in items:
            if item["type"] == "dir":
                folders.append(item)
                continue
            self.prepare(item)
            item.update(folder_data)
            yield self.commit(item)

        for folder in folders:
            self.path.append(folder["path"].lstrip("/"))
            yield from self.files()
            self.path.pop()


class YandexdiskWebAPI():
    """Interface for Yandex Disk web API"""

    API_ROOT = "https://cloud-api.yandex.net/v1/disk/public"
    PER_PAGE = 200

    def __init__(self, extractor):
        self.request = extractor.request

    def folder_content(self, hash, path="/", offset=0):
        """Return a tuple of (folder_info, folder_content)"""
        result = self._folder_content_impl(hash, path, offset)
        return next(result), result

    def _folder_content_impl(self, hash, path, offset):
        params = {
            "limit"     : self.PER_PAGE,
            "public_key": hash,
            "path"      : path,
        }
        folder = None
        while True:
            params["offset"] = offset
            response = self._call("/resources", params, notfound="resource")
            embedded = response.pop("_embedded", {})
            response["total"] = total = embedded.get("total") or 0
            if folder is None:
                folder = response
                yield folder
            items = embedded.get("items") or ()
            if not items:
                # this happens when the total number of returned items
                # is smaller than 'total'
                break
            yield from items
            offset += len(items)
            if offset >= total:
                break

    def _call(self, endpoint, params, **kwargs):
        return self.request(
            self.API_ROOT + endpoint, params=params, **kwargs).json()
