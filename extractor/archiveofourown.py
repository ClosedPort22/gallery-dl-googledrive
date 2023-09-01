# -*- coding: utf-8 -*-

"""Extractors for Archive of Our Own"""

from gallery_dl.extractor.common import Extractor, Message, exception
from gallery_dl import text

BASE_PATTERN = (r"(?:https?://)(?:archiveofourown\.(?:org|com|net)"
                r"|(?:www\.)?ao3\.org)")


class ArchiveofourownExtractor(Extractor):
    """Base class for AO3 extractors"""
    category = "archiveofourown"
    root = "https://archiveofourown.org"
    cookies_domain = ".archiveofourown.org"


class ArchiveofourownWorkExtractor(ArchiveofourownExtractor):
    """Extractor for AO3 stories"""
    subcategory = "work"
    archive_fmt = "{id}_{updated_at}_{is_completed}.{extension}"
    pattern = BASE_PATTERN + r"/(?:collections/[^/]+/)?works/(\d+)"
    test = (
        ("https://archiveofourown.org/works/41934561"),
        ("https://archiveofourown.net/works/41934561"),
        ("https://archiveofourown.com/works/41934561"),
        ("https://ao3.org/works/41934561"),
        ("https://www.ao3.org/works/41934561"),
        ("https://archiveofourown.com/works/137", {
            "keyword": {
                "Additional Tags": ("Community: sticksandsnark",),
                "Archive Warning": ("No Archive Warnings Apply",),
                "Bookmarks"      : int,
                "Category"       : ("F/M",),
                "Chapters"       : "1/1",
                "Characters"     : ("Rodney McKay", "Teyla Emmagan",),
                "Collections"    : "Sticks And Snark 2007",
                "Fandom"         : ("Stargate Atlantis",),
                "Hits"           : int,
                "Kudos"          : int,
                "Language"       : "English",
                "Published"      : "2008-09-16",
                "Rating"         : ("Teen And Up Audiences",),
                "Relationship"   : ("Rodney/Teyla",),
                "Words"          : int,
                "chapters"       : {},
                "collections_url": "re:/collections/Sticksandsnark2007$",
                "downloads"      : {
                    "AZW3"       : r"re:\.azw3\?updated_at=\d+$",
                    "EPUB"       : r"re:\.epub\?updated_at=\d+$",
                    "HTML"       : r"re:\.html\?updated_at=\d+$",
                    "MOBI"       : r"re:\.mobi\?updated_at=\d+$",
                    "PDF"        : r"re:\.pdf\?updated_at=\d+$",
                },
                "extension"      : "epub",
                "filename"       : "Summer Storm",
                "title"          : "Summer Storm",
                "is_completed"   : True,
                "summary": "<p>Teyla is hurt. Rodney is her comfort.</p>",
                "published_date" : "type:datetime",
                "updated_at"     : int,
                "updated_at_date": "type:datetime",
            },
            "count": 1,
        }),
        # custom CSS
        ("https://archiveofourown.org/works/49779421", {
            "keyword": {"workskin": r"re:^#workskin"},
        }),
        # chapters
        ("https://archiveofourown.org/works/49129429", {
            "keyword": {"chapters": {
                "123953188": "1. Prologue",
                "124027732": "2. Chapter 2",
                "124030549": "3. Chapter 3",
                "124108393": "4. Chapter 4",
                "124928227": "5. Chapter 5",
                "125416864": "6. Chapter 6",
                "125657206": "7. Chapter 7"
            }},
        }),
        # could have adult content (not rated)
        ("https://archiveofourown.org/works/30290274", {
            "options": (("view-adult", 0),),
            "count": 0,
        }),
        ("https://archiveofourown.org/works/30290274", {
            "options": (("format", "all"),),
            "count": 5,
        }),
        ("https://archiveofourown.com/works/137", {
            "options": (("format", "epub,html"),),
            "count": 2,
        }),
        ("https://archiveofourown.com/works/138", {
            "exception": exception.NotFoundError,
        }),
        # behind login wall
        ("https://archiveofourown.com/works/13", {
            "exception": exception.AuthorizationError,
        }),
    )

    def __init__(self, match):
        ArchiveofourownExtractor.__init__(self, match)
        self.id = match.group(1)

    def _init(self):
        if self.config("view-adult", True):
            self.cookies.set("view_adult", "true", domain=self.cookies_domain)

    def metadata(self, page):
        """Get metadata from webpage"""
        def strip_html(html):
            stripped = text.rextract(html, ">", "<")[0] or \
                html.rpartition(">")[-1]
            return stripped.strip("\n")

        numerical = ("Words", "Comments", "Kudos", "Bookmarks", "Hits")
        date = ("Published", "Updated", "Completed")

        meta = {"id": self.id}
        extr_page = text.extract_from(page)

        # chapters
        chapters = {}
        chapter_group = extr_page('<ul id="chapter_index"', "</ul>")
        for group in text.extract_iter(chapter_group, "<option", "</option>"):
            chapter_id = text.extr(group, 'value="', '"')
            chapters[chapter_id] = group.rpartition(">")[-1]
        meta["chapters"] = chapters

        # downloads
        downloads = {}
        download_group = extr_page('<li class="download"', "</ul>")
        updated_at = 0
        for group in text.extract_iter(download_group, "<li>", "</li>"):
            extr_dl = text.extract_from(group)
            url = self.root + extr_dl('href="', '"')
            if not updated_at:
                updated_at = text.parse_int(url.partition("updated_at=")[-1])
            name = extr_dl(">", "<")
            downloads[name] = url
        meta["downloads"] = downloads
        meta["updated_at"] = updated_at
        meta["updated_at_date"] = text.parse_timestamp(updated_at)

        # general metadata
        meta_group = extr_page('<dl class="work meta group">', '</dl>')
        for group in text.extract_iter(meta_group, '<dt class="', "</dd>"):
            if ">Stats:<" in group:
                # flatten stats
                group = group.rpartition('<dt class="')[-1]

            key = strip_html(text.extr(group, ">", "</dt>").strip(":\n"))

            if key == "Collections":
                extr = text.extract_from(group)
                meta["collections_url"] = self.root + extr('href="', '"')
                meta[key] = extr(">", "<")
            elif key == "Series":
                extr = text.extract_from(group)
                pos = extr('"position">', "<")
                url = extr('href="', '"')
                meta["series_url"] = self.root + url
                meta["series_id"] = url.rpartition("/")[-1]
                name = extr(">", "<")
                meta[key] = pos + name
                meta["series_name"] = name
            else:
                tags = tuple(strip_html(html) for html in
                             text.extract_iter(group, "<a class=", "</a>"))
                if tags:
                    meta[key] = tags
                else:
                    # parse int
                    value = strip_html(group)
                    if key in numerical:
                        meta[key] = text.parse_int(value.replace(",", ""))
                    # parse date
                    elif key in date:
                        meta[key.lower()+"_date"] = \
                            text.parse_datetime(value, format="%Y-%m-%d")
                        meta[key] = value
                    else:
                        meta[key] = value

        # work skin
        workskin = text.extr(page, '<style type="text/css">', "</style>")
        if workskin:
            meta["workskin"] = workskin.strip()

        meta["title"] = \
            extr_page('<h2 class="title heading">', "</h2>").strip()

        # summary
        meta["summary"] = text.extr(
            extr_page('<div class="summary module">', "</div>"),
            '<blockquote class="userstuff">', "</blockquote>").strip()

        # is the story completed?
        if "Completed" in meta:
            meta["is_completed"] = True
        else:
            current, _, total = meta.get("Chapters", "0/?").partition("/")
            meta["is_completed"] = current == total

        return meta

    def items(self):
        response = self.request(
            "{}/works/{}".format(self.root, self.id), notfound="work")
        if b"This work is only available to registered" in response.content:
            raise exception.AuthorizationError(
                "Login required to access member-only works")
        if b"This work could have adult content" in response.content:
            raise exception.StopExtraction("Adult content")
        if b"This work is part of an ongoing challenge" in response.content:
            raise exception.StopExtraction(
                "This work is part of an ongoing "
                "challenge and will be revealed soon")
        metadata = self.metadata(response.text)

        yield Message.Directory, metadata

        types = self.config("format", "epub")
        if types == "all":
            types = metadata["downloads"].keys()
        elif isinstance(types, str):
            types = types.split(",")

        for type in types:
            try:
                url = metadata["downloads"][type.upper()]
            except KeyError:
                continue
            text.nameext_from_url(url, metadata)
            # use download.archiveofourown.org by default
            # this saves 1 RTT
            metadata["_fallback"] = url
            yield (Message.Url,
                   url.replace(
                       self.root, "https://download.archiveofourown.org"),
                   metadata)


