#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2, urllib, re, argparse, sys, platform, os
from datetime import datetime
import pytz
from email.mime.text import MIMEText
from subprocess import Popen, PIPE
from urlparse import urljoin

class EnergyStatisticsPoller:
	def __init__(self, site, password, log_dir, cache_dir):
		self.site = site
		self.password = password
		self.log_dir = log_dir
		self.cache_dir = cache_dir
		# Internal variables
		self.stored_values = None

	def get_content(self):
		login_uri = urljoin(self.site, '/login.html')
		gauge_uri = urljoin(self.site, '/energenie.html')

		login = dict(pw=self.password)
		data = urllib.urlencode(login)
		req = urllib2.Request(login_uri, data)
		rsp = urllib2.urlopen(req)

		content = urllib2.urlopen(gauge_uri).read()

		# Logout
		urllib2.urlopen(login_uri).read()

		return content

	def extract_values(self, content=None):
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

	def iso8601_utc_timestamp(self):
		u = datetime.utcnow()
		u = u.replace(tzinfo=pytz.utc)
		return u.isoformat()

	def logline(self, values):
		return "{},{:.2f} V,{:.2f} A,{:.2f} W,{:.2f} kWh\n".format(
			self.iso8601_utc_timestamp(),
			values['voltage'],
			values['current'],
			values['power'],
			values['energy']
		)

	def write_to_log(self, values=None):
		if values == None:
			values = self.values()
		with open(os.path.join(self.log_dir, "poller.log"), "a") as file:
			file.write(self.logline(values))

	def values(self, fresh=False):
		if self.stored_values == None or fresh == True:
			self.stored_values = self.extract_values(self.get_content())
		return self.stored_values

	def get_energy_diff(self):
		path = os.path.join(self.cache_dir, 'last_energy.txt')
		open(path, 'a').close  # touch
		since = datetime.fromtimestamp(int(os.path.getmtime(path)), pytz.utc).isoformat()
		with open(path, 'r+') as file:
			c = file.read()
			if c == '':
				last = 0.0
			else:
				last = float(c)
			file.seek(0)
			file.truncate(0)
			file.write("{}".format(self.values()['energy']))
		return dict(
			amount=(self.values()['energy'] - last),
			since=since
		)

class MyParser(argparse.ArgumentParser):
	def error(self, message):
		if len(sys.argv)==1:
			parser.print_help()
			sys.exit(1)
		sys.stderr.write('error: %s\n' % message)
		self.print_help()
		sys.exit(2)

def sendmail(subject, content, sender, receiver):
	msg = MIMEText(content)
	msg["From"] = sender
	msg["To"] = receiver
	msg["Subject"] = subject
	p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
	p.communicate(msg.as_string())

if __name__ == "__main__":

	parser = MyParser(prog="energy-statistics",
		description="Parse the values of Gembird's LAN Energy Meter")
	parser.add_argument('site', help="HTTP URI of the site to query.")
	parser.add_argument('--password', default='1', help="Default: 1")
	sender = "gauge@{}".format(platform.node())
	parser.add_argument('--sender', default='1', help="Default: {}".format(sender))
	parser.add_argument('--receiver', required=True, help="Email receiver.")
	logdir = "/var/log/energy-statistics"
	parser.add_argument('--log-dir', default=logdir, help="Default: {}".format(logdir))
	cachedir = "/var/spool/energy-statistics"
	parser.add_argument('--cache-dir', default=cachedir, help="Default: {}".format(cachedir))

	# Additional actions
	parser.add_argument('--energy-diff', help="Consumed energy since the last diff.", action='store_true')

	# TODO: Warn on energy rotation

	args = parser.parse_args()

	# Poll device and write to log
	e = EnergyStatisticsPoller(
		site = args.site,
		password = args.password,
		log_dir = args.log_dir,
		cache_dir = args.cache_dir
	)
	e.values()
	e.write_to_log()

	if args.energy_diff:
		diff = e.get_energy_diff()
		sendmail(
			"Energy consumption",
			"Energy consumption between {} and {}\nwas {:.4f} kWh".format(
				diff['since'],
				e.iso8601_utc_timestamp(),
				diff['amount']),
			sender,
			args.receiver)

