# -*- coding: utf-8 -*-

"""Extractors for pCloud"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, exception


class PcloudShareExtractor(Extractor):
    """Extractor for shared files hosted on pCloud"""
    category = "pcloud"
    subcategory = "share"
    directory_fmt = ("{category}", "{path[0]:?//}", "{path[1]:?//}",
                     "{path[2]:?//}", "{path[3:]:J - /}")
    archive_fmt = "{code}_{fileid}_{hash}"
    pattern = (r"(?:https?://)?(?:([0-9a-z]+)\.pcloud\.(?:com|link)"
               r"(?:/#page=publink\&code=|/publink/show\?code=)|"
               r"([0-9a-z]+)\.pc\.cd/)([0-9a-zA-Z]+)")
    test = (
        # file
        ("https://u.pcloud.link/publink/show?code="
         "XZT4PPVZpwWKTGNYEl520etWoS0m4LDP17gV", {
             "count": 1,
             "keyword": {
                 "code"        : "XZT4PPVZpwWKTGNYEl520etWoS0m4LDP17gV",
                 "date"        : "type:datetime",
                 "date_created": "type:datetime",
                 "extension"   : "mp3",
                 "filename": "SALSA PARA DEDICAR_Las Mas "
                             "Pedidas_TAKICARDIA_Mixing By.Dj Luis Carlos Mix",
                 "ownerispremium": bool,
                 "parent"      : {},
                 "path"        : (),
             },
             "pattern": r"^https://api\.pcloud\.com/getpublinkdownload",
         }),
        # EU datacenter
        ("https://e.pcloud.link/publink/show?code="
         "XZ4SMkZCpqOqCHicFb0RwggJSJaWFhrQKU7", {
             "count": 1,
             "pattern": r"^https://eapi\.pcloud\.com/getpublinkdownload",
         }),
        ("https://e.pc.cd/KAWotalK", {
            "count": 1,
            "pattern": r"^https://eapi\.pcloud\.com/getpublinkdownload",
            "content": "d52f6082cb729deb984d83bda236eb73d1eeec80",
        }),
        # folder
        ("https://u.pcloud.link/publink/show?code="
         "kZuGtUXZjqkXZG6pCyJTO3VJHoKAWna7dM8gSU9gV", {
             "count": 12,
             "keyword": {
                 "parent": {
                     "date": "type:datetime",
                     "date_created": "type:datetime",
                     "name": "Heckman-SE136746-MS-raw-files",
                 },
                 "path": ("Heckman-SE136746-MS-raw-files",),
             },
         }),
        # expired
        ("https://u.pcloud.link/publink/show?code="
         "XZKWMYXZAXdC7K0Epj4iIb3NotWXgbXxKPck", {
             "exception": exception.NotFoundError,
         }),
        ("https://e.pc.cd/foobar00", {
            "exception": exception.NotFoundError,
        }),

        ("https://e.pcloud.link/publink/show?code="
         "kZtNNYZ3iirUVJUfr7iVmipVrznVHTIHayV"),
        ("https://e.pcloud.com/#page=publink&code="
         "kZtNNYZ3iirUVJUfr7iVmipVrznVHTIHayV"),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        subdomain = match.group(1) or match.group(2) or ""
        # EU or US datacenter
        self.api_root = \
            "https://{}api.pcloud.com".format("e" if "e" in subdomain else "")
        self.code = match.group(3)

    def items(self):
        response = self.request(
            "{}/showpublink?code={}".format(self.api_root, self.code)).json()
        try:
            items = (response.pop("metadata"),)
        except KeyError:
            # 7001: not found or expired
            # 7002: deleted by owner
            # 7003: abuse
            print(response)
            raise exception.NotFoundError("file or folder")
        response.update(self.metadata())
        yield from self.files(items, response, ())

    def metadata(self):
        """Return general metadata"""
        return {"code": self.code, "parent": {}}

    @staticmethod
    def prepare(file):
        """Adjust the content of a file or folder object"""
        file["date"] = text.parse_datetime(
            file["modified"], "%a, %d %b %Y %H:%M:%S %z")
        file["date_created"] = text.parse_datetime(
            file["created"], "%a, %d %b %Y %H:%M:%S %z")

    def commit(self, data):
        def _validate(response):
            if "content-disposition" in response.headers:
                return True
            obj = response.json()
            hosts = obj["hosts"]
            template = "https://{}" + obj["path"]
            data["_fallback"] = tuple(template.format(h) for h in hosts[1:])
            return template.format(hosts[0])

        url = "{}/getpublinkdownload?code={}&forcedownload=1&fileid={}".format(
            self.api_root, self.code, data["fileid"])
        data["_http_validate"] = _validate
        text.nameext_from_url(data["name"], data)
        return Message.Url, url, data

    def files(self, items, data, parent_path):
        """Recursively yield files in a folder"""
        path = parent_path + (data["parent"].get("name"),)
        # the first element should never appear in the actual directory
        # structure
        data["path"] = path[1:]
        yield Message.Directory, data

        folders = []
        for item in items:
            self.prepare(item)
            if "contents" in item:
                folders.append(item)
                continue
            item.update(data)
            yield self.commit(item)

        for folder in folders:
            data["parent"] = folder
            yield from self.files(folder.pop("contents"), data, path)
