#!/usr/bin/env python3.6

import os
import time
import signal
import atexit
import requests
import libtorrent
import subprocess
from yagmail import SMTP
from Addons import Addons
from time import strftime


class TPBTorrent:
    database = None
    dbcursor = None
    stopTorrent = None
    MaxTries = 10
    startupMagnetTime = 20
    samePercentMagnetTime = 60

    def __init__(self):
        self.database = Addons._SQLiteDB()
        self.dbcursor = self.database.cursor()

    def uploadFile(self, filename):
        while True:
            try:
                #Change the username/pass and file uploader accordingly
                link = subprocess.check_output(["plowup -q -a ':' rapidgator '" +
                                                filename + "' | tail +2"], shell=True)
                link = link.decode("utf-8")
                link = link.strip()
                return link
            except:
                print("Upload error, retry in 60sec")
                time.sleep(60)

    def RapidGupload(self, fList):
        linkList = []

        for fname in fList:
            fileName = os.getcwd() + "/Final/" + fname
            finalLink = self.uploadFile(fileName)
            linkList.append(finalLink)
        return linkList

    def alarmHandler(self, signum, frame):
        self.stopTorrent = True

    def torrentSizer(self, fileList, title):
        fileHND = open("./Temp/tmpfilelist.txt", "w")
        for file in fileList:
            filePath = file
            fileHND.write(filePath+"\n")
        fileHND.close()
        print("\nZipping...")
        os.system("cd " + os.getcwd() + "/Temp" + " &&  zip -q -s 500m '../Final/" + title + ".zip' -@ < tmpfilelist.txt")

    def torrentUpload(self):
        print("Uploading...")
        flist = os.listdir(os.getcwd() + "/Final")
        links = self.RapidGupload(flist)
        return links

    def torrentClean(self):
        os.system("rm -rf " + os.getcwd() + "/Temp/*")
        os.system("rm -rf " + os.getcwd() + "/Final/*")

    def getMagnet(self, magnetLink, title, cat):
        fileList = []
        session = libtorrent.session()
        session.listen_on(6881, 6891)
        params = {
            'save_path': './Temp',
            'storage_mode': libtorrent.storage_mode_t(2),
            'paused': False,
            'auto_managed': True,
            'duplicate_is_error': True}
        handle = libtorrent.add_magnet_uri(session, magnetLink, params)
        session.start_dht()

        print("("+strftime("%d/%m/%Y %H:%M")+")"+"Downloading > " + title)

        magnetTime = time.time()
        while not handle.has_metadata():
            time.sleep(1)

            if time.time() - magnetTime > self.startupMagnetTime:
                print("Skip > Startup Inactivity")
                return

        torinfo = handle.get_torrent_info()

        for x in range(torinfo.files().num_files()):
            fileList.append(torinfo.files().file_path(x))

        lastPrec = 0.0
        alarmStarted = False
        self.stopTorrent = False
        signal.signal(signal.SIGALRM, self.alarmHandler)

        while handle.status().state != libtorrent.torrent_status.seeding:
            s = handle.status()
            print("\r{0:.2f}% ".format(s.progress*100), flush=True, end="")
            time.sleep(1)

            if lastPrec == ("{0:.2f}".format(s.progress*100).split('.'))[0]:
                if not alarmStarted:
                    signal.alarm(self.samePercentMagnetTime)
                    alarmStarted = True
            else:
                if alarmStarted:
                    signal.alarm(0)
                    alarmStarted = False
            lastPrec = ("{0:.2f}".format(s.progress*100).split('.'))[0]

            if self.stopTorrent:
                print("\nSkip > Progress Inactivity")
                self.torrentClean()
                return

        self.torrentSizer(fileList, title)
        finalLinks = self.torrentUpload()
        dbLinks = ",".join(finalLinks)
        self.torrentClean()

        self.dbcursor.execute("UPDATE " + cat + " SET Uploadlink ='"+dbLinks+"' WHERE Title='" +title + "'")
        self.database.commit()

        self.dbcursor.execute("UPDATE " + cat + " SET Downloaded=1 WHERE Title='" + title + "'")
        self.database.commit()

    def getContent(self, category):
        print("Downloading > " + category)
        self.dbcursor.execute("SELECT * FROM " + category + " where Downloaded = '0'")
        entries = self.dbcursor.fetchall()

        for entry in entries:
            self.dbcursor.execute("UPDATE " + category + " set Tries=Tries+1 WHERE Title='" + entry[0] + "'")
            self.database.commit()

            self.dbcursor.execute("SELECT Tries FROM " + category + " WHERE Title='" + entry[0] + "'")
            tries = self.dbcursor.fetchone()

            if tries[0] > self.MaxTries:
                self.dbcursor.execute("DELETE FROM " + category + " WHERE Title ='" + entry[0] + "'")
                self.database.commit()
                continue
            else:
                self.getMagnet(entry[2], entry[0], category)

    def work(self):
        for content in Addons.Category:
            self.getContent(content.name)
            time.sleep(60)

def exithandler():
    #Change email accordingly
    yag = SMTP({"@gmail.com": "Darkstar"}, "")
    yag.send("@live.com", "Error", "Torrent Stopped")

atexit.register(exithandler)

content = TPBTorrent()

while True:
    content.work()
