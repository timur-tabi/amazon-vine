amazon-vine
===========

This program is a Python script that checks the list of products on your
Amazon Vine queue and notifies you if a new item becomes available.

If you don't know what Amazon Vine is, please read the Wikipedia page:
http://en.wikipedia.org/wiki/Amazon_Vine

Amazon Vine is an invitation-only program, and there nothing you can do
to get an invitation, not even from other Vine members.  I have no idea
why I was invited.

Death By Captcha support
------------------------

Death By Captcha is one of many paid online services that provides automated
image captcha solving.  That is, you upload an captcha image to their
web site, and few seconds later, it tells you what the image says.  Each
image typically costs a couple cents to process.

Sometimes Amazon gets suspicious and thinks that the script is a bot.
It interrupts the login process and displays an image captcha.  Normally,
the script will display the image on the screen and prompt the user to
"solve" the captcha and type in what it says.

Alternatively, the user can subscribe to the Death By Captcha service, and
the script will use that service to automatically solve the captcha,
without user intervention.  This service is a good option for users of
this script because Amazon typically displays an image captcha only a few
times a day (at most), and each image only costs about two cents to process.
A basic Death By Captcha package costs about $7 for 5,000 images.  That is
enough to last for years.

1. Go to http://www.deathbycaptcha.com and create an account
2. Sign up for the cheapest package ($6.95 for 5,000 views as of this
   writing).  If you're unsure, you might be able to get a free trial.
   Be sure to ask for access to the API.  Only paying customers get
   access to the API.
3. Download and unzip the Python package.  In it will be a file called
   deathbycaptcha.py.  Put that file in the same place as amazon-vine.py.
4. The script needs to know your Death By Captcha userid and password.
   You can either set them on the command line with the --dbcu and --dbcp
   parameters, or set the DEATHBYCAPTCHA_USERID and DEATHBYCAPTCHA_PASSWORD
   environment variables.
5. Start the script.  If/when the Amazon web site prompts an image captcha,
   the script should use the Death By Captcha service transparently.

NOTE: I make no guarantees that this script will work at all with the
Death By Captcha service.  Anything could change at any time, and you
assume all responsibility.  If the script goes haywire, it might
repeatedly use the Death By Captcha service and use up all your funds.
Or the service could change, and the only way to make it work is to
modify this script, and I don't guarantee that I will continue to support
Death By Captcha under any circumstances.