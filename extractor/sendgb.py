# -*- coding: utf-8 -*-

"""Extractors for https://sendgb.com/"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text


class SendgbSendExtractor(Extractor):
    """Extractor for SendGB files"""
    category = "sendgb"
    subcategory = "send"
    archive_fmt = "{id}"
    filename_fmt = "{id}.{extension}"
    root = "https://www.sendgb.com"
    pattern = (r"(?:https?://)(?:www\.)?sendgb\.com/"
               r"(?:upload/\?utm_source=)?([0-9a-zA-Z]+)")
    test = (
        # expired
        ("https://www.sendgb.com/InqYAB1tve4", {
            "content": "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # empty
        }),
        ("https://sendgb.com/upload/?utm_source=InqYAB1tve4"),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.id = match.group(1)

    def items(self):
        data = {"extension": "", "id": self.id}

        def _validate(response):
            # * declared inside 'items' to be able to access 'data'
            # * delegate extraction of 'secret_code' to the downloader to be
            #   able to skip already downloaded files without making requests
            if "content-disposition" in response.headers:
                return True
            extr = text.extract_from(response.text)
            url = extr('id="downloadItems" action="', '"')
            secret_code = extr('id="secret_code" value="', '"')
            if not url or not secret_code:
                return False
            data["_http_method"] = "POST"
            data["_http_data"] = {
                "action"     : "download",
                "secret_code": secret_code,
                "download_id": data["id"],
                "private_id" : "",
            }
            return url

        data["_http_validate"] = _validate
        url = "{}/upload/?utm_source={}".format(self.root, self.id)
        yield Message.Directory, data
        yield Message.Url, url, data
