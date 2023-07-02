# -*- coding: utf-8 -*-

"""Extractors for Disney+"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, exception
from itertools import count
import re


class DisneyplusExtractor(Extractor):
    """Base class for Disney+ extractors"""
    category = "disneyplus"
    archive_fmt = "{id}"
    directory_fmt = (
        "{category}",
        "{text[title][full][series][default][content]"
        "|text[title][full][program][default][content]}",
        "{seasonSequenceNumber:?Season //}",
        "{episodeNumber|episodeSequenceNumber:?Episode //}")
    filename_fmt = "{name|filename}_{id[:8]}.{extension}"
    _match_code = re.compile(r"[a-zA-Z]{2}").fullmatch

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.region = self._get_code("region", "US").upper()
        self.language = self._get_code("language", "en").lower()
        self.seen = set()

    def _get_code(self, key, default):
        # TODO: check against a list of allowed codes
        code = self.config(key, default)
        if isinstance(code, str) and self._match_code(code):
            return code
        raise ValueError("Invalid %s: %s", key, code)

    def images(self, obj):
        """Yield messages from a series or video object"""
        yield Message.Directory, obj

        seen = self.seen
        for image in self._flatten_images(obj["image"]):
            if image["id"] in seen:
                self.log.debug("Skipping %s (previously seen)", image["id"])
                continue
            seen.add(image["id"])
            url = image["url"]
            text.nameext_from_url(url, image)
            image.update(obj)

            yield Message.Url, url, image

    @staticmethod
    def _flatten_images(images):
        """Yield images"""
        for name, value1 in images.items():
            for aspect_ratio, value2 in value1.items():
                for type, value3 in value2.items():
                    for image in value3.values():
                        yield {
                            "aspect_ratio": aspect_ratio,
                            "name"        : name,
                            "image_type"  : type,
                            "id"          : image["masterId"],
                            "width"       : image["masterWidth"],
                            "height"      : image["masterHeight"],
                            "url"         : image["url"],
                        }


class DisneyplusVideoExtractor(DisneyplusExtractor):
    """Extractor for individual videos"""
    subcategory = "video"
    pattern = (r"(?:https?://)(?:www\.)?disneyplus\.com/video/("
               r"[0-9a-f]{8}\b-[0-9a-f]{4}\b-[0-9a-f]{4}\b-[0-9a-f]{4}\b-"
               r"[0-9a-f]{12})")
    test = (
        ("https://www.disneyplus.com/video/"
         "39346307-4dbb-45e8-a765-4ed555bb1e03", {
             "count": 33,
             "pattern": r"^https://prod-ripcut-delivery\.disney-plus\.net/"
                        r"v1/variant/disney/",
             "keyword": {
                 "aspect_ratio": "re:^[0-9.]+$",
                 "name"        : str,
                 "type"        : str,
                 "width"       : int,
                 "height"      : int,
                 "url"         : "re:^https://prod-ripcut-delivery",
             },
         }),
        ("https://www.disneyplus.com/video/"
         "39346307-0000-45e8-a765-4ed555bb1e03", {
             "exception": exception.NotFoundError,
         }),
    )

    def __init__(self, match):
        DisneyplusExtractor.__init__(self, match)
        self.id = match.group(1)

    def items(self):
        api = DisneyplusAPI(self, self.region, self.language)
        return self.images(api.video(self.id))


class DisneyplusProgramExtractor(DisneyplusExtractor):
    """Extractor for movies and series"""
    subcategory = "program"
    pattern = (r"(?:https?://)(?:www\.)?disneyplus\.com/(series|movies)/"
               r"[0-9a-z-]+/([0-9a-zA-Z]{12})")
    test = (
        ("https://www.disneyplus.com/series/baymax/1D141qnxDHLI", {
            "count": 50,
        }),
        # language and region
        ("https://www.disneyplus.com/series/baymax/1D141qnxDHLI", {
            "options": (("region", "JP"), ("language", "ja")),
            "range": "40-",
            "keyword": {
                "text": {
                    "title": {
                        "full": {"program": {"default": {"language": "ja"}}},
                    },
                },
            },
        }),
        # not available in the US
        ("https://www.disneyplus.com/series/attack-on-titan/5D0Qx5ecSvHm", {
            "exception": exception.NotFoundError,
        }),
        ("https://www.disneyplus.com/series/attack-on-titan/5D0Qx5ecSvHm", {
            "options": (("region", "JP"), ("language", "ja")),
            "count": 117,
        }),
        ("https://www.disneyplus.com/movies/coco/db9orsI5O4gC", {
            "count": 41,
        }),
        ("https://www.disneyplus.com/movies/coco/db9orsI5OFFF", {
            "exception": exception.NotFoundError,
        }),
    )

    def __init__(self, match):
        DisneyplusExtractor.__init__(self, match)
        self.type = match.group(1)
        self.id = match.group(2)

    def items(self):
        api = DisneyplusAPI(self, self.region, self.language)

        if self.type == "series":
            series_data = api.series(self.id)
            extras_id = series_data["family"]["encodedFamilyId"]
            yield from self.images(series_data)
            yield from self.video_art(series_data)

            for season in api.seasons(self.id):
                # allow metadata files to be saved in the correct directory
                season["text"] = series_data["text"]
                yield Message.Directory, season

                for video in api.episodes(season["seasonId"]):
                    yield from self.images(video)

        elif self.type == "movies":
            extras_id = self.id
            yield from self.images(api.movie(self.id))

        else:  # should never happen
            raise ValueError("Unexpected URL type: %s:%s", self.type, self.url)

        for extra in api.extras(extras_id):
            yield from self.images(extra)

    def video_art(self, series):
        """Yield videos in a series object"""
        for video in self._flatten_videos(series.get("videoArt") or ()):
            url = video["url"]
            text.nameext_from_url(url, video)
            video.update(series)
            yield Message.Url, url, video

    @staticmethod
    def _flatten_videos(videos):
        """Yield videos"""
        for video in videos:
            urls = [x["url"] for x in video["mediaMetadata"]["urls"]]
            yield {
                "id": urls[0].partition("dssott.com")[-1] or urls[0],
                "url"          : urls[0],
                "video_purpose": video["purpose"],
                "_fallback"    : urls[1:],
            }


class DisneyplusAPI():
    """Interface for Disney+'s web API"""
    PER_PAGE = 30

    def __init__(self, extractor, region, language):
        self.request = extractor.request
        self.api_template = (
            "https://disney.content.edge.bamgrid.com/svc/content/{{endpoint}}/"
            "version/5.1/region/{}/audience/false/maturity/1899/language/"
            "{}".format(region, language))

    def video(self, content_id):
        """Return video info"""
        template = self.api_template + "/contentId/{content_id}"
        resp = self.request(template.format(
            endpoint="DmcVideo", content_id=content_id),
            notfound="video").json()
        video = resp["data"]["DmcVideo"]["video"]
        if not video:
            raise exception.NotFoundError("video")
        return video

    def movie(self, family_id):
        """Return movie info"""
        template = self.api_template + "/encodedFamilyId/{family_id}"
        resp = self.request(template.format(
            endpoint="DmcVideoMeta", family_id=family_id),
            notfound="movie").json()
        movie = resp["data"]["DmcVideoMeta"]["video"]
        if not movie:
            raise exception.NotFoundError("movie")
        return movie

    def series(self, series_id):
        """Return series info"""
        template = self.api_template + "/encodedSeriesId/{series_id}"
        resp = self.request(template.format(
            endpoint="DmcSeries", series_id=series_id),
            notfound="series").json()
        series = resp["data"]["DmcSeries"]["series"]
        if not series:
            raise exception.NotFoundError("series")
        return series[0]

    def episodes(self, season_id):
        """Yield all episodes in a season"""
        template = self.api_template + "/seasonId/{season_id}"
        return self._pagination(
            template.format(endpoint="DmcEpisodes", season_id=season_id),
            "DmcEpisodes", notfound="season")

    def seasons(self, series_id):
        """Yield all seasons in a series"""
        # 'DmcSeasons' does not work despite being listed in the manifest JSON
        template = self.api_template + "/encodedSeriesId/{series_id}"
        resp = self.request(template.format(
            endpoint="DmcSeriesBundle", series_id=series_id),
            notfound="series").json()
        for season in resp["data"]["DmcSeriesBundle"]["seasons"]["seasons"]:
            del season["episodes_meta"]
            yield season

    def extras(self, family_id):
        """Yield all extras of a movie or series"""
        template = self.api_template + "/encodedFamilyId/{family_id}"
        return self._pagination(
            template.format(endpoint="DmcExtras", family_id=family_id),
            "DmcExtras", notfound="movie or series")

    def _pagination(self, endpoint, key, **kwargs):
        for i in count(1):
            resp = self.request(
                "{}/pageSize/{}/page/{}".format(
                    endpoint, self.PER_PAGE, i), **kwargs).json()
            data = resp["data"][key]
            yield from data["videos"]
            if not data["meta"]["hasMore"]:
                break
