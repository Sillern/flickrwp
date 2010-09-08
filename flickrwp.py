#!/usr/local/bin/python
"""
Copyright (c) 2007, Hiroshi Ayukawa

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

            THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
            "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
            LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
            A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
            CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
            EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
            PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
            PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
            LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
            NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
            SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

$LastChangedDate$
"""

import os, optparse, sys, random, time
import urllib2, urllib
import xml.parsers.expat
import cPickle as pickle
from hashlib import sha1

from datetime import date, timedelta

random.seed()

APIKEY = "e1bece9de5776d1259ed309428ff04c1"
URLBASE = "http://api.flickr.com/services/rest/?"

class ResponseParser:
    def __init__(self):
        self.parser = xml.parsers.expat.ParserCreate()
        self.data = {}
        self.cur = self.data
        self.body = None
        self.hie = []
        self.parser.StartElementHandler = self.start_element
        self.parser.EndElementHandler = self.end_element
        self.parser.CharacterDataHandler = self.char_data

    def parse(self, xmlstr):
        self.parser.Parse(xmlstr)
        return self.data

    def start_element(self, name, attrs):
        self.hie.append(self.cur)
        d={}
        d["__attrs__"] = attrs
        d["__child__"] = {}
        d["__body__"] = ""
        if not self.cur.has_key(name):
            self.cur[name] = []
        self.cur[name].append(d)
        self.cur = d["__child__"]
        self.body = d["__body__"]


    def end_element(self, name):
        self.cur = self.hie.pop()

    def char_data(self, data):
        self.body = self.body + data

def callMethod(method, *a, **keys):

    url = [URLBASE, "method=", method, "&api_key=", APIKEY]
    for k,v in keys.iteritems():
        url.append("&")
        url.append(k)
        url.append("=")
        url.append(urllib.quote(v))

    res = urllib.urlopen("".join(url))
    parser = ResponseParser()
    p = parser.parse(res.read())
    res.close()
    del res
    return p

def SaveImage(cache_path, remote_source, metadata):
    try:
        if remote_source == None:
            return

        bp = urllib.urlopen(remote_source)
        data = bp.read()
        bp.close()
        del bp

        sha1hash = sha1(data).hexdigest()
        
        print sha1hash, metadata

        filepath = cache_path + os.path.sep + sha1hash
        image_filepath = filepath + ".jpg"
        metadata_filepath = filepath + ".meta"

        fp = file(image_filepath, "wb")
        fp.write(data)
        fp.close()

        fp = file(metadata_filepath, "wb")
        pickle.dump(metadata, fp)
        fp.close()

    except Exception, e:
        print e

def getInterestingImages(cache_path, date):
    res = callMethod("flickr.interestingness.getList", date=str(date), extras="tags")
    res = res["rsp"][0]
    if res["__attrs__"]["stat"] == "fail":
        print "getPublicList failed"
        return

    total = res["__child__"]["photos"][0]["__attrs__"]["perpage"]

    for photoNum in range(0, int(total)):
        try:

            tags = res["__child__"]["photos"][0]["__child__"]["photo"][photoNum]["__attrs__"]["tags"]

            if "nsfw" in tags.split(" "):
                print "NSFW", tags
                continue

            photo = res["__child__"]["photos"][0]["__child__"]["photo"][photoNum]["__attrs__"]
            farmid = photo["farm"]
            serverid = photo["server"]
            secret = photo["secret"]

            getsizes = callMethod("flickr.photos.getSizes", photo_id=photo["id"])["rsp"][0]
            if getsizes["__attrs__"]["stat"] == "fail":
                print "getSizes failed"
                return

            imageinfo = getsizes["__child__"]["sizes"][-1]["__child__"]["size"][-1]["__attrs__"]
            maxsize = imageinfo["height"], imageinfo["width"]
            source = imageinfo["source"]

            SaveImage(cache_path, source, imageinfo)

        except Exception, e:
            print e
            print tags
            print photo


    return total


if __name__ == "__main__":
    try:
        parser = optparse.OptionParser("""
        ./flickrwp.py [options]

        Example Usage:

            ./flickrwp.py -d 2008-10-02

        """)

        parser.add_option("-d", "--date", dest="date", help="date", default=None)
        parser.add_option("-p", "--cachepath", dest="cachepath", help="cachepath", default=None)
        parser.add_option("-t", "--time", dest="time", help="time to wait in [min.] (default: 10 min.)", type="int", default=10)


        (options, args) = parser.parse_args()

        if options.date == None:
            options.date = date.today() - timedelta(days=7)

        if options.cachepath == None:
            options.cachepath = os.getenv("HOME") + os.path.sep + "flickrwp" + os.path.sep + "images"

        if not os.path.exists(options.cachepath):
            os.mkdir(options.cachepath)

        print "Fetching interesting images"
        getInterestingImages(options.cachepath, options.date)

    except Exception, e:
        print e
        sys.exit(1)
