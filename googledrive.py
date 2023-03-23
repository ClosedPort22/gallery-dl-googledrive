from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, exception


BASE_PATTERN = r"(?:https?://)?(?:drive|docs)\.google\.com"


class GoogledriveExtractor(Extractor):
    """Extractor for Google drive files"""
    category = "googledrive"
    filename_fmt = "{id}"
    archive_fmt = "{id}"
    pattern = (BASE_PATTERN + r"/(?:(?:uc|open)\?(?:[\w=&]+&)?id=([\w-]+)|"
               r"(?:file|presentation)/d/([\w-]+))")
    test = (
        ("https://drive.google.com/file/d/0B9P1L--7Wd2vU3VUVlFnbTgtS2c/view", {
            "pattern": r"^https://doc-\w\w-\w\w-docs\.googleusercontent\.com",
            "content": "69a5a1000f98237efea9231c8a39d05edf013494",
            "keyword": {"id": "0B9P1L--7Wd2vU3VUVlFnbTgtS2c"},
        }),
        ("https://drive.google.com/file/d/foobar/view", {
            "exception": exception.NotFoundError,
        }),
        # security warning
        ("https://drive.google.com/file/d/"
         "1l_5RK28JRL19wpT22B-DY9We3TVXnnQQ/view", {
             "pattern": r"^https://doc-\w\w-\w\w-docs\.googleusercontent\.com",
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
        resp = self.request(
            "https://drive.google.com/"
            "uc?export=download&id={}&confirm=t".format(self.id),
            allow_redirects=False, notfound="file")
        data = {"id": self.id, "extension": ""}

        if "location" in resp.headers:
            print(resp.headers["location"])
            yield Message.Directory, data
            yield Message.Url, resp.headers["location"], data
            return

        msg = text.extr(resp.text, "<title>", "</title>") or \
            text.extr(resp.text, 'class="uc-error-caption">', "</p>")
        if "quota" in msg.lower():
            msg = ("quota exceeded for anonymous downloads; "
                   "use cookies to bypass this error")
        elif not msg:
            # unforeseen errors
            self.log.debug(resp.text)
            msg = "unknown error"
        raise exception.StopExtraction(
            "Unable to retrieve download URL: %s", msg)
