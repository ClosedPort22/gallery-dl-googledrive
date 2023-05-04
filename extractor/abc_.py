# -*- coding: utf-8 -*-

"""Extractors for https://www.abc.net.au/"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, util, exception
from functools import reduce
from operator import getitem


BASE_PATTERN = r"(?:https?://)?(?:www\.)?abc\.net\.au"
LISTEN_PATTERN = BASE_PATTERN + \
    r"(/(?:radio|(?:kids)?listen)/programs/[0-9a-z-:]+)"


class AbcExtractor(Extractor):
    """Base class for ABC extractors"""
    category = "abc"
    root = "https://www.abc.net.au"

    @staticmethod
    def _next_data(txt):
        """Extract `__NEXT_DATA__`"""
        return util.json_loads(text.extr(
            txt,
            '"__NEXT_DATA__" type="application/json">', "</script>"))


class AbcListenEpisodeExtractor(AbcExtractor):
    """Extractor for a single episode"""
    subcategory = "listen-episode"
    archive_fmt = "{id}_{date_updated}_{filename}.{extension}"
    filename_fmt = "{id} - {title}.{extension}"
    # /[productSlug]/programs/[productPageSlug]/[...articleId]
    pattern = LISTEN_PATTERN + r"(/[0-9a-z-:]+/[0-9]+)"
    test = (
        ("https://www.abc.net.au/kidslisten/programs/"
         "dino-dome/megan-vs-scorpy/102268796", {
             "range": "1",
             "count": 1,
             "pattern": r"^https://live-production\.wcms\.abc-cdn\.net\.au/"
                        r"22a157492685516dafc809800ca5b194$",
             "keyword": {
                 "date": "type:datetime",
                 "date_updated": "type:datetime",
             },
         }),
        # first rendition object invalid
        ("https://www.abc.net.au/kidslisten/programs/"
         "dino-dome/krono-vs-quin/102296604", {
             "options": (("image", 0),),
             "count": 1,
             "pattern": r"^https://mediacore-live-production.akamaized.net/"
                        r"audio/01/ht/Z/g8.mp3$",
             "keyword": {
                 "bitrate" : int,
                 "codec"   : str,
                 "MIMEType": str,
                 "fileSize": int,
                 "height"  : None,
             },
         }),
        ("https://www.abc.net.au/kidslisten/programs/"
         "dino-dome/megan-vs-scorpy/102268797", {
             "exception": exception.NotFoundError,
         }),
        ("https://www.abc.net.au/listen/programs/"
         "judith-lucy-overwhelmed-and-dying/"
         "are-we-just-completely-screwed/101699548"),
    )

    def __init__(self, match):
        AbcExtractor.__init__(self, match)
        self.webpage = "".join((self.root, match.group(1), match.group(2)))

    @staticmethod
    def prepare(data):
        dp = data["datelinePrepared"]
        data["date"] = text.parse_datetime(dp["publishedDate"])
        data["date_updated"] = text.parse_datetime(dp["updatedDate"])

    def items(self):
        next_data = self._next_data(
            self.request(self.webpage, notfound="episode").text)
        dp = next_data["props"]["pageProps"]["data"]["documentProps"]
        self.prepare(dp)

        yield Message.Directory, dp

        if self.config("image", True):
            paths = (
                ("headTagsArticlePrepared", "schema", "image", "url"),
                ("headTagsSocialPrepared", "image"),
                ("cropInfo", 0, "value", 0, "url"),
            )
            image_url = _try_retrieve(dp, paths)
            if image_url:
                image_url = image_url.partition("?")[0]
                data = text.nameext_from_url(image_url)
                # get extension from 'content-type' header
                # akamai image server optimizes the image depending on
                # the 'accept' header
                # '*/*' == original image? (at least we can get PNGs)
                data.update(dp)
                yield Message.Url, image_url, data

        for rendition in dp["renditions"]:
            file = rendition.copy()
            url = file["url"]
            if not url:
                continue
            text.nameext_from_url(url, file)
            file.update(dp)
            yield Message.Url, url, file


def _try_retrieve(obj, paths, default=None):
    for path in paths:
        try:
            # same as obj[path[0]][path[1]]...
            return reduce(getitem, path, obj)
        except (KeyError, IndexError):
            pass
    return default


class AbcListenProgramExtractor(AbcExtractor):
    """Extractor for a program"""
    subcategory = "listen-program"
    archive_fmt = "{filename}.{extension}"
    filename_fmt = "{heading}.{extension}"
    # /[productSlug]/programs/[productPageSlug]
    pattern = LISTEN_PATTERN + r"(?:/episodes)?/?(?:$|[?#])"
    test = (
        ("https://www.abc.net.au/kidslisten/programs/dino-dome", {
            "options": (("image", 1), ("chapter-filter", "False")),
            "count": 1,
            "pattern": r"^https://live-production\.wcms\.abc-cdn\.net\.au/"
                       r"ee24db25461bf441b60e321393e8625f$",
            "keyword": {
                "presentersPrepared"    : list,
                "descriptionPrepared"   : dict,
                "heroImagePrepared"     : dict,
                "headTagsPagePrepared"  : dict,
                "headTagsSocialPrepared": dict,
            },
        }),
        ("https://www.abc.net.au/kidslisten/programs/bedtime-stories", {
            "count": "> 2",
            "pattern": r"^https://www\.abc\.net\.au/kidslisten/programs/"
                       r"bedtime-stories/bedtime-stories:-featuring",
        }),
        ("https://www.abc.net.au/kidslisten/programs/dino", {
            "exception": exception.NotFoundError,
        }),
        ("https://www.abc.net.au/kidslisten/"
         "programs/bedtime-stories/episodes"),
        ("https://www.abc.net.au/kidslisten/programs/bedtime-stories/"),
        ("https://www.abc.net.au/kidslisten/programs/bedtime-stories/#foo"),
        ("https://www.abc.net.au/kidslisten/programs/bedtime-stories?foo=bar"),
    )

    def __init__(self, match):
        AbcExtractor.__init__(self, match)
        self.webpage = self.root + match.group(1)

    def _image(self):
        if not self.config("image", False):
            return
        next_data = self._next_data(
            self.request(self.webpage, notfound="program").text)
        pp = next_data["props"]["pageProps"]
        data = pp["heroDescriptionPrepared"].copy()
        data["presentersPrepared"] = pp["presentersPrepared"]
        data.update(pp["heroImagePrepared"])
        data.update(pp["templatePrepared"])

        paths = (
            ("imgSrc",),
            ("srcSet", 0),
        )
        image_url = _try_retrieve(data["heroImagePrepared"], paths)
        if not image_url:
            return

        yield Message.Directory, data

        image_url = image_url.partition("?")[0]
        text.nameext_from_url(image_url, data)
        yield Message.Url, image_url, data

    def items(self):
        yield from self._image()

        next_data = self._next_data(
            self.request(self.webpage + "/episodes", notfound="program").text)
        for item in (next_data["props"]["pageProps"]
                     ["programCollectionPrepared"]["items"]):
            yield (Message.Queue, self.root + item["articleLink"],
                   {"_extractor": AbcListenEpisodeExtractor})
