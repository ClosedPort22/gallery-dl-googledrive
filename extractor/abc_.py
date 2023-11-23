# -*- coding: utf-8 -*-

"""Extractors for https://www.abc.net.au/"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, util, exception
from functools import reduce
from operator import getitem


LISTEN_PATTERN = (
    r"(?:https?://)?(?:www\.)?abc\.net\.au"
    r"(/(?:radio|(?:kids)?listen)/programs/[0-9a-z-:]+)")
IVIEW_PATTERN = r"(?:https?://)?iview\.abc\.net\.au"


class AbcExtractor(Extractor):
    """Base class for ABC extractors"""
    category = "abc"


class AbcListenExtractor(AbcExtractor):
    """Base class for ABC Listen extractors"""
    root = "https://www.abc.net.au"


class AbcIviewExtractor(AbcExtractor):
    """Base class for ABC iview extractors"""
    root = "https://iview.abc.net.au"


class AbcListenEpisodeExtractor(AbcListenExtractor):
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
        AbcListenExtractor.__init__(self, match)
        self.webpage = "".join((self.root, match.group(1), match.group(2)))

    @staticmethod
    def prepare(data):
        dp = data["datelinePrepared"]
        data["date"] = text.parse_datetime(dp["publishedDate"])
        data["date_updated"] = text.parse_datetime(dp["updatedDate"])

    def items(self):
        next_data = _next_data(
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


class AbcListenProgramExtractor(AbcListenExtractor):
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
                       r"7af43d56384d5cbf48b73450154b3882$",
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
        AbcListenExtractor.__init__(self, match)
        self.webpage = self.root + match.group(1)

    def _image(self):
        if not self.config("image", False):
            return
        next_data = _next_data(
            self.request(self.webpage, notfound="program").text)
        pp = next_data["props"]["pageProps"]
        data = pp["heroDescriptionPrepared"].copy()
        data["presentersPrepared"] = pp["presentersPrepared"]
        try:
            # keeping this for now just in case
            data.update(pp["heroImagePrepared"])
        except (KeyError, TypeError):
            data.update(pp["heroImageWithCTAPrepared"])
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

        next_data = _next_data(
            self.request(self.webpage + "/episodes", notfound="program").text)
        for item in (next_data["props"]["pageProps"]
                     ["programCollectionPrepared"]["items"]):
            yield (Message.Queue, self.root + item["articleLink"],
                   {"_extractor": AbcListenEpisodeExtractor})


class AbcIviewVideoExtractor(AbcIviewExtractor):
    """Extractor for ABC iview videos"""
    subcategory = "iview-video"
    archive_fmt = "{url}"
    filename_fmt = "{filename|title}.{extension}"
    directory_fmt = ("{category}", "{showTitle}")
    pattern = IVIEW_PATTERN + r"/(?:[^/]+/)*video/([^/?#]+)"
    test = (
        ("https://iview.abc.net.au/video/LE2227H007S00", {
            "range": "1",
            "count": 1,
            "pattern": r"^ytdl:https://iview\.abc\.net\.au"
                       r"/video/LE2227H007S00",
            "keyword": {"date": "type:datetime"},
        }),
        ("https://iview.abc.net.au/video/LE2227H008S00", {
            "range": "2-",
            "count": 6,
            "pattern": r"^https://cdn\.iview\.abc\.net\.au/",
        }),
        ("https://iview.abc.net.au/video/LE2227H025S00", {
            "exception": exception.NotFoundError,
        }),
        ("https://iview.abc.net.au"
         "/show/gruen/series/14/video/LE2227H008S00"),
    )

    api_root = "https://api.iview.abc.net.au/v3/video"

    def __init__(self, match):
        AbcIviewExtractor.__init__(self, match)
        self.house_number = match.group(1)

    def items(self):
        try:
            response = self.request(
                "{}/{}".format(self.api_root, self.house_number),
                notfound="video").json()
        except exception.NotFoundError:
            # unpublished episode
            # 302 -> self.api_root + f'/api/programs/{program}/{house_number}'
            response = self.request(
                "{}/api/programs/{}".format(self.root, self.house_number),
                notfound="video").json()

        try:
            response["date"] = text.parse_datetime(
                response["pubDate"], "%Y-%m-%d %H:%M:%S")
        except KeyError:
            pass
        data = response.copy()

        yield Message.Directory, response
        # disable ytdl downloader to download images only
        if "_embedded" in response:
            # pacify formatters
            response["url"] = response["shareUrl"]
            response["extension"] = "mp4"
            yield Message.Url, "ytdl:" + self.url, response

        if "thumbnail" in response:
            data["url"] = url = response["thumbnail"]
            text.nameext_from_url(url, data)
            yield Message.Url, url, data

        for image in response.get("images") or ():
            data.update(image)
            url = image["url"]
            text.nameext_from_url(url, data)
            yield Message.Url, url, data


class AbcIviewSeriesExtractor(AbcIviewExtractor):
    """Extractor for ABC iview series (seasons)"""
    subcategory = "iview-series"
    archive_fmt = "{url}"
    directory_fmt = ("{category}", "{parent[showTitle]}", "{parent[title]}")
    pattern = \
        IVIEW_PATTERN + r"/show/([^/]+)/series/([\w-]+)(?:$|/(?!video).*)"
    test = (
        ("https://iview.abc.net.au/show/gruen/series/11", {
            "options": (("chapter-filter", "False"),),
            "count": 1,
            "pattern": r"LE1927H_5d6dc8e58e3e3\.jpg$",
        }),
        ("https://iview.abc.net.au/show/gruen/series/14", {
            "options": (("image-filter", "False"),),
            "count": ">= 8",
            "pattern": AbcIviewVideoExtractor.pattern,
        }),
        ("https://iview.abc.net.au/show/dictionary/series/2", {
            "exception": exception.NotFoundError,
        }),
        ("https://iview.abc.net.au/show/dictionary/series/2/"),
        ("https://iview.abc.net.au/show/dictionary/series/2/foo/bar"),
    )

    # v2 sometimes has exclusive series thumbnails
    # v3 images are already included in /v3/video
    api_root = "https://api.iview.abc.net.au/v2/series"

    def __init__(self, match):
        AbcIviewExtractor.__init__(self, match)
        self.series_name, self.series = match.groups()

    def items(self):
        response = self.request(
            "{}/{}/{}".format(self.api_root, self.series_name, self.series),
            notfound="series").json()

        data = {"parent": response}
        yield Message.Directory, data

        url = response["thumbnail"]
        file = text.nameext_from_url(url)
        file["parent"] = response
        file["url"] = url
        yield Message.Url, url, file

        data["_extractor"] = AbcIviewVideoExtractor
        # use --chapter-filter to exclude videoExtras
        for video in _smart_chain_from_iterable(
                response["_embedded"].values()):
            data.update(video)
            # 'shareUrl' is unreliable
            yield (Message.Queue,
                   self.root + data["_links"]["deeplink"]["href"], data)


class AbcIviewProgramExtractor(AbcIviewExtractor):
    """Extractor for ABC iview programs (shows)"""
    subcategory = "iview-program"
    pattern = IVIEW_PATTERN + r"/show/([\w-]+)(?:$|/(?!series|video).*)"
    test = (
        ("https://iview.abc.net.au/show/gruen", {
            "count": ">= 4",
            "pattern": r"^https://iview\.abc\.net\.au"
                       r"/show/gruen/series/[0-9]+",
            "keyword": {"parent": {"date": "type:datetime"}},
        }),
        ("https://iview.abc.net.au/show/dictionary", {
            "exception": exception.NotFoundError,
        }),
        # single-video program
        ("https://iview.abc.net.au/show/kangaroo-beach-summer-special", {
            "count": 1,
            "pattern": r"^https://iview\.abc\.net\.au/video/CH2105H001S00$",
            "keyword": {"houseNumber": "CH2105H001S00"},
        }),
        ("https://iview.abc.net.au/show/dictionary/"),
        ("https://iview.abc.net.au/show/dictionary/foo/bar"),
    )

    def __init__(self, match):
        AbcIviewExtractor.__init__(self, match)
        self.series_name = match.group(1)

    def items(self):
        response = self.request(
            "{}/show/{}".format(self.root, self.series_name),
            notfound="program")
        pd = _initial_state(response.text)["route"]["pageData"]
        series_list = pd["_embedded"].pop("seriesList", None)

        pd["date"] = text.parse_datetime(pd["updated"], "%Y-%m-%d %H:%M:%S")

        data = {"parent": pd}
        if series_list:
            data["_extractor"] = AbcIviewSeriesExtractor
            for series in series_list:
                data.update(series)
                yield (Message.Queue,
                       self.root + data["_links"]["deeplink"]["href"], data)
        else:
            # single-video program
            data["_extractor"] = AbcIviewVideoExtractor
            for video in _smart_chain_from_iterable(pd["_embedded"].values()):
                data.update(video)
                url = "https://iview.abc.net.au/video/" + video["id"]
                yield Message.Queue, url, data


###############################################################################
# Helper functions ############################################################


def _smart_chain_from_iterable(iterable):
    """Yield nested `dict`s in `iterable`"""
    # ({}, [{}, {}], {}) -> ({}, {}, {}, {})
    for item in iterable:
        if isinstance(item, dict):
            yield item
        else:  # assume nested iterable
            yield from item


def _try_retrieve(obj, paths, default=None):
    for path in paths:
        try:
            # same as obj[path[0]][path[1]]...
            return reduce(getitem, path, obj)
        except (KeyError, IndexError):
            pass
    return default


def _initial_state(txt):
    return util.json_loads(util.json_loads(text.extr(
        txt, "__INITIAL_STATE__", "</script>").strip("\r\n =;")))


def _next_data(txt):
    return util.json_loads(text.extr(
        txt,
        '"__NEXT_DATA__" type="application/json">',
        "</script>"))
