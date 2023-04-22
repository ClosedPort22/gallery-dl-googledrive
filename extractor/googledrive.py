# -*- coding: utf-8 -*-

"""Extractors for Google Drive"""

from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import util, text, exception
from urllib.parse import urlencode
import re


BASE_PATTERN = r"(?:https?://)?(?:drive|docs)\.google\.com"


class GoogledriveExtractor(Extractor):
    """Base class for Google Drive extractors"""
    category = "googledrive"
    filename_fmt = "{id}.{extension}"
    archive_fmt = "{id}"
    root = "https://drive.google.com"

    @staticmethod
    def prepare(file):
        """Adjust the content of a file or folder object"""
        file["date"] = text.parse_datetime(
            file["modifiedDate"], "%Y-%m-%dT%H:%M:%S.%f%z")
        file["date_created"] = text.parse_datetime(
            file["createdDate"], "%Y-%m-%dT%H:%M:%S.%f%z")

        if "fileSize" in file:
            file["filesize"] = text.parse_int(file.pop("fileSize"))
        if "fileExtension" in file:
            file["extension"] = ext = file.pop("fileExtension")
            if file["title"].endswith(ext):
                file["filename"] = file["title"][:-len(ext)-1]
            else:
                file["filename"] = file["title"]
        file["parents"] = [x["id"] for x in file.get("parents") or ()]

    def _validate(self, response):
        # delegate checks to the downloader to be able to skip already
        # downloaded files without making any requests
        if "content-disposition" in response.headers:
            return True
        if "x-auto-login" in response.headers:  # redirected to login page
            raise exception.AuthorizationError()
        self.log.warning(
            "Quota exceeded for anonymous downloads. "
            "Use cookies to bypass this error.")
        return False

    def url_data(self, id, resource_key):
        """Get URL and data from file ID and (optionally) resourcekey"""
        url = "{}/uc?export=download&id={}&resourcekey={}&confirm=t".format(
            self.root, id, resource_key)
        data = {
            "id"            : id,
            "extension"     : "",
            "resourceKey"   : resource_key,
            "_http_validate": self._validate,
        }

        return url, data


