# -*- coding: utf-8 -*-

"""Extractors for Mediafire"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, exception


BASE_PATTERN = r"(?:https?://)?(?:www\.)?mediafire\.com"


class MediafireExtractor(Extractor):
    """Extractor for Mediafire URLs"""
    category = "mediafire"
    filename_fmt = "{id}.{extension}"
    archive_fmt = "{id}"
    root = "https://www.mediafire.com"
    pattern = BASE_PATTERN + r"/(?:download(?:\.php\?|/)|file/|\?)([0-9a-z]+)"
    test = (
        # direct download
        ("http://www.mediafire.com/file/ise1i57s4dfkgc8", {
            "count": 1,
            "pattern": r"^https://www\.mediafire\.com/download/",
            "keyword": {"id": "ise1i57s4dfkgc8", "extension": ""},
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
        ("http://www.mediafire.com/download.php?u79eqi2we39k343"),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.id = match.group(1)

    def items(self):
        data = {"id": self.id, "extension": "", "_http_validate": _validate}

        yield Message.Directory, data
        yield Message.Url, "{}/download/{}".format(self.root, self.id), data


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
    if not url:
        # return True
        raise exception.StopExtraction("Unable to get download URL")
    return url
