import requests
import json
from getpass import getpass

def parse_portfolio(entry):
	""" Given a blob of JSON data that describes a portfolio, return
		a dictionary with the important data. """
	portfolio = {
		'title' : entry['title']['$t'],
		'updated' : entry['updated']['$t'],
		'id' : entry['id']['$t'],
		'etag' : entry['gd$etag'],
		'link' : entry['link'][1]['href'],
		'feedLink' : entry['gd$feedLink']['href'],
		'portfolioData' : {},
		'positions' : {}
	}
	portfolio['portfolioData'].update(entry['gf$portfolioData'])
	for key in portfolio['portfolioData']:
		if key != "currencyCode":
			portfolio['portfolioData'][key] = float(portfolio['portfolioData'][key])
	return portfolio

class FinanceSession():
	def __init__(self, username, password):
		self.Auth = None
		self.service = "finance"
		self.source = "peterldowns-pynance-1.0"
		self.email = username
		self.passwd = password
		self.headers = {
			'GData-Version' : '2',
			'content-type':'application/x-www-form-urlencoded',
		}
		self.portfolios = {}
		#self.positions = {}
		#self.transactions = {}
		
		self.login() # Authenticate to begin the session

	def login(self):
		""" Begin a session and retrieve a GoogleAuth key for later use.
			A user must have this key to perform any other operation. """
		print "Authenticating ..."
		target = "https://www.google.com/accounts/ClientLogin"
		payload = {
			"Email" : self.email,
			"Passwd" : self.passwd,
			"service" : self.service,
			"source" : self.source
		}
		response = requests.post(target, data=payload, headers=self.headers)
		if login_resp.status_code == 200:
			SID, LSID, Auth = map(lambda x:x.split('=')[1], login_resp.content.split('\n')[0:3])
			self.Auth = Auth
			self.headers["Authorization"] = ("GoogleLogin auth="+Auth)
			print "... successful!"
			return True
		else:
			#TODO: raise exception?
			print "... failed. Please retry."
			return False
	
	def get_portfolios(self):
		""" Retrieve a list of all of a user's portfolios. """
		if not self.Auth:
			print "Not authenticated!"
			return False

		target = "https://finance.google.com/finance/feeds/default/portfolios?alt=json"
		response = requests.get(target, headers=self.headers)
		if not response.status_code == 200:
			print "Error! Response status code = {}".format(response.status_code)
			return False
		else:
			resp_data = json.loads(response.content)
			feed = resp_data['feed']
			entries = feed['entry']
			for entry in entries:
				port = parse_portfolio(entry)
				self.portfolios[port['title']] = port
			return True
	
	def show_portfolios(self):
		""" Prints out a list of the user's portfolios """
		if not self.portfolios:
			self.get_portfolios()
		print "Portfolios:"
		print "-----------"
		for p in self.portfolios:
			print_portfolio(p)
		print "-----------"
	
	def create_portfolio(self, title, currencyCode):
		""" Create a new portfolio with a given title and base currency. """
		cc = currencyCode.upper()
		if len(cc) != 3:
			print "Currency code must be 3 characters. You supplied: {}".format(currencyCode)
			print "Portfolio creation failed."
			return False
		if not title: # title=="", title=None
			print "Must supply a title."
			print "Portfolio creation failed."
			return False
		
		pf_entry = "<entry xmlns='http://www.w3.org/2005/Atom' "\
						"xmlns:gf='http://schemas.google.com/finance/2007'> "\
						"<title>{}</title> "\
						"<gf:portfolioData currencyCode='{}'/> "\
					"</entry>".format(title, cc)
		target = "https://finance.google.com/finance/feeds/default/portfolios?alt=json"
		
		_headers = user['headers']
		_headers['content-type'] = 'application/atom+xml' # must change content type; posting XML

		r = requests.post(target, headers=_headers, data=pf_entry)
		if r.status_code != 201:
			print "Unable to create portfolio {} (currency: {})".format(title, cc)
			print "Server returned:", r.content
			return False
		
		resp_data = json.loads(r.content)
		new_portfolio = parse_portfolio(resp_data['entry'])
		self.portfolios[new_portfolio['title']] = new_portfolio
		print "Created new portfolio: {} (currency: {})".format(title, cc)
		#print_portfolio(new_portfolio)
		return True
		



def login(user):
	""" Logs a user in and returns the auth keys """

	login_target = "https://www.google.com/accounts/ClientLogin"
	login_payload = {
		"Email" : user['Email'],
		"Passwd" : user['Passwd'],
		"service" : user['service'],
		"source" : user['source'],
	}
	login_headers = user['headers']
	login_resp = requests.post(login_target, data=login_payload, headers=login_headers)

	if login_resp.status_code == 200:
		SID, LSID, Auth = map(lambda x:x.split('=')[1], login_resp.content.split('\n')[0:3])
		user["Auth"] = Auth
		user["headers"]["Authorization"] = ("GoogleLogin auth="+Auth)
	return user

def make_portfolio(user, title, currencyCode):
	""" Create a new portfolio with a given title and currency. """
	port_str = "<entry xmlns='http://www.w3.org/2005/Atom' "\
					"xmlns:gf='http://schemas.google.com/finance/2007'> "\
		  			"<title>{}</title> "\
		    		"<gf:portfolioData currencyCode='{}'/> "\
				"</entry>"
	port_str = port_str.format(title, currencyCode)
	
	headers = user['headers']
	headers['content-type'] = 'application/atom+xml'

	r = requests.post("https://finance.google.com/finance/feeds/default/portfolios?alt=json", headers=headers, data=port_str)
	if r.status_code != 201:
		print "THERE WAS A SERIOUS ERROR. THIS IS NOT A JOKE. YOUR PORTFOLIO WAS NOT CREATED"
		print "... please take me seriously?"
		return user
	
	resp_data = json.loads(r.content)
	new_portfolio = make_port_from_entry(resp_data['entry'])
	user['portfolios'][new_portfolio['title']] = new_portfolio
	print "Portfolio created."
	print_portfolio(new_portfolio)
	
	return user

