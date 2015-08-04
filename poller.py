#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2, urllib, re, argparse, sys, platform
from datetime import datetime
import pytz
from email.mime.text import MIMEText
from subprocess import Popen, PIPE
from urlparse import urljoin

def get_content(site, password):
	login_uri = urljoin(site, '/login.html')
	gauge_uri = urljoin(site, '/energenie.html')

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
	return "{},{:.2f} V,{:.2f} A,{:.2f} W,{:.2f} kWh\n".format(
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

def write_to_log(values, logdir):
	with open(logdir+"poller.log", "a") as file:
		file.write(logline(values))

class MyParser(argparse.ArgumentParser):
	def error(self, message):
		if len(sys.argv)==1:
			parser.print_help()
			sys.exit(1)
		sys.stderr.write('error: %s\n' % message)
		self.print_help()
		sys.exit(2)

if __name__ == "__main__":

	#sendmail("energy", "{:.2f}".format(values['energy']), sender, receiver)

	parser = MyParser(prog="energy-statistics",
		description="Parse the values of Gembird's LAN Energy Meter")
	parser.add_argument('site', help="HTTP URI of the site to query.")
	parser.add_argument('--password', default='1', help="Default: 1")
	sender = "gauge@{}".format(platform.node())
	parser.add_argument('--sender', default='1', help="Default: {}".format(sender))
	parser.add_argument('--receiver', help="Email receiver.")
	logdir = "/var/log/energy-statistics/"
	parser.add_argument('--log-dir', default=logdir, help="Default: {}".format(logdir))

	# Additional actions
	# TODO
	parser.add_argument('--diff-energy', help="Consumed energy since the last diff.")

	# TODO: Warn on energy rotation

	args = parser.parse_args()

	# Poll device and write to log
	values = extract_values(get_content(args.site, args.password))
	write_to_log(values, args.log_dir)