class ArchiveofourownTagExtractor(ArchiveofourownExtractor):
    """Extractor for all works with a given tag"""
    subcategory = "tag"
    pattern = BASE_PATTERN + r"/tags/([^/]+)/works(?:\?page=(\d+))?"
    test = (
        ("https://archiveofourown.org/tags/Douglas%20Mortimer/works", {
            "count": ">= 85",
        }),
        ("https://archiveofourown.org/tags/Douglas%20Mortimer/works?page=4", {
            "count": ">= 21",
        }),
        ("https://archiveofourown.org/tags/DouglasDouglas/works", {
            "exception": exception.NotFoundError,
        }),
    )

    def __init__(self, match):
        ArchiveofourownExtractor.__init__(self, match)
        self.tag = match.group(1)
        self.page = match.group(2) or 1

    def _pagination(self):
        url = "{}/tags/{}/works?page={}".format(self.root, self.tag, self.page)
        while True:
            response = self.request(url, notfound="tag")
            txt = response.text
            next = text.extr(txt, '<a rel="next" href="', '"')
            for id in text.extract_iter(txt, '<a href="/works/', '"'):
                if id.isnumeric():
                    yield "{}/works/{}".format(self.root, id)
            if not next:
                break
            url = self.root + next

    def items(self):
        for url in self._pagination():
            yield (Message.Queue, url,
                   {"_extractor": ArchiveofourownWorkExtractor})


