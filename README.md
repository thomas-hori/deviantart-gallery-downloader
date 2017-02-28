# Before use

[Mechanize](http://wwwsearch.sourceforge.net/mechanize/) and [BeautifulSoup 4](https://www.crummy.com/software/BeautifulSoup/) are needed:

`sudo pip install mechanize bs4`

# Usage

`python deviantart_gallery_downloader.py [-i] [-n|-p|YOUR_USERNAME YOUR_PASSWORD] URL`

The downloader uses URLs of gallery pages, e.g.
http://azoexevan.deviantart.com/gallery/?catpath=/

Passing passwords in the command line will show up in bash history and ps
listings, and will of course echo.

Option|Explanation
---|---
-i|indefinite gallery mode (do not attempt to extract the gallery page count, simply read until there are no image links left). This is an extension not offered by the Ruby script.
-n|take login credentials from netrc.
-p|prompt for your login credentials. If possible, the password will not be echoed. This is an extension not offered by the Ruby script.

