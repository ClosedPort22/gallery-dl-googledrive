# -*- coding: utf-8 -*-

"""Extractors for Podbean"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, exception
import xml.etree.ElementTree as ET


class PodbeanFeedExtractor(Extractor):
    """Extractor for a Podbean creator's RSS feed"""
    category = "podbean"
    subcategory = "feed"
    archive_fmt = "{itunes_author}_{itunes_image}_{filename}.{extension}"
    directory_fmt = ("{category}", "{itunes_author}")
    filename_fmt = ("S{itunes_season|'0':>02}E{itunes_episode:?//>03} - "
                    "{title|filename}.{extension}")
    pattern = \
        (r"(?:podbean:(?:https?://)?.+|"  # custom domain name and path
         r"(?:https?://)(?:feed\.podbean\.com/[\w-]+|"  # name in path
         r"(?!www|feed)[\w-]+\.podbean\.com))/feed\.xml")  # name as subdomain
    test = (
        ("https://aaronmax.podbean.com/feed.xml", {
            "options": (("podcast-logo", 0), ("episode-logo", 0)),
            "count": "> 50",
            "pattern": r"^https://mcdn\.podbean\.com/mf/web/[0-9a-z]+/",
            "keyword": {
                "itunes_block"   : bool,
                "itunes_explicit": bool,
                "?itunes_season" : int,
                "date"           : "type:datetime",
                "filesize"       : int,
                "mimetype"       : str,
                "podcast": {
                    "ttl"            : int,
                    "itunes_block"   : bool,
                    "itunes_explicit": bool,
                    "date"           : "type:datetime",
                },
            },
        }),
        ("https://feed.podbean.com/abilitynet/feed.xml", {
            "archive": False,
            "range": "1-2",
            "count": 2,
            "pattern": r"^https://[0-9a-z]+\.cloudfront\.net/",
            "keyword": {"?podcast": {"itunes_category":
                                     ["Technology", "News - Tech News",
                                      "Society & Culture"]}},
        }),
        ("https://feed.podbean.com/non_existent/feed.xml", {
            "exception": exception.NotFoundError,
        }),
        # no audio
        ("https://feed.podbean.com/aaronx/feed.xml", {
            "options": (("podcast-logo", 0), ("episode-logo", 0)),
            "count": 0,
        }),
        ("https://feed.podbean.com/aaronx/feed.xml", {
            "count": 1,
            "pattern": r"^https://[0-9a-z]+\.cloudfront\.net/podbean-logo",
            "keyword": {
                "width" : int,
                "height": int,
            },
        }),
        ("https://aaronmax.podbean.com/feed.xml"),
        ("podbean:https://example.org/feed.xml"),
        ("podbean:http://example.org/feed.xml"),
        ("podbean:example.org/feed.xml"),
        ("podbean:https://web.archive.org/web/20200111005954if_/"
         "https://feed.podbean.com/aaronmax/feed.xml"),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        # strip the prefix (if present)
        no, _, url = self.url.partition("podbean:")
        self.feed_url = text.ensure_http_scheme(self.url if no else url)

    @staticmethod
    def prepare_metadata(metadata):
        """Adjust the content of `data`"""
        metadata["date"] = text.parse_datetime(
            metadata["pubDate"], "%a, %d %b %Y %H:%M:%S %z")
        metadata["ttl"] = text.parse_int(metadata["ttl"])
        image = metadata["image"]
        for key in ("width", "height"):
            image[key] = text.parse_int(image[key])

        categories = []
        remove = []
        # FIXME: switch to XPath expressions after dropping suport for
        # older python versions
        # ref: https://docs.python.org/3/library/xml.etree.elementtree.html
        for key, value in metadata.items():
            if not key[0] == "itunes_category":
                continue
            categories.append(" - ".join(_flatten(key, value)))
            remove.append(key)
        for key in remove:
            del metadata[key]
        metadata["itunes_category"] = categories

    @staticmethod
    def prepare_item(item):
        """Adjust the content of `item`"""
        item["date"] = text.parse_datetime(
            item["pubDate"], "%a, %d %b %Y %H:%M:%S %z")
        item["enclosure"]["length"] = text.parse_int(
            item["enclosure"]["length"])

        for key in ("itunes_episode", "itunes_season"):
            if key in item:
                item[key] = text.parse_int(item[key])

    def items(self):
        # XXX: this might break if the site switches to Cloudflare
        # in the future
        raw = self.request(self.feed_url, notfound="user", stream=True).raw
        raw.decode_content = True
        # raw.read = functools.partial(raw.read, decode_content=True)
        root = ET.parse(raw).getroot()

        items = []
        channel_metadata = []
        for child in root.findall("./channel/"):
            if child.tag == "item":
                items.append(child)
            else:
                channel_metadata.append(child)

        metadata = _elements_to_dict(
            channel_metadata, get_key=_get_key_metadata)
        self.prepare_metadata(metadata)
        if self.config("podcast-logo", True):
            url = metadata["itunes_image"]
            data = text.nameext_from_url(url)
            image = metadata["image"]
            data["width"] = image["width"]
            data["height"] = image["height"]

            data.update(metadata)
            yield Message.Directory, data
            yield Message.Url, url, data

        episode_image = self.config("episode-logo", True)

        for item in items:
            data = _elements_to_dict(item, extr=_extr_item)
            self.prepare_item(data)
            data["podcast"] = metadata
            yield Message.Directory, data

            if episode_image:
                url = data["itunes_image"]
                text.nameext_from_url(url, data)
                yield Message.Url, url, data

            # /mf/web/ is basically the same as /mf/download/, the
            # only difference is the 'content-disposition' header
            url = data["enclosure"]["url"]
            # strip the prefix (chrt.fm, pcdn.co, etc.), since these domains
            # send 302s anyway
            _, sep, path = url.partition("mcdn.podbean.com")
            if sep:
                url = "".join(("https://", sep, path))
            text.nameext_from_url(url, data)
            # data["episode_id"] = url.split("/")[-2]
            audio = data.pop("enclosure")
            data["audio"] = url
            data["filesize"] = audio["length"]
            data["mimetype"] = audio["type"]
            yield Message.Url, url, data


###############################################################################
# XML Parsers #################################################################


_ns_map = (
    ("{http://www.w3.org/2005/Atom}", "atom"),
    ("{http://purl.org/rss/1.0/modules/content/}", "content"),
    ("{http://www.itunes.com/dtds/podcast-1.0.dtd}", "itunes"),
)


def _get_key(element):
    tag = element.tag
    if "{" not in tag:
        return tag
    # remove namespace
    for ns, orig in _ns_map:
        if ns in tag:
            return "{}_{}".format(orig, tag.rpartition("}")[-1])
    return tag


def _get_key_metadata(element):
    key = _get_key(element)
    if key != "itunes_category":
        return key
    # smuggle 'text'
    return (key, element.attrib["text"])


def _flatten(key, value):
    """Recursively flatten nested objects in the form of
    ```
    {("itunes_category", "cat1"): {
        ("itunes_category", "cat2"): {("itunes_category", "cat3"): "cat3"},
    }}
    ```
    """
    yield key[-1]
    if isinstance(value, str):
        return
    # assume dict
    for t in value.items():
        yield from _flatten(*t)


def _extr(element):
    txt = element.text
    if not txt or not txt.strip("\n\t"):
        return element.attrib.get("text") or element.attrib.get("href")

    if len(txt) > 3:
        return txt
    lower = txt.lower()
    if lower == "yes":
        return True
    if lower == "no":
        return False

    return txt


def _extr_item(element):
    if element.tag == "guid":
        data = {"guid": element.text}
        data.update(element.attrib)
        data["isPermaLink"] = True if data["isPermaLink"] == "true" else False
        return data

    if element.tag == "enclosure":
        return element.attrib

    return _extr(element)


def _elements_to_dict(element, get_key=_get_key, extr=_extr):
    """Recursively extract useful information in an element (or a
    list of elements) and convert it into a `dict`
    """
    if len(element):
        return {get_key(child): _elements_to_dict(child, get_key, extr)
                for child in element}
    return extr(element)
