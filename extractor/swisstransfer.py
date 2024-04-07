# -*- coding: utf-8 -*-

"""Extractors for SwissTransfer"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text


class SwisstransferLinkExtractor(Extractor):
    """Extractor for SwissTransfer links"""
    category = "swisstransfer"
    subcategory = "link"
    archive_fmt = "{UUID}"
    root = "https://www.swisstransfer.com"
    pattern = (r"(?:https?://)(?:www\.)?swisstransfer\.com/d/("
               r"[0-9a-f]{8}\b-[0-9a-f]{4}\b-[0-9a-f]{4}\b-[0-9a-f]{4}\b-"
               r"[0-9a-f]{12})")
    test = ()

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.link_uuid = match.group(1)

    @staticmethod
    def prepare(file):
        """Adjust the content of a file object"""
        text.nameext_from_url(file.pop("fileName"), file)
        file["filesize"] = file.pop("fileSizeInBytes")
        file["date"] = text.parse_datetime(file["createdDate"])
        file["date_expired"] = text.parse_datetime(file["expiredDate"])

    def items(self):
        data = self.request(
            "{}/api/links/{}".format(self.root, self.link_uuid),
            notfound="object").json()["data"]
        assert data["linkUUID"] == self.link_uuid
        download_host = data["downloadHost"]
        files = data["container"].pop("files")

        yield Message.Directory, data

        for file in files:
            self.prepare(file)
            url = "https://{}/api/download/{}/{}".format(
                download_host, self.link_uuid, file["UUID"])
            yield Message.Url, url, file
