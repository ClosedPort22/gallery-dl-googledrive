# -*- coding: utf-8 -*-

"""Extractors for Bhadoo Drive Index"""

from gallery_dl.extractor.common import BaseExtractor, Message
from gallery_dl import text


class BhadooExtractor(BaseExtractor):
    """Base class for Bhadoo extractors"""
    basecategory = "bhadoo"


BASE_PATTERN = BhadooExtractor.update({})


class BhadooFolderExtractor(BhadooExtractor):
    """Extractor for a folder"""
    subcategory = "folder"
    archive_fmt = "{id}"
    directory_fmt = ("{category}", "{path[0]:?//}", "{path[1]:?//}",
                     "{path[2]:?//}", "{path[3:]:J - /}")
    filename_fmt = "{id[:8]}_{filename}.{extension}"
    pattern = BASE_PATTERN + r"(.+)?"
    test = (
        ("bhadoo:https://example.org/"),
        ("bhadoo:https://example.org/0:/"),
        ("bhadoo:https://example.org/foo/bar/"),
        ("bhadoo:example.org/"),
    )

    FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

    def __init__(self, match):
        BaseExtractor.__init__(self, match)
        path = match.group(match.lastindex)
        if path:
            self.base_path = tuple(text.unquote(path.strip("/")).split("/"))
        else:
            self.base_path = ()

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

    def items(self):
        self.api = BhadooAPI(self)
        return self.files(self.base_path)

    def files(self, parent_path, parent_data=None):
        """Recursively yield files in a folder"""
        folder_data = {"parent": parent_data, "path": parent_path}
        yield Message.Directory, folder_data

        folders = []
        # remove trailing slash to download as ZIP
        for file in self.api.folder_content(
                "/{}/".format("/".join(parent_path))):
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
            file.update(folder_data)

            yield Message.Url, url, file

        for folder in folders:
            yield from self.files(parent_path + (folder["name"],), folder)


class BhadooAPI():
    """Interface for the web API"""

    def __init__(self, extractor):
        self.api_root = extractor.root
        self.request = extractor.request

    def folder_content(self, path, id="", password=""):
        return self._pagination(
            path, {"id": id, "type": "folder", "password": password})

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

    def _call(self, endpoint, params):
        return self.request(self.api_root + endpoint,
                            method="POST", json=params).json()
