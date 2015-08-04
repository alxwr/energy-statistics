#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2, urllib, re
from datetime import datetime
import pytz

base_uri = "http://192.168.8.99/"
password = "SqqRakQ2jVGLQ1ikpWz4"

login_uri = base_uri + 'login.html'
gauge_uri = base_uri + 'energenie.html'

login = dict(pw=password)
data = urllib.urlencode(login)
req = urllib2.Request(login_uri, data)
rsp = urllib2.urlopen(req)

content = urllib2.urlopen(gauge_uri).read()

# Logout
urllib2.urlopen(login_uri).read()

javascript = re.search('<script>(.+)</script>', content).group(1)
voltage = float(re.search('var V.*?=.*?([0-9]+);', javascript).group(1))/10
current = float(re.search('var I.*?=.*?([0-9]+);', javascript).group(1))/100
power = float(re.search('var P.*?=.*?([0-9]+);', javascript).group(1))/466
energy = float(re.search('var E.*?=.*?([0-9]+);', javascript).group(1))/25600

u = datetime.utcnow()
u = u.replace(tzinfo=pytz.utc)
timestamp = u.isoformat()

print("{},{:.2f} V,{:.2f} A,{:.2f} W,{:.2f} kWh".format(timestamp, voltage, current, power, energy))
