#!/usr/bin/env python3.6

import time
import atexit
from yagmail import SMTP
from Addons import Addons
from time import strftime
from xmlrpc.client import SafeTransport
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost, GetPost


class SpecialTransport(SafeTransport):
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' \
                 ' (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'


class TPBPost:
    #Your website goes here
    wp_url = ""
    wp_username = ""
    wp_password = ""

    def __init__(self):
        self.database = Addons._SQLiteDB()
        self.dbcursor = self.database.cursor()

    def createPost(self, title, description, size, tags, links, category):
        wp = Client(self.wp_url, self.wp_username, self.wp_password, transport=SpecialTransport())
        post = WordPressPost()
        post.post_status = 'publish'
        title = title.replace('.', ' ')
        title = title.replace('_', ' ')
        post.title = title
        post.content = 'Size:<b> ' + size + '</b> <br /><br /><br />'
        post.content = post.content + description
        post.content = post.content + '<br /><div class='"downLinks"'>Download Links:</div>'

        addLinks = '<textarea readonly>'
        for link in links:
            addLinks = addLinks + link + '&#13;&#10;'
        addLinks = addLinks + '</textarea>'

        post.content = post.content + addLinks

        post.terms_names = {
            'post_tag': tags,
            'category': [category]
        }

        id = wp.call(NewPost(post))
        postLink = WordPressPost()
        postLink = wp.call(GetPost(id))
        return postLink.link

    def post(self, title, description, size, tags, links, category):
        while True:
            try:
                link = self.createPost(title, description, size, tags, links, category)
                return link
            except:
                print("Something went wrong when post, try again in 60 seconds...")
                time.sleep(60)

    def work(self):
        for content in Addons.Category:
            self.dbcursor.execute("SELECT * FROM " + content.name +
                                  " where Downloaded = '1' AND Tries > '0' AND Postlink = '' ")
            entries = self.dbcursor.fetchall()

            for entry in entries:
                print("("+strftime("%d/%m/%Y %H:%M")+")"+"Posting "+entry[0])

                if entry[6] == "":
                    tags = ""
                else:
                    tags = str(entry[6]).split(',')

                links = str(entry[7]).split(',')
                postLink = self.post(entry[0], entry[1], entry[5], tags, links, Addons.GetRealCategory(content.name))

                self.dbcursor.execute("UPDATE " + content.name + " set Postlink ='" + postLink +
                                      "' WHERE Title='" + entry[0] + "'")
                self.database.commit()
            time.sleep(60)

def exithandler():
    #Change email accordingly
    yag = SMTP({"@gmail.com": "Darkstar"}, "")
    yag.send("@live.com", "Error", "Posting Stopped")

atexit.register(exithandler)

content = TPBPost()

while True:
    content.work()