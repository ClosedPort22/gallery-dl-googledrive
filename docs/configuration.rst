Configuration
#############

Once loaded, the Google Drive extractors can be configured in the same way as
built-in extractors. This file lists all available options that are specific
to said extractors.

For documentation on how to configure *gallery-dl*, see
`gallery-dl/docs/configuration.rst <https://github.com/mikf/gallery-dl/blob/master/docs/configuration.rst>`__.


Extractor Options
=================


extractor.googledrive.folder.metadata
-------------------------------------
Type
    ``bool``
Default
    ``false``
Description
    Fetch metadata for the base folder. If ``false``, the ``id`` of the folder
    is used in place of its name.
