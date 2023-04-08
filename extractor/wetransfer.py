# -*- coding: utf-8 -*-

"""Extractors for WeTransfer"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, util, exception


class WetransferFileExtractor(Extractor):
    """Extractor for WeTransfer files"""
    category = "wetransfer"
    subcategory = "file"
    archive_fmt = "{id}"
    root = "https://wetransfer.com"
    pattern = (r"(?:https?://)?(?:www\.)?wetransfer\.com/"
               r"downloads/([0-9a-f]{46})/([0-9a-f]{6})")
    test = (
        # expired
        ("https://wetransfer.com/downloads/"
         "91c97b339855d6c0f4a2772d9b7a5fe720190406121754/7b85a0", {
             "pattern": "/api/v4/transfers/"
                        "91c97b339855d6c0f4a2772d9b7a5fe720190406121754/"
                        "download$",
             "content": "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # empty
         }),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.id = match.group(1)
        self.security_hash = match.group(2)

    def metadata(self):
        return {
            "filename" : self.id,
            "extension": "",
            "id"       : self.id,
            "security_hash": self.security_hash,
        }

    def items(self):
        data = self.metadata()

        def _validate(response):
            # * declared inside 'items' to be able to access 'data'
            # * delegate extraction of direct URL to the downloader to be able
            #   to skip already downloaded files without making any requests
            if "content-disposition" in response.headers:  # no filename
                return True
            del data["_http_method"]
            del data["_http_headers"]
            del data["_http_data"]
            url = response.json().get("direct_link")
            if not url:
                return False
            text.nameext_from_url(url, data)
            return url

        post_data = {"security_hash": self.security_hash,
                     "intent"       : "entire_transfer"}
        data.update({"_http_method"  : "POST",
                     "_http_headers" : {"Content-Type": "application/json"},
                     "_http_data"    : util.json_dumps(post_data),
                     "_http_validate": _validate})

        api_url = "{}/api/v4/transfers/{}/download".format(self.root, self.id)
        yield Message.Directory, data
        yield Message.Url, api_url, data


class WetransferWetlExtractor(Extractor):
    """Extractor for we.tl short links"""
    category = "wetransfer"
    subcategory = "wetl"
    pattern = r"(?:https?://)?we\.tl/[^/?#]+"
    test = (
        ("https://we.tl/t-df2pCDR04C", {
            "pattern": "https://wetransfer.com/downloads/"
                       "91c97b339855d6c0f4a2772d9b7a5fe720190406121754/7b85a0",
        }),
        ("https://we.tl/t-foobar1234", {
            "exception": exception.NotFoundError,
        }),
    )

    def items(self):
        response = self.request(self.url, method="HEAD", allow_redirects=False)
        location = response.headers.get("location")
        if not location or not WetransferFileExtractor.pattern.match(location):
            raise exception.NotFoundError("transfer")
        yield Message.Queue, location, {"_extractor": WetransferFileExtractor}
