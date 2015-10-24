#!/usr/bin/env python

# Copyright 2014, Timur Tabi

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import re
import time
import urllib2
import webbrowser
import datetime
import subprocess

import getpass
from optparse import OptionParser

# Try to import packages that the user might not have
try:
    from bs4 import BeautifulSoup
except Exception as e:
    print "Please install the bs4 (BeautifulSoup 4.x) package from"
    print "http://www.crummy.com/software/BeautifulSoup/"
    print e
    sys.exit(1)

try:
    import mechanize
except Exception as e:
    print "Please install the mechanize package from"
    print "https://pypi.python.org/pypi/mechanize/"
    print e
    sys.exit(1)

try:
    import fake_useragent
except Exception as e:
    print "Please install the fake_useragent package from"
    print "https://pypi.python.org/pypi/fake-useragent"
    print e
    sys.exit(1)

# Initialize the fake_useragent module.  This will take a minute
print "Initializing fake_useragent"
ua = fake_useragent.UserAgent(cache=False)

your_queue_url = 'https://www.amazon.com/gp/vine/newsletter?ie=UTF8&tab=US_Default'
vine_for_all_url = 'https://www.amazon.com/gp/vine/newsletter?ie=UTF8&tab=US_LastChance'

def get_list(url, name):
    global options
    global ua

    while True:
        br = mechanize.Browser()

        # Necessary for Amazon.com
        br.set_handle_robots(False)
        br.addheaders = [('User-agent', ua.random)]

        try:
            print 'Opening %s website' % name
            br.open(url)

            print 'Logging in'
            # Select the sign-in form
            br.select_form(name='signIn')
            br['email'] = options.email
            br['password'] = options.password
            response = br.submit()

            break
        except urllib2.HTTPError as e:
            print e
        except urllib2.URLError as e:
            print 'URL Error', e
        except Exception as e:
            print 'General Error', e
            print br
            print br.forms()
            sys.exit(1)

    print 'Reading response'
    html = response.read()
    br.close()
    print 'Parsing response'
    soup = BeautifulSoup(html)

    asins = set()
    for link in soup.find_all('tr', {'class':'v_newsletter_item'}):
        if link['id'] in asins:
            print 'Duplicate in-stock item:', link['id']
        asins.add(link['id'])

    if len(asins) == 0:
        print datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open('debug.html', 'w') as f:
            print >>f, html
        with open('debug.txt', 'w') as f:
            for link in soup.find_all('tr', {'class':'v_newsletter_item'}):
                print >>f, link

    # Find list of out-of-stock items.  All of items listed in the
    # 'vineInitalJson' variable are out of stock.  Also, Amazon's web
    # developers don't know how to spell.  "Inital"?  Seriously?
    for script in soup.find_all('script', {'type':'text/javascript'}):
        for s in script.findAll(text=True):
            m = re.search(r'^.*vineInitalJson(.*?)$', s, re.MULTILINE)
            if m:
                # {asin:"B007XPLI56"},
                oos = re.findall('{"asin":"([^"]*)"}', m.group(0).encode('ascii','ignore'))

                # Remove all out-of-stock items from our list
                asins.difference_update(oos)

    print 'Found %u items' % len(asins)
    return asins

# Return True if the display is off
def asleep_mac():
    from Quartz import CGMainDisplayID

    # A hackish way to create a static local variable in Python
    if not hasattr(asleep_mac, "once"):
        asleep_mac.once = False

        # If we're on a Mac, use Quartz to read the current Display ID, and
        # store it. This only works if the user has launched the script
        # while logged into his account on the GUI.
        asleep_mac.display_id = CGMainDisplayID()

    try:
        # The pmset program can tell us if the display is on, off, or asleep
        output = subprocess.check_output(['pmset','-g','powerstate','AppleDisplay'])
        m = re.search('^AppleDisplay.*USEABLE', output, re.MULTILINE)
        if not m:
            # Display is turned off or asleep
            return True

        # If the Display ID has changed, then we've fast-switched to another
        # user, and so it's the same thing as being asleep.
        return asleep_mac.display_id != CGMainDisplayID()
    except Exception as e:
        if not asleep_mac.once:
            print "Warning: pmset not installed and/or broken"
            # Display the warning only once
            asleep_mac.once = True

        return False

def asleep_linux():
    global options

    # A hackish way to create a static local variable in Python
    if not hasattr(asleep_linux, "once"):
        asleep_linux.once = False

    try:
        output = subprocess.check_output(['xprintidle'])
        idle_ms = int(output)

        # If the
        return idle_ms > (options.wait * 60 * 1000)
    except:
        if not asleep_linux.once:
            print "Warning: xprintidle not installed and/or broken"
            # Display the warning only once
            asleep_linux.once = True

        return False

def asleep():
    if sys.platform == "darwin":
        return asleep_mac()

    if sys.platform.startswith('linux'):
        return asleep_linux()

    return False

parser = OptionParser(usage="usage: %prog [options]")
parser.add_option("-e", dest="email",
    help="Amazon.com email address (default is AMAZON_EMAIL environment variable)",
    type="string", default=os.getenv('AMAZON_EMAIL'))
parser.add_option("-p", dest="password",
    help="Amazon.com password (default is AMAZON_PASSWORD environment variable)",
    type="string", default=os.getenv('AMAZON_PASSWORD'))
parser.add_option("-w", dest="wait",
    help="Number of minutes to wait between iterations (default is %default minutes)",
    type="int", default=10)

(options, args) = parser.parse_args()

if not options.email:
    options.email = raw_input('Amazon.com email address: ')
    if not options.email:
        sys.exit(0)

if not options.password:
    options.password = getpass.getpass('Amazon.com password: ')
    if not options.password:
        sys.exit(0)

# Test if asleep() works before we start
asleep()

your_queue_list = get_list(your_queue_url, "Your Queue")
vine_for_all_list = get_list(vine_for_all_url, "Vine For All")

while True:
    print 'Waiting %u minute%s' % (options.wait, 's'[options.wait == 1:])
    time.sleep(options.wait * 60)
    if asleep():
        continue

    your_queue_list2 = get_list(your_queue_url, "Your Queue")
    for link in your_queue_list2:
        if link not in your_queue_list:
            print datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'New item:', link
            webbrowser.open_new_tab('https://www.amazon.com/gp/vine/product?ie=UTF8&asin=%s&tab=US_Default' % link)
            time.sleep(1)

    # If there are no items, then assume that it's a glitch.  Otherwise, the
    # next pass will think that all items are new and will open a bunch of
    # browser windows.
    if your_queue_list2:
        your_queue_list = your_queue_list2

    vine_for_all_list2 = get_list(vine_for_all_url, "Vine For All")
    for link in vine_for_all_list2:
        if link not in vine_for_all_list:
            print datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'New item:', link
            webbrowser.open_new_tab('https://www.amazon.com/gp/vine/product?ie=UTF8&asin=%s&tab=US_LastChance' % link)
            time.sleep(1)

    # If there are no items, then assume that it's a glitch.  Otherwise, the
    # next pass will think that all items are new and will open a bunch of
    # browser windows.
    if vine_for_all_list2:
        vine_for_all_list = vine_for_all_list2
