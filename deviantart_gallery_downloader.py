#!/usr/bin/env python
# -*- mode: python; charset: utf-8 -*-

import mechanize, bs4
import re, getpass, sys, time, os, traceback, getopt, netrc

# Translated and tweaked from Ruby version at https://github.com/xofred/deviantart-gallery-downloader

class DeviantartGalleryDownloader(object):
    HOME_URL = "https://www.deviantart.com/users/login"

    def __init__(self, opts, pargs):
        optsns = zip(*opts)[0] if opts else []
        u_n = self.use_netrc = ("-n" in optsns)
        u_p = self.use_prompt = ("-p" in optsns)
        if u_n or u_p:
            if len(pargs) != 1:
                self.display_help_message()
                sys.exit(1)
            self.gallery_url = pargs[0]
        else:
            if len(pargs) != 3:
                self.display_help_message()
                sys.exit(1)
            self.gallery_url = pargs[2]
        self.use_indefinite = ("-i" in optsns)
        self.no_store = ("-d" in optsns) # Presently useless.
        self.pargs = pargs
        #
        self.author_name = self.gallery_url.split('.')[0].split('//')[-1]
        if len(self.gallery_url.split('/')) == 6:
            self.gallery_name = self.gallery_url.split('/')[-1]
        else:
            self.gallery_name = "default-gallery"
        self.agent = mechanize.Browser()
        self.agent.set_handle_robots(False) # http://www.archiveteam.org/index.php?title=Robots.txt

    def fetch(self):
        t1 = time.time()

        self.create_image_directories()
        credentials = self.create_or_update_credential()
        self.login_to_deviantart(credentials)
        image_page_links = self.get_image_page_links()
        for index, page_link in enumerate(image_page_links):
            retry_count = 0
            while 1:
                try:
                    self.soup = bs4.BeautifulSoup(self.agent.open(page_link), "html5lib")
                    # For some reason, the next keeps blumming failing always on the same
                    # blumming pages in spite of the button complete with these blumming classes
                    # being blumming present when I browse it.  And other pages work.
                    dblsel = ".dev-page-button.dev-page-button-with-text.dev-page-download"
                    download_button_link = [a["href"] for a in self.soup.select(dblsel)]
                    image_link = [img["src"] for img in self.soup.select(".dev-content-full")]
                    download_link = download_button_link[0] if download_button_link else image_link[0]
                    file_path = self.get_file_path(index, image_page_links, download_link)
                    if (not os.path.exists(file_path)) or (not os.stat(file_path).st_size):
                        open(file_path,"wb").write(self.agent.open(download_link).read())
                except Exception: #i.e. let KeyboardInterrupt through.
                    traceback.print_exc()
                    if retry_count < 3:
                        retry_count += 1
                        print ("retrying...")
                        continue
                    else:
                        print (page_link)
                        print ("failed after 3 retries, next")
                break # Yes, dedented.

        print ("\nAll download completed. Check deviantart/%(author_name)s/%(gallery_name)s.\n\n"%self.__dict__)
        t2 = time.time()
        save = t2 - t1
        print ("Time costs: %d mins %d secs."%(save//60, save%60))

    def create_or_update_credential(self):
        # netrc module provides no support for storing???
        n = {}
        if self.use_prompt:
            sys.stdout.write("\nUsername: ")
            username = sys.stdin.readline().rstrip("\n")
            password = getpass.getpass("Password: ")
            n["deviantart.com"] = username, None, password
        elif self.use_netrc:
            n = netrc.netrc().hosts
        elif len(self.pargs) == 3:
            n["deviantart.com"] = self.pargs[0], None, self.pargs[1]
        else:
            self.display_help_message()
            sys.exit(1)
        return n

    def display_help_message(self):
        print ("""
python %s [-i] [-n|-p|YOUR_USERNAME YOUR_PASSWORD] URL

The downloader uses URLs of gallery pages, e.g.
http://azoexevan.deviantart.com/gallery/?catpath=/

Passing passwords in the command line will show up in bash history and ps
listings, and will of course echo.

-i  indefinite gallery mode (do not attempt to extract the gallery page
    count, simply read until there are no image links left). This is an
    extension not offered by the Ruby script.

-n  take login credentials from netrc.

-p  prompt for your login credentials. If possible, the password will not 
    be echoed. This is an extension not offered by the Ruby script.
"""%sys.argv[0])

    def create_image_directories(self):
        if not os.path.exists("deviantart"):
            os.mkdir("deviantart")
        if not os.path.exists(os.path.join("deviantart",self.author_name)):
            os.mkdir(os.path.join("deviantart",self.author_name))
        if not os.path.exists(os.path.join("deviantart",self.author_name,self.gallery_name)):
            os.mkdir(os.path.join("deviantart",self.author_name,self.gallery_name))

    def login_to_deviantart(self, credentials):
        print ("Logging in")
        retry_count = 0
        while 1:
            try:
                response = self.agent.open(self.HOME_URL)
                lda = lambda i:(hasattr(i, "attrs") and "id" in i.attrs and i.attrs["id"]=="login")
                for f in filter(lda, mechanize.ParseResponse(response)):
                    f["username"] = credentials["deviantart.com"][0]
                    f["password"] = credentials["deviantart.com"][2]
                f.click()
                #
                # dunno how to translate this to py mechanize:
                """
                if len(self.agent.cookie_jar) < 3:
                    print ("Log on unsuccessful (maybe wrong login/pass combination?)")
                    print ("You might not be able to fetch the age restricted resources")
                else:
                    print ("Log on successful")
                self.agent.pluggable_parser.default = mechanize.Download
                """
            except Exception: #i.e. let KeyboardInterrupt through.
                traceback.print_exc()
                if retry_count < 3:
                    retry_count += 1
                    print ("Will retry after 1 second")
                    time.sleep(1)
                    continue   
                else:
                    print ("Login failed after 3 retries")
                    print ("You might not be able to fetch the age restricted resources")
            break

    def get_image_page_links(self):
        retry_count = 0
        print ("Connecting to gallery")
        while 1:
            try:
                self.soup = bs4.BeautifulSoup(self.agent.open(self.gallery_url), "html5lib")
                page_links = []
                link_selector = 'a.torpedo-thumb-link'
                if not self.use_indefinite:
                    last_page_number = self.get_last_page_number()
                else:
                    last_page_number = "???"
                i = 0
                while ((self.use_indefinite and self.soup.select(link_selector))
                       or ((not self.use_indefinite) and i<last_page_number)):
                    current_page_number = i + 1
                    print ("(%d/%s)Analyzing %s"%(current_page_number, last_page_number, self.gallery_url))
                    page_link = [a["href"] for a in self.soup.select(link_selector)]
                    page_links.extend(page_link)
                    gallery_link = (self.gallery_url + "&") if ("?" in self.gallery_url) else (self.gallery_url + "?")
                    if current_page_number > 1:
                        gallery_link += "offset=" + str(current_page_number * 24)
                    self.soup = bs4.BeautifulSoup(self.agent.open(gallery_link), "html5lib")
                    i += 1
                return page_links
            except Exception: #i.e. let KeyboardInterrupt through.
                if retry_count < 3:
                    traceback.print_exc()
                    retry_count += 1
                    print ("will retry after 1 second")
                    time.sleep(1)
                    continue
                else:
                    print ("failed to connect to gallery after 3 retries, abort")
                    raise
            break

    def get_file_path(self, index, image_page_links, download_link):
        title_art_elem = self.soup.select(".dev-title-container h1 a")
        title_elem = title_art_elem[0]
        title_art = title_art_elem[-1].text
        title = title_elem.text

        print ("(%d/%d)Downloading \"%s\""%(index + 1, len(image_page_links), title))

        #Sanitize filename
        file_name = download_link.split('?')[0].split('/')[-1]
        file_id = title_elem['href'].split('-')[-1]
        file_ext = file_name.split('.')[-1]
        file_title = " ".join(title.strip().strip(".").strip().split()).replace('/', '-').replace('\\', '-')

        file_name = title_art+'-'+file_title+'.'+file_id+'.'+file_ext
        file_path = "deviantart/%s/%s/%s"%(self.author_name, self.gallery_name, file_name)
        return file_path

    def get_last_page_number(self):
        page_numbers_selector = '.zones-top-left .pagination ul.pages li.number'
        pages = self.soup.select(page_numbers_selector)
        last_page = pages[-1] if pages else None
        next_buttons = self.soup.select('.zones-top-left .pagination ul.pages li.next a')

        if last_page:
            last_page_number = int(last_page.text)
        elif (next_buttons) and (not "href" in next_buttons[0]):
            last_page_number = 1
        else:
            print ("Error: Cannot determine page numbers, abort (try with -i)")
            sys.exit(1)
        return last_page_number

if __name__ == "__main__":
    main = DeviantartGalleryDownloader(*getopt.gnu_getopt(sys.argv[1:], "pnid"))
    main.fetch()




