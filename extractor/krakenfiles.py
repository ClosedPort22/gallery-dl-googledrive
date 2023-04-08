# -*- coding: utf-8 -*-

"""Extractors for Krakenfiles"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, util


class KrakenfilesFileExtractor(Extractor):
    """Extractor for Krakenfiles files"""
    category = "krakenfiles"
    subcategory = "file"
    filename_fmt = "{hash}.{extension}"
    archive_fmt = "{hash}"
    pattern = (r"(?:https?://)?(?:www\.)?krakenfiles\.com/"
               r"view/([0-9a-zA-Z]+)/file\.html")
    test = (
        # 10 MB file
        ("https://krakenfiles.com/view/oFv13tQf8d/file.html", {
            "count": 1,
            "pattern": "^https://krakenfiles.com/view/oFv13tQf8d/file.html$",
            "content": "c26b9470e7584f13f4ea1fe24ce1288f17059756",
        }),
        # 404
        ("https://krakenfiles.com/view/foobarbaz1/file.html", {
            "content": "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # empty
        }),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.hash = match.group(1)

    def metadata(self):
        return {"extension": "", "hash": self.hash}

    def items(self):
        data = self.metadata()

        def _validate(response):
            # * declared inside 'items' to be able to access 'data'
            # * delegate URL extraction to the downloader to be able to skip
            #   already downloaded files without making any requests
            if "content-disposition" in response.headers:
                return True
            if "json" in response.headers.get("content-type", ""):
                del data["_http_method"]
                del data["_http_data"]
                del data["_http_headers"]
                return response.json()["url"]
            # assume html
            # hash = text.extr(html, 'data-file-hash="', '"')
            hash = data["hash"]
            token = text.extr(
                response.text, 'name="token" value="', '" title="dl-token"')
            if not token:
                return False
            boundary_marker = util.generate_token(8)[:-1]
            post_data = DATA.format(boundary_marker=boundary_marker,
                                    token=token)
            headers = {
                "content-type": ("multipart/form-data; "
                                 "boundary=----WebKitFormBoundary" +
                                 boundary_marker),
                "hash": hash,
            }
            data.update({
                "_http_method" : "POST",
                "_http_data"   : post_data,
                "_http_headers": headers,
            })
            return "https://krakenfiles.com/download/" + hash

        data["_http_validate"] = _validate
        yield Message.Directory, data
        yield Message.Url, self.url, data


DATA = """------WebKitFormBoundary{boundary_marker}
Content-Disposition: form-data; name="token"

{token}
------WebKitFormBoundary{boundary_marker}--"""
