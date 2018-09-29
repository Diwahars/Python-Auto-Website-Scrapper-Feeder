#!/usr/bin/env python3.6

import re
import time
import atexit
import urllib3
import random
import requests
import urllib.parse
from yagmail import SMTP
from time import strftime
from Addons import Addons
from bs4 import BeautifulSoup


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TPBContent:
    timeOut = 5
    pirate = None
    database = None
    dbcursor = None
    pirateList = None
    userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' \
                ' (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'

    def __init__(self):
        self.database = Addons._SQLiteDB()
        self.dbcursor = self.database.cursor()
        self.getplist()

    def getplist(self):
        f = open("Pirates.txt", "r")
        self.pirateList = f.read().splitlines()
        f.close()

    def getcontent(self, dbname, cat):
        newContent = 0
        self.pirate = random.choice(self.pirateList)
        #print("("+strftime("%d/%m/%Y %H:%M")+")"+'Checking '+dbname)

        # Get all titles from front page
        while True:
            try:
                htmlpage = requests.get(self.pirate + cat, headers={'User-Agent': self.userAgent},
                                        timeout=self.timeOut, verify=False).text
                soupTitle = BeautifulSoup(htmlpage, "html.parser")
                titles = soupTitle.findAll(class_="detLink")

                if titles is None:
                    raise Exception

                break

            except:
                self.pirate = random.choice(self.pirateList)

        for title in titles:
            regex = r"[^\/]+$"
            m = re.search(regex, title.get("href"))
            finTitle = str(m.group(0))
            finTitle = urllib.parse.unquote(finTitle)
            self.dbcursor.execute("SELECT * FROM " + dbname + " where Title='%s'" % finTitle)
            entry = self.dbcursor.fetchone()

            # check only non existing titles
            if entry is None:
                nextTorrent = False
                # Get Magnet
                while True:
                    try:
                        torLink = title.get("href")

                        if 'https://' in torLink:
                            htmlpage = requests.get(title.get("href"),
                                                    headers={'User-Agent': self.userAgent},
                                                    timeout=self.timeOut, verify=False).text
                        else:
                            htmlpage = requests.get(self.pirate + title.get("href"),
                                                    headers={'User-Agent': self.userAgent},
                                                    timeout=self.timeOut, verify=False).text

                        soup = BeautifulSoup(htmlpage, "html.parser")

                        # Continue with the next torrent if not found
                        if soup.find('h2', text='Not Found (aka 404)'):
                            nextTorrent = True
                            break

                        # Continue with the next torrent if found privacy
                        if 'protect-your-privacy' in torLink:
                            nextTorrent = True
                            break

                        magnetLink = soup.find('div', class_='download')

                        if magnetLink is None:
                            raise Exception
                        else:
                            magnetLink = str(soup.find("a", href=re.compile('^magnet')).get("href"))
                            break
                    except:
                        self.pirate = random.choice(self.pirateList)
                        time.sleep(10)


                # Skip current torrent
                if nextTorrent:
                    continue

                # Get Description, empty if there is no description
                try:
                    description = str(soup.find('div', class_='nfo').find('pre').contents[0])
                except:
                    description = ""

                # Get Size, alternative version may occur
                try:
                    size = soup.find('dt', text='Size:').find_next_siblings('dd')[0]
                except:
                    size = soup.find('td', text='Size:').find_next_siblings('td')[0]

                sizeRegex = r"[0-9]*\.?[0-9]+\s[B|KiB|MiB|GiB]+\s"
                sizeMatch = re.findall(sizeRegex, str(size))
                finalSize = str(sizeMatch[0])

                # Get Tags separated with comma
                try:
                    TAGS = soup.find('dt', text='Tag(s):').find_next_siblings('dd')[0]
                    tagString = []
                    if TAGS:
                        for tg in TAGS:
                            tagChecker = str(tg.string)
                            if not (tagChecker.isspace()):
                                tagString.append(tg.string)
                        finTag = ",".join(tagString)
                except:
                    finTag = ""

                # Do not download files bigger than 10GB | Tries=0 Downloaded=1
                chkBytes = finalSize.split("\xa0")[1]
                chkSize = float(finalSize.split("\xa0")[0])

                if chkBytes == 'GiB' and chkSize > 10:
                    self.dbcursor.execute("INSERT INTO " + dbname + " values (?,?,?,?,?,?,?,?,?)",
                                          (finTitle, description, magnetLink, 0, 1, finalSize, finTag, "", ""))
                    self.database.commit()
                else:
                    self.dbcursor.execute("INSERT INTO " + dbname + " values (?,?,?,?,?,?,?,?,?)",
                                          (finTitle, description, magnetLink, 0, 0, finalSize, finTag, "", ""))
                    self.database.commit()
                    newContent += 1
                    time.sleep(10)

        if newContent != 0:
            print("("+strftime("%d/%m/%Y %H:%M")+")"+"Added " + str(newContent) + " " + str(dbname))

    def work(self):
        for content in Addons.Category:
            self.getcontent(content.name, content.value)
            time.sleep(60)

def exithandler():
    #Change mail accordingly
    yag = SMTP({"@gmail.com": "Darkstar"}, "")
    yag.send("@live.com", "Error", "Content Stopped")


atexit.register(exithandler)
content = TPBContent()

while True:
    content.work()