class ArchiveofourownSeriesExtractor(ArchiveofourownExtractor):
    """Extractor for a series on AO3"""
    subcategory = "series"
    pattern = BASE_PATTERN + r"/series/(\d+)"
    test = (
        ("https://archiveofourown.org/series/67839", {
            "keyword": {
                "Bookmarks"     : int,
                "is_completed"  : False,
                "Creator"       : "NewNewDoctor (DisnerdingAvenger)",
                "Description"   : "<p>A series of fanfictions about"
                                  " Rose Tyler and the Doctor.</p>",
                "Series Begun"  : "2013-12-23",
                "Series Updated": "2019-04-15",
                "Words"         : int,
                "Works"         : int,
                "creator_url"   : r"re:/users/DisnerdingAvenger"
                                  r"/pseuds/NewNewDoctor$",
                "id"            : "67839",
                "name"          : "The Physician and His Flower",
                "series_begun_date"  : "type:datetime",
                "series_updated_date": "type:datetime",
            },
            "count": 11,
        }),
        ("https://archiveofourown.org/series/678304", {
            "exception": exception.NotFoundError,
        }),
        # needs login
        ("https://archiveofourown.org/series/67834", {
            "exception": exception.AuthorizationError,
        }),
    )

    def __init__(self, match):
        ArchiveofourownExtractor.__init__(self, match)
        self.id = match.group(1)

    def metadata(self, page):
        """Get metadata from series page"""
        extr = text.extract_from(page)

        numerical = ("Words", "Bookmarks", "Works")
        date = ("Series Begun", "Series Updated")

        meta = {
            "id"  : self.id,
            "name": extr('<h2 class="heading">', "</h2>").strip(),
        }

        groups = extr('<dl class="series meta group">', "</div")
        for key, value in zip(
            text.extract_iter(groups, "<dt>", "</dt>"),
            text.extract_iter(groups, "<dd>", "</dd>"),
        ):
            key = key.rstrip(":")
            if key == "Bookmarks":
                value = text.extr(value, ">", "<")
            elif key == "Creator":
                meta["creator_url"] = \
                    self.root + text.extr(value, 'href="', '"')
                value = text.extr(value, ">", "<")
            elif key == "Complete":
                key = "is_completed"
                value = True if value.strip().lower() == "yes" else False
            elif key == "Description":
                value = text.extr(
                    value, '<blockquote class="userstuff">', "</blockquote>")

            if key in numerical:
                value = text.parse_int(value.replace(",", ""))

            if key in date:
                meta[key.lower().replace(" ", "_")+"_date"] = \
                    text.parse_datetime(value, format="%Y-%m-%d")

            meta[key] = value
        return meta

    def items(self):
        response = self.request(
            "{}/series/{}".format(self.root, self.id), notfound="series")
        if b"This work is only available to registered" in response.content:
            raise exception.AuthorizationError(
                "Login required to access member-only works")

        txt = response.text
        metadata = self.metadata(txt)
        metadata["_extractor"] = ArchiveofourownWorkExtractor
        for id in text.extract_iter(txt, '<a href="/works/', '"'):
            if id.isnumeric():
                yield (Message.Queue,
                       "{}/works/{}".format(self.root, id), metadata)