class GoogledriveFileExtractor(GoogledriveExtractor):
    """Extractor for Google Drive files"""
    subcategory = "file"
    pattern = BASE_PATTERN + \
        (r"/(?:(?:uc|open)\?(?:[\w=&]+&)?id=([\w-]+)|"
         r"(?:file|presentation)/d/([\w-]+))"
         r"(?:.*resourcekey=([\w-]+))?")  # optional 'resourcekey'
    test = (
        ("https://drive.google.com/file/d/0B9P1L--7Wd2vU3VUVlFnbTgtS2c/view", {
            "pattern": r"^https://drive\.google\.com/uc\?export=download"
                       r"&id=0B9P1L--7Wd2vU3VUVlFnbTgtS2c&resourcekey="
                       r"&confirm=t$",
            "content": "69a5a1000f98237efea9231c8a39d05edf013494",
            "keyword": {"id": "0B9P1L--7Wd2vU3VUVlFnbTgtS2c"},
        }),
        # resourcekey
        ("https://drive.google.com/file/d/0B9P1L--7Wd2vU3VUVlFnbTgtS2c/"
         "view?resourcekey=0-WWs_XOSctfaY_0-sJBKRSQ", {
             "pattern": r"^https://drive\.google\.com/uc\?export=download"
                        r"&id=0B9P1L--7Wd2vU3VUVlFnbTgtS2c"
                        r"&resourcekey=0-WWs_XOSctfaY_0-sJBKRSQ&confirm=t$",
             "content": "69a5a1000f98237efea9231c8a39d05edf013494",
             "keyword": {"id": "0B9P1L--7Wd2vU3VUVlFnbTgtS2c",
                         "resourceKey": "0-WWs_XOSctfaY_0-sJBKRSQ"},
         }),
        # request metadata for file
        ("https://drive.google.com/file/d/0B9P1L--7Wd2vU3VUVlFnbTgtS2c/view", {
            "options": (("metadata", True),),
            "keyword": {
                "date"     : "type:datetime",
                "date_created": "type:datetime",
                "extension": "txt",
                "filesize" : int,
                "filename" : "spam",
                "title"    : "spam.txt",
            },
        }),
        # request metadata for file with resourcekey
        ("https://drive.google.com/file/d/0B-3Qtybib9z5RXJ3T0RCdFpvR3M/view?"
         "resourcekey=0-T9hv6EgWElqYLfi7HArd2g", {
             "options": (("metadata", True),),
             "keyword": {"title": "1 LEAN BOOK Lonnie Wilson.pdf"},
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
        # quota exceeded (big file!)
        # ("https://docs.google.com/file/d/0B1MVW1mFO2zmZHVRWEQ3Rkc3SVE/view",{
        #     "content": "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # empty
        # }),

        ("https://drive.google.com/file/d/0B9P1L--7Wd2vU3VUVlFnbTgtS2c/"
         "view?usp=drivesdk&resourcekey=0-WWs_XOSctfaY_0-sJBKRSQ"),
        ("https://drive.google.com/uc?id=0B9P1L--7Wd2vU3VUVlFnbTgtS2c&"
         "resourcekey=0-WWs_XOSctfaY_0-sJBKRSQ"),
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
        GoogledriveExtractor.__init__(self, match)
        self.id = match.group(1) or match.group(2)
        self.resource_key = match.group(3) or ""
        if self.config("metadata", False):
            self.api = GoogledriveWebAPI(self)
        else:
            self.api = None

    def metadata(self):
        if not self.api:
            return {"resourceKey": self.resource_key}
        data = self.api.file_info(self.id, self.resource_key)
        self.prepare(data)
        return data

    def items(self):
        url, data = self.url_data(self.id, self.resource_key)
        data.update(self.metadata())

        yield Message.Directory, data
        yield Message.Url, url, data


class GoogledriveFolderExtractor(GoogledriveExtractor):
    """Extractor for Google Drive folders"""
    subcategory = "folder"
    directory_fmt = ("{category}", "{path[0]:?//}", "{path[1]:?//}",
                     "{path[2]:?//}", "{path[3:]:J - /}")
    filename_fmt = "{id}_{filename}.{extension}"
    pattern = BASE_PATTERN + \
        (r"/drive/(?:mobile/)?folders/([\w-]+)"
         r"(?:.*resourcekey=([\w-]+))?")  # optional 'resourcekey'
    test = (
        # flat
        ("https://drive.google.com/drive/folders/"
         "1dQ4sx0-__Nvg65rxTSgQrl7VyW_FZ9QI", {
             "pattern": GoogledriveFileExtractor.pattern,
             "count": 3,
             "keyword": {
                 "parent": {"id": "1dQ4sx0-__Nvg65rxTSgQrl7VyW_FZ9QI"},
                 "path"  : ["1dQ4sx0-__Nvg65rxTSgQrl7VyW_FZ9QI"],
             },
         }),
        # folder with resourcekey, files don't have resourcekey
        ("https://drive.google.com/drive/folders/"
         "0B2SJp-WVjVPrb25NNXRWbWtCYWs?"
         "resourcekey=0-G_0dVFn0W27KPOlQt731Wg", {
             "pattern": r"^https://drive\.google\.com/uc\?export=download"
                        r"&id=[\w-]+&resourcekey=&confirm=t$",
             "count": 3,
             "keyword": {"parent": {
                 "id": "0B2SJp-WVjVPrb25NNXRWbWtCYWs",
                 "resourceKey": "0-G_0dVFn0W27KPOlQt731Wg",
             }},
         }),
        # files have resourcekey
        ("https://drive.google.com/drive/folders/"
         "0B5AjhfOF0uKGYUQxX3J2dkt4RkE?"
         "resourcekey=0-_DWxgrD5dHZogiqzo3q5lw", {
             # TODO: The first file is a text document
             # * doesn't have'fileExtension' field
             # * 'googleusercontent.com' always returns
             #   '500 Internal Server Error'
             # * can be exported to multiple formats
             "range": "2",
             "pattern": r"^https://drive\.google\.com/uc\?export=download"
                        r"&id=0B5AjhfOF0uKGNnVWLTlrNFM3MDA&resourcekey="
                        r"0-lCgPINsP-OoZx9hhQDAoyQ&confirm=t$",
         }),
        # request metadata for base folder
        ("https://drive.google.com/drive/folders/"
         "1dQ4sx0-__Nvg65rxTSgQrl7VyW_FZ9QI", {
             "options": (("metadata", True),),
             "count": 3,
             "keyword": {
                 "parent": {"title": "Forrest"},
                 "path"  : ["Forrest"],
             },
         }),
        # nested folder
        ("https://drive.google.com/drive/folders/"
         "1TMZoSAu4ecs_Q3GEEWfiyrQIPtj3DJAC", {
             "count": 2,
             "keyword": {
                 "date"     : "type:datetime",
                 "date_created": "type:datetime",
                 "extension": "txt",
                 "filesize" : int,
                 "filename" : "file",
                 "title"    : "file.txt",
                 "parent"   : dict,
                 "path"     : list,
             },
         }),
        # more than 50 files
        ("https://drive.google.com/drive/folders/"
         "1gd3xLkmjT8IckN6WtMbyFZvLR4exRIkn", {
             "count": 100,
         }),

        # 404
        ("https://drive.google.com/drive/folders/"
         "foobarkmjT8IckN6WtMbyFZvLR4exRIkn", {
             "options": (("metadata", True),),
             "exception": exception.NotFoundError,
         }),
        ("https://drive.google.com/drive/folders/"
         "foobarkmjT8IckN6WtMbyFZvLR4exRIkn", {
             "exception": exception.NotFoundError,
         }),

        ("https://drive.google.com/drive/folders/"
         "0B5AjhfOF0uKGYUQxX3J2dkt4RkE?usp=sharing&"
         "resourcekey=0-_DWxgrD5dHZogiqzo3q5lw"),
        ("https://drive.google.com/drive/mobile/folders/"
         "1gd3xLkmjT8IckN6WtMbyFZvLR4exRIkn"),
    )

    FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

    def __init__(self, match):
        GoogledriveExtractor.__init__(self, match)
        self.id = match.group(1)
        self.resource_key = match.group(2) or ""
        self.api = GoogledriveWebAPI(self)
        self.path = []

    def metadata(self):
        if not self.config("metadata", False):
            return {"id": self.id, "resourceKey": self.resource_key}
        data = self.api.folder_info(self.id, self.resource_key)
        self.prepare(data)
        return data

    def items(self):
        yield from self.files(self.id, self.metadata())

    def files(self, id, parent_data):
        """Recursively yield files in a folder"""
        self.path.append(parent_data.get("title") or parent_data["id"])

        folder_data = {"parent": parent_data, "path": self.path.copy()}
        yield Message.Directory, folder_data

        for file in self.api.folder_content(id, self.resource_key):
            self.prepare(file)
            if file["mimeType"] == self.FOLDER_MIME_TYPE:
                # trust 'orderBy'
                yield from self.files(file["id"], file)
                continue
            url, data = self.url_data(
                file["id"], file.get("resourceKey") or "")
            data.update(folder_data)
            data.update(file)

            print(url)
            yield Message.Url, url, data

        self.path.pop()


class GoogledriveWebAPI():
    """Interface for Google Drive web API"""

    API_KEY = "AIzaSyC1qbk75NzWBvSaDh6KnsjjA9pIrP4lYIE"
    # ref: https://developers.google.com/drive/api/v3/reference/files
    FIELDS = \
        ("kind,modifiedDate,modifiedByMeDate,lastViewedByMeDate,fileSize,"
         "owners(kind,permissionId,id),lastModifyingUser(kind,permissionId,"
         "id),hasThumbnail,thumbnailVersion,title,id,resourceKey,shared,"
         "sharedWithMeDate,userPermission(id,name,emailAddress,domain,role,"
         "additionalRoles,photoLink,type,withLink),permissions(id,name,"
         "emailAddress,domain,role,additionalRoles,photoLink,type,withLink),"
         "explicitlyTrashed,mimeType,quotaBytesUsed,copyable,fileExtension,"
         "sharingUser(kind,permissionId,id),spaces,version,teamDriveId,"
         "hasAugmentedPermissions,createdDate,trashingUser(kind,permissionId,"
         "id),trashedDate,parents(id),shortcutDetails(targetId,targetMimeType,"
         "targetLookupStatus),capabilities(canCopy,canDownload,canEdit,"
         "canAddChildren,canDelete,canRemoveChildren,canShare,canTrash,"
         "canRename,canReadTeamDrive,canMoveTeamDriveItem,"
         "canMoveItemWithinDrive,canMoveItemOutOfDrive,"
         "canMoveItemOutOfTeamDrive,canComment,canMoveChildrenWithinDrive),"
         "driveId,description,iconLink,alternateLink,"
         "copyRequiresWriterPermission,headRevisionId,md5Checksum,"
         "sha1Checksum,sha256Checksum,labels(starred,trashed,restricted,"
         "viewed)")
    QUERY_PARAMS = {
        "openDrive"    : "true",
        "syncType"     : 0,
        "errorRecovery": "false",
        "retryCount"   : 0,
    }
    OUTER_HEADERS = {
        'Content-Type': 'text/plain;charset=UTF-8;',
        'Origin'      : 'https://drive.google.com',
    }
    DATA = """--{boundary_marker}
content-type: application/http
content-transfer-encoding: binary

GET {path}?{query_params} HTTP/1.1
{headers}

--{boundary_marker}
"""

    def __init__(self, extractor):
        self.request = extractor.request
        self._find_json = re.compile("(?s)[^{]+(.+})").match

    def folder_content(self, folder_id, resource_key=None):
        """Yield folder content (including subfolders)"""
        params = self.QUERY_PARAMS.copy()
        params.update({
            # "reason"       : 102,
            "q": "trashed = false and '{}' in parents".format(folder_id),
            "fields": "kind,nextPageToken,items({}),incompleteSearch".format(
                self.FIELDS),
            "appDataFilter": "NO_APP_DATA",
            "spaces"       : "drive",
            "maxResults"   : 50,
            "includeItemsFromAllDrives": "true",
            "corpora"      : "default",
            "orderBy"      : "folder,title_natural asc",
        })
        rkey = "{}/{}".format(folder_id, resource_key) \
            if resource_key else None
        return self._pagination("/drive/v2beta/files", rkey, params)

    def folder_info(self, folder_id, resource_key=None):
        """Return folder info"""
        params = self.QUERY_PARAMS.copy()
        # reason 1001
        params["fields"] = self.FIELDS
        rkey = "{}/{}".format(folder_id, resource_key) \
            if resource_key else None
        return self._call(
            "/drive/v2beta/files/{}".format(folder_id), rkey, params)

    def file_info(self, file_id, resource_key=None):
        """Return file info"""
        params = {"fields": self.FIELDS, "enforceSingleParent": "true"}
        rkey = "{}/{}".format(file_id, resource_key) \
            if resource_key else None
        return self._call(
            "/drive/v2beta/files/{}".format(file_id), rkey, params)

    def _pagination(self, endpoint, resource_key, params):
        page_token = ""
        while True:
            params["pageToken"] = page_token
            page = self._call(endpoint, resource_key, params)
            yield from page["items"]
            page_token = page.get("nextPageToken")
            if not page_token:
                break

    def _call(self, endpoint, resource_key, params={}, **kwargs):
        """Call an API endpoint

        This encapsulates the HTTP request (as defined in 'DATA') in the
        payload of a normal HTTP POST request, which is then sent to
        https://clients6.google.com/batch/drive/v2beta
        """
        boundary_marker = "====={}=====".format(util.generate_token(6))
        params.update({"supportsTeamDrives": "true", "key": self.API_KEY})
        params_str = urlencode(params)  # safe="()'", quote_via=quote
        header = "X-Goog-Drive-Resource-Keys: {},".format(resource_key) \
            if resource_key else ""
        data = self.DATA.format(
            boundary_marker=boundary_marker,
            path=endpoint, query_params=params_str, headers=header).encode()
        outer_params = {
            "$ct": 'multipart/mixed; boundary="{}"'.format(boundary_marker),
            "key": self.API_KEY,
        }
        resp = self.request(
            "https://clients6.google.com/batch/drive/v2beta", method="POST",
            headers=self.OUTER_HEADERS, params=outer_params, data=data,
            **kwargs)
        data = util.json_loads(self._find_json(resp.text).group(1))
        if "error" not in data:
            return data
        error = data["error"]
        if error["code"] == 404:
            raise exception.NotFoundError("file or folder")
        raise exception.StopExtraction("Unexpected API response (%s: %s)",
                                       error["code"], error["message"])
