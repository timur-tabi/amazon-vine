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
import time
import urllib2
from bs4 import BeautifulSoup
import mechanize
import webbrowser
import datetime

import getpass
from optparse import OptionParser

your_queue_url = 'https://www.amazon.com/gp/vine/newsletter?ie=UTF8&tab=US_Default'
vine_for_all_url = 'https://www.amazon.com/gp/vine/newsletter?ie=UTF8&tab=US_LastChance'

def get_list(url, name):
    global options

    while True:
        br = mechanize.Browser()

        # Necessary for Amazon.com
        br.set_handle_robots(False)
        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.10 (maverick) Firefox/3.6.13')]

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

    list = set()
    for link in soup.find_all('tr', {'class':'v_newsletter_item'}):
        list.add(link['id'])

    if len(list) == 0:
        print datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open('debug.html', 'w') as f:
            print >>f, html
        with open('debug.txt', 'w') as f:
            for link in soup.find_all('tr', {'class':'v_newsletter_item'}):
                print >>f, link

    print 'Found %u items' % len(list)
    return list

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

your_queue_list = get_list(your_queue_url, "Youe Queue")
vine_for_all_list = get_list(vine_for_all_url, "Vine For All")

while True:
    print 'Waiting %u minute%s' % (options.wait, 's'[options.wait == 1:])
    time.sleep(options.wait * 60)

    your_queue_list2 = get_list(your_queue_url, "Youe Queue")
    for link in your_queue_list2:
        if link not in your_queue_list:
            print datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'New item:', link
            webbrowser.open_new_tab('https://www.amazon.com/gp/vine/product?ie=UTF8&asin=%s&tab=US_Default' % link)

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

    # If there are no items, then assume that it's a glitch.  Otherwise, the
    # next pass will think that all items are new and will open a bunch of
    # browser windows.
    if vine_for_all_list2:
        vine_for_all_list = vine_for_all_list2

