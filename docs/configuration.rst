Configuration
#############


For documentation on how to configure *gallery-dl*, see
`gallery-dl/docs/configuration.rst <https://github.com/mikf/gallery-dl/blob/master/docs/configuration.rst>`__.

See the respective config files for more info.


Extractor Options
=================


extractor.abc.listen-episode.image
----------------------------------
Type
    ``bool``
Default
    ``true``
Description
    Extract image for the episode.


extractor.abc.listen-program.image
----------------------------------
Type
    ``bool``
Default
    ``false``
Description
    Extract image for the program. This requires 1 extra HTTP request.


extractor.disneyplus.region
---------------------------
Type
    ``string``
Default
    ``US``
Description
    Specifies which region to use. Accepts
    [ISO 3166-2](https://en.wikipedia.org/wiki/ISO_3166-2) country codes.


extractor.disneyplus.language
-----------------------------
Type
    ``string``
Default
    ``en``
Description
    Specifies which language to use. Accepts
    [ISO 639-1](https://en.wikipedia.org/wiki/ISO_639-1) language codes.


extractor.googledrive.folder.metadata
-------------------------------------
Type
    ``bool``
Default
    ``false``
Description
    Fetch metadata for the base folder. This requires 1 additional API request.
    If ``false``, the ``id`` of the folder is used in place of its name.


extractor.googledrive.file.metadata
-----------------------------------
Type
    ``bool``
Default
    ``false``
Description
    Fetch metadata for the file. This requires 1 API request per file.


extractor.mediafire.folder.metadata
-----------------------------------
Type
    ``bool``
Default
    ``false``
Description
    Fetch metadata for the base folder. This requires 1 additional API request.
    If ``false``, the ``folderkey`` of the folder is used in place of its name.


extractor.mediafire.file.metadata
---------------------------------
Type
    ``bool``
Default
    ``false``
Description
    Fetch metadata for the file. This requires 1 API request per file.


extractor.podbean.feed.podcast-logo
-----------------------------------
Type
    ``bool``
Default
    ``true``
Description
    Extract podcast logo.


extractor.podbean.feed.episode-logo
-----------------------------------
Type
    ``bool``
Default
    ``true``
Description
    Extract episode logo.
