# -*- coding: utf-8 -*-

"""Extractors for Bhadoo Drive Index"""

from gallery_dl.extractor.common import BaseExtractor, Message
from gallery_dl import text


class BhadooExtractor(BaseExtractor):
    """Base class for Bhadoo extractors"""
    basecategory = "bhadoo"
    subcategory = "folder"
    archive_fmt = "{id}"
    directory_fmt = ("{category}", "{path[0]:?//}", "{path[1]:?//}",
                     "{path[2]:?//}", "{path[3:]:J - /}")
    filename_fmt = "{id[:8]}_{filename}.{extension}"

    FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

    def __init__(self, match):
        BaseExtractor.__init__(self, match)
        # do not move these to _init
        self.id = ""
        self.base_path = ()
        self._drive_order = 0

    def _init(self):
        self._fetch_path = self.config("path", False)

    @staticmethod
    def prepare(file):
        """Adjust the content of a file or folder object"""
        file["date"] = text.parse_datetime(
            file["modifiedTime"], "%Y-%m-%dT%H:%M:%S.%f%z")

        if "size" in file:
            file["filesize"] = text.parse_int(file.pop("size"))
        if "fileExtension" in file:
            file["extension"] = ext = file.pop("fileExtension")
            if file["name"].endswith(ext):
                file["filename"] = file["name"][:-len(ext)-1]
            else:
                file["filename"] = file["name"]
        else:
            text.nameext_from_url(file["name"], file)

    def items(self):
        self.api = BhadooAPI(self)
        return self.files(self.base_path, self.id)

    def content(self, endpoint, id):
        """Interface for API endpoints"""

    def _fetch_parent_path(self, id):
        path = self.api.path("/{}:id2path".format(self._drive_order), id)
        if not path:
            return ()
        return tuple(text.unquote(path.strip("/")).split("/")[:-1])

    def files(self, parent_path, id="", parent_data=None):
        """Recursively yield files in a folder"""
        if not parent_path and id and self._fetch_path:
            parent_path = self._fetch_parent_path(id)
        folder_data = {"parent": parent_data, "path": parent_path}
        yield Message.Directory, folder_data

        folders = []
        # remove trailing slash to download as ZIP
        for file in self.content(
                endpoint="/{}/".format("/".join(parent_path)), id=id):
            self.prepare(file)
            if file["mimeType"] == self.FOLDER_MIME_TYPE:
                folders.append(file)
                continue
            url = file.get("link")
            if not url:
                self.log.debug("Download URL not found: %s", file["name"])
                folders.append(file)
                continue
            if url[0] == "/":
                url = self.root + url

            # if possible, fetch paths for individual files in search results
            file_id = file.get("id")
            if not parent_path and (id or id is None) and \
                    file_id and self._fetch_path:
                path = self._fetch_parent_path(file_id)
                if path:
                    folder_data["path"] = path
                    yield Message.Directory, folder_data
            file.update(folder_data)

            yield Message.Url, url, file

        for folder in folders:
            yield from self.files(
                parent_path + (folder["name"],), id=folder.get("id") or "",
                parent_data=folder)


BASE_PATTERN = BhadooExtractor.update({})


class BhadooFolderExtractor(BhadooExtractor):
    """Extractor for a folder"""
    pattern = BASE_PATTERN + r"(?:/?$|/((?!\d+:search).+))"
    test = (
        ("bhadoo:https://example.org"),
        ("bhadoo:https://example.org/"),
        ("bhadoo:https://example.org/0:/"),
        ("bhadoo:https://example.org/foo/bar/"),
        ("bhadoo:https://example.org/fallback?id=foo"),
        ("bhadoo:example.org/"),
    )

    def __init__(self, match):
        BhadooExtractor.__init__(self, match)
        path = match.group(match.lastindex)
        if path:
            if path.startswith("fallback?"):
                # id-based
                self.id = text.extr(path + "&", "id=", "&")
            else:
                # path-based
                self.base_path = tuple(
                    text.unquote(path.strip("/")).split("/"))
        # else: path-based, starts from root

    def _init(self):
        BhadooExtractor._init(self)
        if self.id:
            # make a request to the webpage to determine the drive number
            self._drive_order = text.extr(
                self.request(self.url).text,
                "current_drive_order", ";").strip(" =")

    def content(self, endpoint, id):
        return self.api.folder_content(
            "/{}:fallback".format(self._drive_order) if self.id else endpoint,
            id=id)


class BhadooSearchExtractor(BhadooExtractor):
    """Extractor for search results"""
    pattern = BASE_PATTERN + r"/(\d+):search\?q=(.+)"
    test = (
        ("bhadoo:https://example.org/0:search?q=a"),
    )

    def __init__(self, match):
        BhadooExtractor.__init__(self, match)
        self.query = match.group(match.lastindex)
        self._drive_order = do = match.group(match.lastindex-1)
        self._search_endpoint = "/{}:search".format(do)
        self._fallback_endpoint = "/{}:fallback".format(do)

    def items(self):
        self.api = BhadooAPI(self)
        return self.files(self.base_path, None)  # sentinel value

    def content(self, endpoint, id):
        if id is None:
            return self.api.search(self._search_endpoint, query=self.query)
        elif id:
            return self.api.folder_content(self._fallback_endpoint, id=id)
        else:
            return self.api.folder_content(endpoint, id=id)


class BhadooAPI():
    """Interface for the web API"""

    def __init__(self, extractor):
        self.api_root = extractor.root
        self.request = extractor.request
        self.log = extractor.log

        # handle misuse of 500 response code
        sreq = extractor.session.request

        def sreq_patched(method, url, **kwargs):
            resp = sreq(method, url, **kwargs)
            if url.endswith("id2path") and resp.status_code == 500:
                resp.status_code = 404
            return resp
        extractor.session.request = sreq_patched

    def folder_content(self, path, id="", password=""):
        return self._pagination(
            path, {"id": id, "type": "folder", "password": password})

    def search(self, path, query):
        return self._pagination(path, {"q": query})

    def path(self, path, id):
        """Fetch path for a given ID. Returns `None` if not found"""
        response = self._call(path, {"id": id}, fatal=False)
        try:
            return response["path"]
        except KeyError:
            self.log.debug("Got error while fetching path: %s, %s",
                           response.get("message"), response.get("error"))
            return None

    def _pagination(self, endpoint, params):
        page_token = ""
        page_index = 0
        while True:
            params["page_token"] = page_token
            params["page_index"] = page_index
            page = self._call(endpoint, params)
            yield from page["data"]["files"]
            page_token = page.get("nextPageToken")
            if not page_token:
                break
            try:
                page_index = page["curPageIndex"] + 1
            except (KeyError, TypeError):
                page_index = 1

    def _call(self, endpoint, params, **kwargs):
        return self.request(self.api_root + endpoint,
                            method="POST", json=params, **kwargs).json()
