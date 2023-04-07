Configuration
#############


For documentation on how to configure *gallery-dl*, see
`gallery-dl/docs/configuration.rst <https://github.com/mikf/gallery-dl/blob/master/docs/configuration.rst>`__.

See the respective config files for more info.


Extractor Options
=================


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
