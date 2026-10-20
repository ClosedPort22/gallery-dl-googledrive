# gallery-dl-addons

Extractor add-ons for [*gallery-dl*](https://github.com/mikf/gallery-dl) that are out of scope for the main project.

## Why?

*gallery-dl* provides a highly configurable framework that handles things such as sleeping between requests and skipping already downloaded files. It can technically be used to download any type of file, not just images. By writing custom extractors for *gallery-dl* instead of dedicated downloaders from scratch, we can instantly take advantage of these features and avoid having to reinvent the wheel.

For example, if someone shares with you a Google Drive folder that gets updated often, you can use the Google Drive extractor to check for updates and only download new or changed files as they appear.

One downside of this approach, however, is that the internal API used by *gallery-dl* is not guaranteed to be stable; when it changes, the extractors in this repository must be manually fixed even if the external sites remain unchanged.

## Usage

Move the modules to your location of choice and modify `module-sources`
in the config file accordingly. Then invoke *gallery-dl* with the `-c`
option:

```bash
$ gallery-dl -c addons.conf https://drive.google.com/file/d/0B9P1L--7Wd2vU3VUVlFnbTgtS2c/view
* ./googledrive/0B9P1L--7Wd2vU3VUVlFnbTgtS2c_spam.txt
```

Alternatively, you can add the relevant configuration options to your
main config file and use the add-ons like built-in extractors.

## Requirements

Python 3.9+

## Inspired By

* [gallery-dl](https://github.com/mikf/gallery-dl)
* [gdown](https://github.com/wkentaro/gdown)
* [yt-dlp](https://github.com/yt-dlp/yt-dlp)
* [OpenDirectoryDownloader](https://github.com/KoalaBear84/OpenDirectoryDownloader)
* [mediafire-dl](https://github.com/Juvenal-Yescas/mediafire-dl)
* [JDownloader](https://github.com/mirror/jdownloader)
* [PatreonDownloader](https://github.com/Foxite/PatreonDownloader)
* [xeuledoc](https://github.com/Malfrats/xeuledoc)
* [FanFicFare](https://github.com/JimmXinu/FanFicFare)
* [py-kraken](https://github.com/tha23rd/py-kraken)

## License

MIT License
