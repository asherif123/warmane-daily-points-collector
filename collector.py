# -*- coding: utf-8 -*-
import requests
import sys
import os
import ConfigParser
from bs4 import BeautifulSoup
from functools import wraps

def exit_program():
	"""Waits for the user to press enter then exits."""
	raw_input("Press Enter to exit.")
	sys.exit()

def resource_path(resource):
	"""
	Returns absolute path of resource. Used to get the abs path of
	SSL-certification 'cacert.pem' after the application have been
	compiled to one-file .exe including the cacert.pem.
	"""
	return os.path.join(
		os.environ.get("_MEIPASS2", os.path.abspath(".")), resource)

def get_pass():
	"""
	Gets user password without showing the entered characters.
	Shows ***** instead.
	"""
	import msvcrt
	#Comma after print to avoid new line.
	print("Password: "),
	password = ''
	while 1:
		x = msvcrt.getch()
		#If input is enter.
		if x == '\r' or x == '\n':
			break
		#If input is backspace.
		elif x == '\x08':
			#Only delete from the password string, not the prompt message.
			if len(password) > 0:
				password = password[:-1]
				sys.stdout.write('\x08 \x08')
		else:
			sys.stdout.write('*')
			password = password + x
	msvcrt.putch('\n')
	return password
	
def config_set():
	"""
	Asks user to input:
	1)Number of accounts
	2)All accounts usernames + passwords.
	And, creates a configuration file
	to save this data for later usage.
	"""
	n_accounts = input('Number of accounts: ')
	
	#Create configuration file	to write to it.
	config_file = open(os.getcwd() + '\\collector-config.ini', 'w')
	for i in range(0, n_accounts):
		username = raw_input('\nUsername(%d): ' % (i+1))
		password = get_pass()
		
		#Add the settings to the file, and write it out.
		#Create a new section for each Account.
		section = 'Account%d' % (i+1)
		config.add_section(section)
		config.set(section, 'Username', username)
		config.set(section, 'Password', password)
	
	#Create a new section for program configuration.
	config.add_section('Program Configuration')
	config.set('Program Configuration','Number of Accounts',n_accounts)

	config.write(config_file)
	config_file.close()
	
def get_n_accounts():
	"""Returns the number of accounts from the configuration file."""
	config.read(os.getcwd() + '\\collector-config.ini')
	n_accounts = config.getint('Program Configuration', 'Number of Accounts')
	return n_accounts
	
def get_account_info(n_accounts):
	"""
	Generator function, iterates over the configuration file and 
	returns (username, password) in each iteration.
	"""
	for i in range(n_accounts):
		section = 'Account%d' % (i+1)
		username = config.get(section, 'Username')
		password = config.get(section, 'Password')
		yield username, password
		
def my_decorator(function):
	@wraps(function)
	def wrapper(*args):
		"""Places a try and catch at every get or post request."""
		try:
			response = function(*args)
		except requests.exceptions.ConnectionError:
			print '[Error]: There is no internet connection.'
			exit_program()
		else:
			return response
	return wrapper
	
@my_decorator
def get(url):
	"""Gets the given URL."""
	return s.get(url, headers=custom_headers, verify=ssl_cert)
		
@my_decorator
def post(url, payload):
	"""Posts the payload to the given URL."""
	return s.post(url, data=payload, headers=custom_headers, verify=ssl_cert)		

def init_cookies():
	"""Gets login page, to initialize cookies."""
	response = get('https://www.warmane.com/account/login')
	return response
	
def find_csrf_token(response):
	"""
	Finds the CSRF-Token. Warmane provides it in its website code,
	usually in the second meta tag. CSRF-Token should be included in
	the header, its a security feature that Warmane uses to prevent
	cross site scripting.
	"""
	soup = BeautifulSoup(response.text, 'lxml')
	metas = soup.find_all('meta')
	for meta in metas:
		if 'csrf-token' in meta.prettify():
			#Add CSRF-Token value to custom_headers.
			custom_headers['X-CSRF-Token'] = meta['content']
			break

def login(username, password):
	"""
	Logs in account by posting the payload to the
	login_url and returns the account page if succeeded.
	"""
	#Login Form Data
	payload = {	'return': '',
				'userID': username,
				'userPW': password,
				'userCode': '',
				'userRM': 'False'}
				
	print"\n[Log In]: Username = %s" % username
	response = post('https://www.warmane.com/account/login', payload)
	
	if response.text == '{"redirect":["\/account"]}':
		print'[Log In]: Logged in Successfully!'
		return True
	
	#Warmane is expecting a captcha code!
	elif "The captcha code provided is incorrect." in response.text:
		msg = (
			'[Log In]: Warmane is expecting a captcha code!'
			' So you have to manually login from the browser to enter it.')
		print msg
		
	elif "Incorrect account name or password." in response.text:
		print"[Log In]: Incorrect username or password."
	return False

def collect_points():
	"""Collects daily points. By posting a payload to the account_url."""
	payload = {'collectpoints': 'true'}
	response = post('https://www.warmane.com/account', payload)
	points = find_points()
	
	'''All the possible responses'''
	#'{"messages":{"error":["You have not logged in-game today."]}}'
	#'{"messages":{"error":["You do not have any points to collect."]}}'
	#'{"messages":{"success":["Daily points collected."]},"points":[26.2]}'
	#'{"messages":{"error":["You have already collected your points today."]}}'
	
	if "You have not logged in-game today." in response.text:
		msg = (
			"[Collect Points]: You have not logged in-game today."
			" Points: %s" % points)

	#If account does not have the minimum achievement points.
	elif "You do not have any points to collect." in response.text:
		msg = (
			"[Collect Points]: You must have a character with at least"
			" 1,000 achievement points to be eligible for points."
			" Points: %s" % points)

	elif "Daily points collected." in response.text:
		msg = (
			"[Collect Points]: Daily points collected. Points: %s" % points)

	elif "You have already collected your points today." in response.text:
		msg = (
			"[Collect Points]: You've already collected your points today."
			" Points: %s" % points)
	print msg
	
def find_points():
	"""
	Returns points value from the account page,
	response must be of the account_url page.
	"""
	response = get('https://www.warmane.com/account')
	soup = BeautifulSoup(response.text, 'lxml')
	
	#The line containing the points value
	points = soup.find_all('span', class_='myPoints')
	
	#This is the points value.
	points = str(points[0].string)
	return points
	
def logout():
	"""Logs out! :)"""
	response = get('https://www.warmane.com/account/logout')
	if response.url == 'https://www.warmane.com/':
		print'[Log Out]: Logged out.'

custom_headers = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebK it/537.36 \
	(KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36',
	'Referer': 'http://www.warmane.com/account/login'
	}
	
#ssl_cert is the path to the cacert.pem file which contains all
#trusted certificates used for secure https connection.
ssl_cert = resource_path('cacert.pem')

#Check if configuration file exists. If it exists, read it
#and start logging-in and collecting points. Otherwise,
#create a new configuration file.
config = ConfigParser.ConfigParser()

#If configuration file does not exist, create a new one.
if not os.path.isfile(os.getcwd() + '\\collector-config.ini'):
	config_set()
	
#Get the number of accounts from the configuration file.
n_accounts = get_n_accounts()

#Initialize the accounts generator.
account_generator = get_account_info(n_accounts)

for i in range(n_accounts):
	with requests.Session() as s:
		#account_generator will yield the next username and password.
		username, password = next(account_generator)
		response = init_cookies()
		find_csrf_token(response)
		status = login(username, password)
		
		#If Logged-in successfully.
		if status:
			collect_points()
			logout()
			
exit_program()
