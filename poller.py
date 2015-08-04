#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2, urllib, re
from datetime import datetime
import pytz
from email.mime.text import MIMEText
from subprocess import Popen, PIPE

def get_content(base_uri, password):
	login_uri = base_uri + 'login.html'
	gauge_uri = base_uri + 'energenie.html'

	login = dict(pw=password)
	data = urllib.urlencode(login)
	req = urllib2.Request(login_uri, data)
	rsp = urllib2.urlopen(req)

	content = urllib2.urlopen(gauge_uri).read()

	# Logout
	urllib2.urlopen(login_uri).read()

	return content

def extract_values(content):
	javascript = re.search('<script>(.+)</script>', content).group(1)
	voltage = float(re.search('var V.*?=.*?([0-9]+);', javascript).group(1))/10
	current = float(re.search('var I.*?=.*?([0-9]+);', javascript).group(1))/100
	power = float(re.search('var P.*?=.*?([0-9]+);', javascript).group(1))/466
	energy = float(re.search('var E.*?=.*?([0-9]+);', javascript).group(1))/25600
	return dict(
		voltage=voltage,
		current=current,
		power=power,
		energy=energy
	)

def iso8601_utc_timestamp():
	u = datetime.utcnow()
	u = u.replace(tzinfo=pytz.utc)
	return u.isoformat()

def logline(values):
	return "{},{:.2f} V,{:.2f} A,{:.2f} W,{:.2f} kWh".format(
		iso8601_utc_timestamp(),
		values['voltage'],
		values['current'],
		values['power'],
		values['energy']
	)

def sendmail(subject, content, sender, receiver):
	msg = MIMEText(content)
	msg["From"] = sender
	msg["To"] = receiver
	msg["Subject"] = subject
	p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
	p.communicate(msg.as_string())

if __name__ == "__main__":
	base_uri = "http://192.168.8.99/"
	password = "SqqRakQ2jVGLQ1ikpWz4"
	sender = "gauge@ausguck.srv.local"
	receiver = "aw@sz9i.net"

	values = extract_values(get_content(base_uri, password))
	print(logline(values))
	print(values['energy'])
	sendmail("energy", "{:.2f}".format(values['energy']), sender, receiver)
