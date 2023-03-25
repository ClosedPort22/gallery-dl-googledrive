# -*- coding: utf-8 -*-

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import exception


BASE_PATTERN = r"(?:https?://)?(?:drive|docs)\.google\.com"


class GoogledriveExtractor(Extractor):
    """Extractor for Google drive files"""
    category = "googledrive"
    filename_fmt = "{id}.{extension}"
    archive_fmt = "{id}"
    root = "https://drive.google.com"
    pattern = (BASE_PATTERN + r"/(?:(?:uc|open)\?(?:[\w=&]+&)?id=([\w-]+)|"
               r"(?:file|presentation)/d/([\w-]+))")
    test = (
        ("https://drive.google.com/file/d/0B9P1L--7Wd2vU3VUVlFnbTgtS2c/view", {
            "pattern": r"^https://drive\.google\.com/uc\?export=download"
                       r"&id=0B9P1L--7Wd2vU3VUVlFnbTgtS2c&confirm=t$",
            "content": "69a5a1000f98237efea9231c8a39d05edf013494",
            "keyword": {"id": "0B9P1L--7Wd2vU3VUVlFnbTgtS2c"},
        }),
        # 404
        ("https://drive.google.com/file/d/foobar/view", {
            "content": "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # empty
        }),
        # login required
        ("https://drive.google.com/file/d/0B9P1L--7Wd2vNm9zMTJWOGxobkU/view", {
            "exception": exception.AuthorizationError,
            "content": "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # empty
        }),
        # quota exceeded
        # ("https://docs.google.com/file/d/0B1MVW1mFO2zmZHVRWEQ3Rkc3SVE/view",{
        #     "exception": exception.GalleryDLException,
        # }),

        ("https://drive.google.com/file/d/"
         "0B9P1L--7Wd2vNm9zMTJWOGxobkU/view?usp=sharing"),
        ("https://drive.google.com/file/d/0B9P1L--7Wd2vNm9zMTJWOGxobkU/edit"),
        ("https://drive.google.com/uc?id=1l_5RK28JRL19wpT22B-DY9We3TVXnnQQ"),
        ("https://drive.google.com/file/d/0B9P1L--7Wd2vNm9zMTJWOGxobkU"),
        ("http://drive.google.com/file/d/0B9P1L--7Wd2vNm9zMTJWOGxobkU"),

        ("https://docs.google.com/uc?id=1l_5RK28JRL19wpT22B-DY9We3TVXnnQQ"),
        ("https://docs.google.com/open?id=1l_5RK28JRL19wpT22B-DY9We3TVXnnQQ"),
        ("https://docs.google.com/"
         "uc?export=download&id=1l_5RK28JRL19wpT22B-DY9We3TVXnnQQ"),
        # random parameters
        ("https://docs.google.com/"
         "uc?export=download&confirm=t&id=1l_5RK28JRL19wpT22B-DY9We3TVXnnQQ"),
        ("https://docs.google.com/"
         "uc?id=1l_5RK28JRL19wpT22B-DY9We3TVXnnQQ&export=download"),
        ("https://docs.google.com/file/d/0B9P1L--7Wd2vNm9zMTJWOGxobkU/view"),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.id = match.group(1) or match.group(2)

    def items(self):
        url = "{}/uc?export=download&id={}&confirm=t".format(
            self.root, self.id)
        data = {"id": self.id, "extension": "", "_http_validate": _validate}

        yield Message.Directory, data
        yield Message.Url, url, data


# delegate checks to the downloader to be able to skip already
# downloaded files without making any requests
def _validate(response):
    if "content-disposition" in response.headers:
        return True
    if "x-auto-login" in response.headers:  # redirected to login page
        raise exception.AuthorizationError()
    raise exception.StopExtraction(
        "Quota exceeded for anonymous downloads. "
        "Use cookies to bypass this error.")
