# -*- coding: utf-8 -*-

"""Extractors for WeTransfer"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, util, exception


class WetransferFileExtractor(Extractor):
    """Extractor for WeTransfer files"""
    category = "wetransfer"
    subcategory = "file"
    archive_fmt = "{file_id}"
    root = "https://wetransfer.com"
    pattern = (r"(?:https?://)?(?:www\.)?wetransfer\.com/"
               r"downloads/([0-9a-f]{46})/([0-9a-f]{6})")
    test = (
        # expired
        ("https://wetransfer.com/downloads/"
         "91c97b339855d6c0f4a2772d9b7a5fe720190406121754/7b85a0", {
             "exception": exception.NotFoundError,
         }),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.id = match.group(1)
        self.security_hash = match.group(2)

    @staticmethod
    def prepare(file):
        """Adjust the content of a file object"""
        text.nameext_from_url(file["name"], file)
        # prevent conflict with folder (transfer) metadata
        file["filesize"] = file.pop("size")
        file["file_id"] = file.pop("id")

    def items(self):
        def _validate(response):
            # * declared inside 'items' to be able to access 'data'
            # * delegate extraction of direct URL to the downloader to be able
            #   to save 1 request per file when skipping downloaded files
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

        headers = {"Content-Type": "application/json"}
        data = {"_http_method"  : "POST",
                "_http_headers" : headers,
                "_http_validate": _validate}
        post_data = {"security_hash": self.security_hash,
                     "intent"       : "single_file"}

        metadata = self.request(
            "{}/api/v4/transfers/{}/prepare-download".format(
                self.root, self.id),
            data=util.json_dumps({"security_hash": self.security_hash}),
            method="POST", headers=headers, notfound="transfer").json()
        items = metadata.pop("items")
        data["parent"] = metadata

        api_url = "{}/api/v4/transfers/{}/download".format(self.root, self.id)
        yield Message.Directory, data

        for item in items:
            self.prepare(item)
            data.update(item)
            post_data["file_ids"] = (data["file_id"],)
            data["_http_data"] = util.json_dumps(post_data)
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
