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


extractor.archiveofourown.view-adult
------------------------------------
Type
    ``bool``
Default
    ``true``
Description
    Fetch stories that could potentially contain adult content.


extractor.archiveofourown.format
--------------------------------
Type
    * ``string``
    * ``list`` of ``string``s
Default
    ``epub``
Description
    A (comma-separated) list of file formats to download.
    Accepted values are ``EPUB``, ``AZW3``, ``MOBI``, ``PDF``,
    and ``HTML`` (case insensitive).

    It is possible to use "all" instead of listing all values separately.


extractor.bhadoo.path
---------------------
Type
    ``bool``
Default
    ``false``
Description
    Try to fetch (base) path if an object is path-less.

    Note: This requires 1 additional HTTP request per directory or file.


extractor.disneyplus.region
---------------------------
Type
    ``string``
Default
    ``US``
Description
    Specifies which region to use. Accepts
    `ISO 3166-2 <https://en.wikipedia.org/wiki/ISO_3166-2>`__ country codes.


extractor.disneyplus.language
-----------------------------
Type
    ``string``
Default
    ``en``
Description
    Specifies which language to use. Accepts ``en``, ``en-GB``,
    ``zh-Hant``, etc.


extractor.disneyplus.program.seasons
------------------------------------
Type
    ``bool``
Default
    ``true``
Description
    Controls whether to fetch season metadata. This requires 1 HTTP request.


extractor.disneyplus.program.episodes
-------------------------------------
Type
    ``bool``
Default
    ``true``
Description
    Controls whether to fetch episode metadata. This requires 1 HTTP request
    per 30 episodes. This option will be ignored if
    `seasons <extractor.disneyplus.program.seasons_>`_ is set to ``false``.


extractor.disneyplus.program.extras
-----------------------------------
Type
    ``bool``
Default
    ``true``
Description
    Controls whether to fetch extras. This requires 1 HTTP request
    per 30 extras.


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
