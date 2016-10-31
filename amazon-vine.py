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
import cookielib

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
    print "Initializing fake_useragent"
    ua = fake_useragent.UserAgent(cache=False)
    # We want to use the same user agent every time.  Apparently, Amazon gets
    # less suspicious if we do.
    useragent = ua.ff;

except Exception as e:
    print "Please install the fake_useragent package from"
    print "https://pypi.python.org/pypi/fake-useragent"
    print e
    sys.exit(1)

try:
    import browsercookie
except Exception as e:
    print "Please install the browsercookie package from"
    print "https://pypi.python.org/pypi/browsercookie/"
    print e
    sys.exit(1)

your_queue_url = 'https://www.amazon.com/gp/vine/newsletter?ie=UTF8&tab=US_Default'
vine_for_all_url = 'https://www.amazon.com/gp/vine/newsletter?ie=UTF8&tab=US_LastChance'

# True = use Death By Captcha service
use_deathbycaptcha = False

# Show an image on the screen.  If the Python Image Library is available,
# then use it.  Otherwise, open a web browser window.  I'm not sure if
# this is useful, since on my system, webbrowser.open() uses the Image
# Viewer anyway.
def show_captcha(filename):
    try:
        import Image
        image = Image.open(filename)
        image.show()
    except Exception as e:
        # No image library, use existing webbrowser
        webbrowser.open_new('file://' + filename)

# Solve the image captcha.  If the Death By Captcha module is available,
# then use it, otherwise display the image on the screen and prompt the
# user to type in what it says.
def solve_captcha(filename):
    global options
    global use_deathbycaptcha

    show_captcha(filename)  # For debugging

    if use_deathbycaptcha:
        try:
            dbc = deathbycaptcha.HttpClient(options.dbcu, options.dbcp)
            captcha = dbc.decode(filename, 60)
            if captcha:
                # Sometimes the image shows blank spaces, and the text includes
                # those spaces, but Amazon doesn't like them.
                text = captcha['text'].encode('ascii','ignore')
                text = text.translate(None, ' ')
                print 'Death By Captcha returns', text
                try:
                    # It's not important if we can't get the balance
                    print 'Death By Captcha balance: %.3f cents' % dbc.get_balance()
                except Exception:
                    pass
                return text
            else:
                print 'Death By Captcha could not solve captcha'
        except Exception as e:
            print e  # For debugging
            pass

    # If Death By Captcha is unavailable or fails, then fall back to manual
    return raw_input('What word is in the image? ')

def login():
    global options
    global useragent

    br = mechanize.Browser(factory = mechanize.RobustFactory())

    # Load cookies from the selected web browser
    cj2 = getattr(browsercookie, options.browser)()

    # Create a new cookie jar to hold the cookies we want
    cj = cookielib.CookieJar()

    # We only want cookies for Amazon
    for cookie in cj2:
        if cookie.domain == '.amazon.com':
            cj.set_cookie(cookie)

    if not cj:
        print 'No Amazon session data found in browser "%s"' % options.browser
        sys.exit(1)

    # Load those cookies into mechanize for the session
    br.set_cookiejar(cj)

    # Necessary for Amazon.com
    br.set_handle_robots(False)
    br.addheaders = [('User-agent', useragent)]

    try:
        print 'Logging into Amazon.com'
        br.open('https://www.amazon.com/gp/vine')

        with open('login_form.html', 'w') as f:
            print >>f, br.response().read()

        # Select the sign-in form
        br.select_form(name='signIn')
        br['email'] = options.email
        br['password'] = options.password
        response = br.submit()

         # Make sure we actually logged in
        html = response.read()
        with open('login_response.html', 'w') as f:
            print >>f, html

        # Check for bad password
        # Fixme: not robust
        if 'Your email or password was incorrect' in html:
            print 'Invalid userid or password'
            sys.exit(1)

        if 'Enter a valid email or mobile number' in html:
            print 'Unable to log in (invalid email)'
            sys.exit(1)

        if 'Please Enable Cookies to Continue' in html:
            print 'Unable to log in (cookies disabled)'
            sys.exit(1)

        soup = BeautifulSoup(html)

        # Check for image captcha
        # Fixme: if the user waits too long to responde, the script terminates
        captcha = soup.find('img',{'id':'auth-captcha-image'})
        if captcha:
            response = br.retrieve(captcha['src'])
            print 'Login captcha detected, saved to', response[0]
            value = solve_captcha(os.path.realpath(response[0]))
            br.select_form(name='signIn')
            br['email'] = options.email
            br['password'] = options.password
            br['guess'] = value
            response = br.submit()
            # Fixme: we should verify that the login actually went through

        # Check for account verification
        # Fixme: this is untested.
        verify = soup.find('div', {'id':'dcq_question_1'})
        if verify:
            br.select_form(name='ap_dcq_form')
            text = verify.find('label')
            # Get the text of the 'label' tag, and remove all extra spaces
            prompt = ' '.join(text.get_text().split())
            # The prompt starts with '1. ', so remove that and
            # add an extra space after the ?
            prompt = prompt[3:] + ' '
            br['dcq_question_subjective_1'] = raw_input(prompt)
            br.submit()
            # Fixme: we should verify that the login actually went through

        return br
    except urllib2.HTTPError as e:
        print e
    except urllib2.URLError as e:
        print 'URL Error', e
    except Exception as e:
        print 'General Error', e

    sys.exit(1)

def download_vine_page(br, url, name = None):
    if name:
        print 'Opening %s website' % name
    try:
        response = br.open(url)
    except:
        return None

    if name:
        print 'Reading response'
    html = response.read()
    if name:
        print 'Parsing response'
    return BeautifulSoup(html)

