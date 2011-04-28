import os
import sys
import csv
from ConfigParser import SafeConfigParser
import feedparser
import urllib2

_config_file = os.path.expanduser('~/.trss/config')
_feed_file = os.path.expanduser('~/.trss/feeds')
config = SafeConfigParser()

class TorrentFeed:
    def __init__(self, url, name=None, lastguid=None):
        self.url = url
        self.name = name
        self.lastguid = lastguid
        self._parsed = None
    def parse(self):
        if not self._parsed:
            self._parsed = feedparser.parse(self.url)
            if self._parsed.feed.has_key('title'):
                self.name = self._parsed.feed.title
        return self._parsed
    def set_last_index(self, index=0):
        parsed = self.parse()
        self.lastguid = parsed.entries[index].guid

    def download(self, folder):
        parsed = self.parse()
        downloads = []
        for entry in parsed.entries:
            if entry.guid == self.lastguid:
                break
            downloads.append(entry)
        downloads.reverse()
        for download in downloads:
            # Download, break on failure
            if download.enclosures:
                enclosure = download.enclosures[0]
                print 'Downloading {0} to {1}'.format(download.title, folder)
                remote = urllib2.urlopen(enclosure.href)
                filename = os.path.basename(enclosure.href)
                if filename.endswith('.torrent'):
                    # Strip the extension, it'll be re-applied later
                    filename = filename[:filename.rfind('.torrent')]
                local_file = '{0}.torrent'.format(filename)
                attempt = 0
                while os.path.exists(os.path.join(folder, local_file)):
                    attempt += 1
                    local_file = '{0} ({1}).torrent'.format(filename, attempt)
                local = open(os.path.join(folder, local_file), 'wb')
                local.write(remote.read())
                local.close()
                remote.close()
            self.lastguid = download.guid

def read_cfg():
    config.read(_config_file)

def write_cfg():
    try:
        if not os.path.exists(os.path.dirname(_config_file)):
            os.makedirs(os.path.dirname(_config_file))
        with open(_config_file, 'w') as config_file:
            config.write(config_file)
    except:
        print 'Could not write config file'

def read_feeds():
    try:
        feed_file = csv.reader(open(_feed_file, 'rb'))
        for url, name, lastguid in feed_file:
            feed = TorrentFeed(name, url, lastguid)
            feeds.append(feed)
    except:
        pass
    return feeds

def write_feeds():
    try:
        if not os.path.exists(os.path.dirname(_feed_file)):
            os.makedirs(os.path.dirname(_feed_file))
        feed_file = csv.writer(open(_feed_file, 'wb'))
        for feed in feeds:
            feed_file.writerow((feed.name, feed.url, feed.lastguid))
    except:
        raise
        print 'Could not write feeds file'

def add_rss(url, recent=0):
    existing = [f for f in feeds if f.url == url]
    if existing:
        feed = existing[0]
        feeds.remove(feed)
    else:
        feed = TorrentFeed(url)
    feed.set_last_index(recent)
    feeds.append(feed)
    return feed

def usage():
    print """Usage:
    {0} add <rss-url> [<recent-items>]
        Adds an RSS feed to follow

        rss-url:        Full URL to the RSS feed
        recent-items:   (Optional) number of recent items to queue
                        for downloading
    {0} remove <index>
        Remove an RSS feed

        index:          Numeric index of the feed to remove as
                        reported by the list command
    {0} list
        Displays a list of followed feeds

    {0} download
        Fetch all feeds and download new items
    """.format(sys.argv[0])

feeds = []

if __name__ == '__main__':
    read_cfg()
    read_feeds()

    arguments = sys.argv[1:]
    try:
        command = arguments.pop(0).lower()
    except:
        usage()
        exit(1)
    
    if command == 'add':
        try:
            url = arguments.pop(0)
        except:
            print 'You must specify an RSS url to add'
            exit(1)
        try:
            recent = int(arguments.pop(0))
        except:
            recent = 0
        feed = add_rss(url, recent)
        print "Added feed '{0}'".format(feed.name)
        write_feeds()
    elif command == 'remove':
        try:
            index = int(arguments.pop(0))
            feed = feeds.pop(index)
            print "Removed feed '{0}'".format(feed.name)
        except:
            print 'Invalid feed index'
            exit(1)
        write_feeds()
    elif command == 'list':
        for index, feed in enumerate(feeds):
            print '{0}: {1} - {2}'.format(index, feed.name, feed.url)
    elif command == 'download':
        try:
            folder = config.get('trss', 'download_folder')
        except:
            print 'Download folder is not set, using current directory'
            folder = os.getcwd()
        for feed in feeds:
            print 'FEED', feed.name
            feed.download(folder)
            write_feeds()
    elif command == 'set':
        try:
            key = arguments.pop(0)
        except:
            for section in config.sections():
                for key in config.options(section):
                    print "{0}.{1}: {2}".format(section, key, config.get(section, key))
            exit()
        try:
            value = arguments.pop(0)
        except:
            value = None

        try:
            section, key = key.split('.')
        except:
            section = 'trss'

        if value is None:
            try:
                print "{0}.{1}: {2}".format(section, key, config.get(section, key))
            except:
                print "Value {0}.{1} does not exist".format(section, key)
        else:
            if not config.has_section(section):
                config.add_section(section)
            config.set(section, key, value)
            write_cfg()
    else:
        usage()
        exit(1)