def delete_portfolio(user, title):
	""" Delete a portfolio given its title. If the portfolio doesn't exist,
		show an error message and then continue anyway."""
	if title in user['portfolios']:
		r = requests.delete(user['portfolios'][title]['link'], headers=user['headers'])
		if r.status_code == 200:
			print "Successfully deleted portfolio: {}".format(title)
			del user['portfolios'][title]
		else:
			print "Wasn't able to delete '{}' due to some auth/header error, probably. Idk.".format(title)
	else: print "Unable to successfully delete portfolio: {}".format(title)
	return user

def make_port_from_entry(entry):
	"""Given a JSON entry from the google API, create a portfolio object"""

	portData = {
		'title' : entry['title']['$t'],
		'updated' : entry['updated']['$t'],
		'id' : entry['id']['$t'],
		'etag' : entry['gd$etag'],
		'link' : entry['link'][1]['href'],
		'feedLink' : entry['gd$feedLink']['href'],
		'portfolioData' : {},
		'positions' : {}
	}
	portData['portfolioData'].update(entry['gf$portfolioData'])
	for key in portData['portfolioData']:
		if key != "currencyCode":
			portData['portfolioData'][key] = float(portData['portfolioData'][key])
	return portData

def print_portfolio(portData):
	""" Given a portfolio dict, print it out nice and pretty."""
	print "{}:\n  Last Updated: {}\n  Link to feed: {}".format(portData['title'], portData['updated'], portData['link'])
	for k, v in portData['portfolioData'].iteritems():
		print "    {} = {}".format(k, v)

def get_portfolios(user):
	""" Retrieve a list of all of a user's portfolios. Print them out,
		giving short summaries of each, and store this data to the user
		dict that is being passed around this program. """

	reqstr = "https://finance.google.com/finance/feeds/default/portfolios?alt=json"
	if not user or not user['Auth']:
		print "Not authenticated!"
		return
	
	r = requests.get(reqstr, headers=user['headers'])
	resp_data = json.loads(r.content)
	feed = resp_data['feed']
	entries = feed['entry']
	
	for entry in entries:
		#print json.dumps(entry, sort_keys=True, indent=4)
		portData = make_port_from_entry(entry)
		user['portfolios'][portData['title']] = portData
		print_portfolio(portData)
	return user

def make_pos_from_entry(entry):
	""" Given a JSON position entry, create a position dict"""
	posData = {
		'id' : entry['id']['$t'],
		'updated' : entry['updated']['$t'],
		'title' : entry['title']['$t'],
		'link' : entry['link'][0]['href'],
		'feedLink' : entry['gd$feedLink']['href'],
		'symbol' : entry['gf$symbol']['symbol'],
		'exchange': entry['gf$symbol']['exchange'],
		'fullName' : entry['gf$symbol']['fullName'],
		'positionData' : {},
		'transactions' : {}
	}
	posData['positionData'].update(entry['gf$positionData'])
	for key in posData['positionData']:
		posData['positionData'][key] = float(posData['positionData'][key])
	return posData

def print_position(posData):
	""" Given a position, pretty-print it."""
	print "{}:{} - {}".format(posData['exchange'], posData['symbol'], posData['title'])
	print "  Last Updated:", posData['updated']
	print "  Link to feed:", posData['feedLink']
	for k, v in posData['positionData'].iteritems():
		print "    {} = {}".format(k, v)

def view_positions(user, port_title):
	""" Get all of the current positions of a given portfolio"""
	if not port_title in user['portfolios']:
		print "Portfolio '{}' does not exist".format(port_title)
	pos_str = "{}?alt=json".format(user['portfolios'][port_title]['feedLink'])
	r = requests.get(pos_str, headers=user['headers'])
	if r.status_code != 200:
		print "serious error here: r.status_code = {}".format(r.status_code)
		print "This is clearly not working, goodbye"
		return user
	pos_resp = json.loads(r.content)
	feed = pos_resp['feed']
	entries = feed['entry']
	for entry in entries:
		posData = make_pos_from_entry(entry)
		user['portfolios'][port_title]['positions'][posData['title']] = posData
		print_position(posData)
	return user



def session():
	user = {
		"Email" : raw_input("Email > "),
		"Passwd" : getpass("Password > "),
		"service" : "finance",
		"source" : "downsEllisTrainer-autoStock-1.0",
		"Auth" : None,
		"portfolios" : {},
		"headers" : {
			"GData-Version" : "2",
			'content-type':'application/x-www-form-urlencoded',
		}
	}
	print "Attempting to authenticate..."
	user = login(user)
	if not user['Auth']:
		print "... failure."
		return
	else:
		print "... success."
		print "Waiting for commands."
	
	user = get_portfolios(user)
	import time
	p_name = "Testing_"+str(time.time())
	user = make_portfolio(user, p_name, "USD")
	user = delete_portfolio(user, p_name)
	for port_title in user['portfolios'].keys():
		if port_title != "My Portfolio":
			user = delete_portfolio(user, port_title)
	user = get_portfolios(user)
	for port_title in user['portfolios']:
		view_positions(user, port_title)

if __name__=="__main__":
	session()