def get_list(br, url, name):
    global options

    soup = download_vine_page(br, url, name)
    if not soup:
        return None

    asins = set()
    for link in soup.find_all('tr', {'class':'v_newsletter_item'}):
        if link['id'] in asins:
            print 'Duplicate in-stock item:', link['id']
        asins.add(link['id'])

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

        # Check if the system has been idle longer than we normally wait
        # between passes.
        return idle_ms > (options.wait * 60 * 1000)
    except:
        if not asleep_linux.once:
            print "Warning: xprintidle not installed and/or broken"
            # Display the warning only once
            asleep_linux.once = True

        return False

def asleep():
    global options

    # -w0 should only be used for testing
    if options.wait == 0:
        return False

    if sys.platform == "darwin":
        return asleep_mac()

    if sys.platform.startswith('linux'):
        return asleep_linux()

    return False

def open_vine_page(br, link, url):
    global options
    global tax

    print datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    soup = download_vine_page(br, url % link)
    # Make sure we don't get a 404 or some other error
    if soup:
        print 'New item:', link
        # Display how much tax it costs
        tags = soup.find_all('p', text=re.compile('Estimated tax value : \$[0-9\.]*'))
        if tags:
            tag = tags[0].contents[0]
            m = re.search('\$([0-9\.]*)', tag)
            if m:
                cost = float(m.group(1))
                print 'Tax cost: $%.2f' % cost
                # We only care about the cost if we're under the $600 limit.
                # If we're already over it, then show everything.
                if options.tax and tax < 500.0:
                    # If it's too expensive, then don't bother showing it
                    if cost >= (600.0 - tax):
                        print 'Too expensive'
                        return True
        webbrowser.open_new_tab(url % link)
        time.sleep(1)
        return True
    else:
        print 'Invalid item:', link
        return False

def update_tax_estimate(br):
    global tax

    soup = download_vine_page(br, 'https://www.amazon.com/gp/vine/account')
    if soup:
        year = datetime.datetime.today().year
        # A tax year starts from July 1 the previous year to June 30 of this year
        if (datetime.datetime.today().month > 6):
            year = year + 1
        tags = soup.find_all('li', text=re.compile('Estimated %4u: \$[0-9\.]*' % year))
        if tags:
            # Find the tax estimate for "this" year
            tag = tags[0].contents[0]
            m = re.search('\$([0-9\.]*)', tag)
            if m:
                tax = float(m.group(1))
                print 'Current %4u tax estimate: $%.2f' % (year, tax)

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
parser.add_option("--dbcu", dest="dbcu",
    help="Death By Captcha userid (default is DEATHBYCAPTCHA_USERID environment variable)",
    type="string", default=os.getenv('DEATHBYCAPTCHA_USERID'))
parser.add_option("--dbcp", dest="dbcp",
    help="Death By Captcha password (default is DEATHBYCAPTCHA_PASSWORD environment variable)",
    type="string", default=os.getenv('DEATHBYCAPTCHA_PASSWORD'))
parser.add_option("-t", dest="tax",
    help="Ignore items that would cause tax liability to exceed $600",
    action="store_true")
parser.add_option('--browser', dest='browser',
    help='Which browser to use ("firefox" or "chrome") from which to load the session cookies (default is "%default")',
    type="string", default='firefox')

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

# Test for Death By Captcha
try:
    import deathbycaptcha
    dbc = deathbycaptcha.HttpClient(options.dbcu, options.dbcp)
    if not dbc:
        print 'Death By Captcha login failed'
    else:
        print 'Death By Captcha balance: %.3f cents' % dbc.get_balance()
        dbc.close()
        use_deathbycaptcha = True
except Exception:
    pass

br = login()
if not br:
    print "Could not log in"
    sys.exit(1)

your_queue_list = get_list(br, your_queue_url, "Your Queue")

vine_for_all_list = get_list(br, vine_for_all_url, "Vine For All")
if not vine_for_all_list:
    # There's always a bunch of vine-for-all items.
    print 'Cannot get list of items'
    sys.exit(1)

br.close()

while True:
    print 'Waiting %u minute%s' % (options.wait, 's'[options.wait == 1:])
    time.sleep(options.wait * 60)
    if asleep():
        continue

    br = login()
    update_tax_estimate(br)
    your_queue_list2 = get_list(br, your_queue_url, "Your Queue")
    if your_queue_list2:
        for link in your_queue_list2.copy():
            if link not in your_queue_list:
                if not open_vine_page(br, link, 'https://www.amazon.com/gp/vine/product?ie=UTF8&asin=%s&tab=US_Default'):
                    # If the item can't be opened, it might be because the web site
                    # isn't ready to show it to me yet.  Remove it from our list so
                    # that it appears again as a new item, and we'll try again.
                    your_queue_list2.remove(link)

        # If there are no items, then assume that it's a glitch.  Otherwise, the
        # next pass will think that all items are new and will open a bunch of
        # browser windows.
        your_queue_list = your_queue_list2

    vine_for_all_list2 = get_list(br, vine_for_all_url, "Vine For All")
    if vine_for_all_list2:
        for link in vine_for_all_list2.copy():
            if link not in vine_for_all_list:
                if not open_vine_page(br, link, 'https://www.amazon.com/gp/vine/product?ie=UTF8&asin=%s&tab=US_LastChance'):
                    # If the item can't be opened, it might be because the web site
                    # isn't ready to show it to me yet.  Remove it from our list so
                    # that it appears again as a new item, and we'll try again.
                    vine_for_all_list2.remove(link)

        # If there are no items, then assume that it's a glitch.  Otherwise, the
        # next pass will think that all items are new and will open a bunch of
        # browser windows.
        vine_for_all_list = vine_for_all_list2

    br.close()
