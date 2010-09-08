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


import os, optparse, sys, random, time, glob, logging, traceback
import urllib2, urllib
import xml.parsers.expat
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



def getFavorite(username, sizebound):
    res = callMethod("flickr.people.findByUsername", username=username)
    res = res["rsp"][0]
    if res["__attrs__"]["stat"] == "fail":
        print "findByUser failed"
        return

    user_id = res["__child__"]["user"][0]["__attrs__"]["nsid"]
    res = callMethod("flickr.favorites.getPublicList", user_id=user_id)
    res = res["rsp"][0]
    if res["__attrs__"]["stat"] == "fail":
        print "getPublicList failed"
        return
    return chooseOne(res, sizebound)

def chooseOne(res, sizebound):
    total = res["__child__"]["photos"][0]["__attrs__"]["perpage"]

    photoNum = random.randint(0,int(total) - 1)

    photo = res["__child__"]["photos"][0]["__child__"]["photo"][photoNum]["__attrs__"]
    farmid = photo["farm"]
    serverid = photo["server"]
    id = photo["id"]
    secret = photo["secret"]

    return getPhotoDetail(id, secret, sizebound)

def getByTag(tags, sizebound):
    res = callMethod("flickr.photos.search", tags=tags, tag_mode="all")
    res = res["rsp"][0]
    if res["__attrs__"]["stat"] == "fail":
        print "search failed"
        return

    return chooseOne(res, sizebound)

def getPhotoDetail(id, secret, sizebound):
    res = callMethod("flickr.photos.getSizes", photo_id=id, secret=secret)
    res = res["rsp"][0]
    if res["__attrs__"]["stat"] == "fail":
        print "getSizes failed"
        return
    source = None
    for x in res["__child__"]["sizes"][0]["__child__"]["size"]:
        if int(x["__attrs__"]["width"]) > sizebound:
               break
        source = x["__attrs__"]["source"]
        if x["__attrs__"]["label"] == "Original":
            break
    return source
    

if __name__ == "__main__":
    bufDir = os.getenv("HOME") + os.path.sep + ".flickrwp"
    if not os.path.exists(bufDir):
        os.mkdir(bufDir)

    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s LineNo:%(lineno)d %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename=bufDir + os.path.sep + 'flickrwp.log',
                    filemode='a')

    try:
        parser = optparse.OptionParser("""
        ./flickrwp.py [options]
        
        **************************************
        ****   Flicker Wallpaper for KDE  ****
        **************************************

        This Program fetchs a flickr user's favorite photo randomely and places it on desktop.
        This  only works on KDE/Linux.

        Example Usage:
        
         To get specified user's favorite photos: 
            ./flickrwp.py -u hiroshiykw -s 1280 -c 333399

         To get photos of tags:
            ./flickrwp.py -g iceland,mountain -s 1280 -c 333399

         One of -u(--user) and -g(--tag) should be specified.
         The two are not used both together.
         
        """)

        parser.add_option("-u", "--user", dest="user", help="user id (default: hiroshiykw)", default=None)
        parser.add_option("-s", "--size-bound", dest="size", help="upper bound of image width (default: 1200)", default=1200)
        parser.add_option("-c", "--color", dest="color", help="background color (default 333300)", default="333399")
        parser.add_option("-t", "--time", dest="time", help="time to wait in [min.] (default: 10 min.)", type="int", default=10)
        parser.add_option("-g", "--tag", dest="tag", help="comma-separated tags to search.", default=None)
        parser.add_option("-G", "--Gnome", dest="gnome", help="Using Gnome as desktop environment.If this option is NOT used, assume that you are using KDE.", action="store_true", default=False)
        

        (options, args) = parser.parse_args()
        if (options.user == None and options.tag == None) or (options.user != None and options.tag != None):
            print "You should specify either user (-u) or tags (-t)."
            sys.exit(1)            
        
        while True:                
            if options.user != None:
                fileInfo = getFavorite(options.user, options.size)
            elif options.tag != None:
                fileInfo = getByTag(options.tag, options.size)
            else:
                print "ARIENAI!!"
                sys.exit(1)
                
            if fileInfo != None:
                bp = urllib.urlopen(fileInfo)

            fname = bufDir + os.path.sep + str(int(time.time())) + "." + fileInfo[-3:]
            delfnames = list(glob.glob(bufDir + os.path.sep + "*"))
            
            fp = file(fname, "wb")
            fp.write(bp.read())
            fp.close()
            bp.close()
            del bp
            for d in delfnames:
                if d[-3:] == "log": continue
                os.remove(d)
            if not options.gnome:
                if os.system("/usr/bin/dcop kdesktop KBackgroundIface setColor '#%s' false" % options.color) != 0:
                    logging.error("dcop error 1")
                    sys.exit(1)
                if  os.system("/usr/bin/dcop kdesktop KBackgroundIface setColor '#%s' false" % options.color) != 0:
                    logging.error("dcop error 2")
                    sys.exit(1)
                if os.system("/usr/bin/dcop kdesktop KBackgroundIface setWallpaper %s 7" % fname) != 0:
                    logging.error("dcop error 3")
                    sys.exit(1)
                logging.info("changed to " + fname)
            else:
                import gconf
                client = gconf.client_get_default()
                client.set_string ("/desktop/gnome/background/picture_filename", fname)
                client.set_string("/desktop/gnome/background/picture_options", "centered")
            time.sleep(options.time * 60)
    except Exception, e:
        logging.error(e)
        logging.error(traceback.format_exc())
        sys.exit(1)
