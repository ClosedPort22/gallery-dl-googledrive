# -*- coding: utf-8 -*-

"""Extractors for https://dbree.org/ and https://dbree.me/"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, util
import itertools


BASE_PATTERN = r"(?:https?://)?dbree\.(?:org|me)"


class DbreeExtractor(Extractor):
    """Base class for Dbree extractors"""
    category = "dbree"
    archive_fmt = "{id}"
    cookiedomain = ".dbree.org"
    root = "https://dbree.org"

    def __init__(self, match):
        Extractor.__init__(self, match)
        domain = self.root.rpartition("/")[2]
        cookies = self.session.cookies
        if not cookies.get("PHPSESSID", domain=domain):
            cookies.set("PHPSESSID", util.generate_token(13), domain=domain)

    def items(self):
        self._prepare_ddosguard_cookies()

        for file in self.files():
            yield Message.Directory, file

            response = self.request("{}/v/{}".format(self.root, file["id"]))

            extr = text.extract_from(response.text)
            text.nameext_from_url(
                text.unescape(extr("<li>Name: ", "</li>")), file)
            file["filesize"] = extr("<li>Size: ", "</li>")
            file["date"] = text.parse_datetime(
                extr("<li>Created: ", "</li>"), "%Y-%m-%d %H:%M:%S")
            file["last_download"] = text.parse_datetime(
                extr("<li>Last Download: ", "</li>"), "%Y-%m-%d %H:%M:%S")

            url = "{}/d/{}".format(self.root, extr("'//dbree.org/d/", "'"))
            yield Message.Url, url, file

    def files(self):
        """Return an iterable of file objects"""

    def metadata(self):
        """Return general metadata"""


class DbreeFileExtractor(DbreeExtractor):
    """Extractor for individual files"""
    subcategory = "file"
    pattern = BASE_PATTERN + r"/v/([0-9a-f]{5,})"
    test = (
        ("https://dbree.org/v/24e421", {
            "pattern": r"^https://dbree\.org/d/[0-9a-f]+",
            "keyword": {
                "date"     : "type:datetime",
                "extension": "jpg",
                "filename" : "re:^STOP-LEAKING-problé",
                "filesize" : "0.01 MB",
                "id"       : "24e421",
            },
            "content": "377cbcd06221f8af8a6311be4e7b3161bdc00c26",
        }),
        ("https://dbree.me/v/24e421"),
        ("https://dbree.org/v/24e42"),
    )

    def __init__(self, match):
        DbreeExtractor.__init__(self, match)
        self.id = match.group(1)

    def files(self):
        return ({"id": self.id},)


class DbreeSearchExtractor(DbreeExtractor):
    subcategory = "search"
    pattern = BASE_PATTERN + r"/s/([^/?#&]+)(?:&page=(\d+))?"
    per_page = 10
    test = (
        ("https://dbree.org/s/166", {
            "count": ">= 11",
            "keyword": {"search": "166"},
        }),
        ("https://dbree.org/s/166&page=10", {
            "count": "<= 15",
        }),
    )

    def __init__(self, match):
        DbreeExtractor.__init__(self, match)
        self.search = match.group(1)
        self.page = text.parse_int(match.group(2))

    def files(self):
        for i in itertools.count(0):
            url = "{}/s/{}&page={}".format(
                self.root, self.search, self.page + self.per_page * i)
            a = self.request(url)
            ids = tuple(text.extract_iter(
                a.text, "<a href='/v/", "'"))
            if not ids:
                return
            for id in ids:
                data = self.metadata()
                data["id"] = id
                yield data

    def metadata(self):
        return {"search": self.search}
