import requests
import json
from getpass import getpass

def parse_portfolio(entry):
	""" Given a blob of JSON data (as a dict) that describes a portfolio,
		return a dictionary with the important data. """
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
	#print json.dumps(portfolio, sort_keys=True, indent=4)
	return portfolio
def print_portfolio(portData):
	""" Given a portfolio dict, print it out nice and pretty."""
	#print json.dumps(portData, sort_keys=True, indent=4)
	print "{}:\n  Last Updated: {}\n  Link to feed: {}".format(portData['title'], portData['updated'], portData['link'])
	for k, v in portData['portfolioData'].iteritems():
		print "    {} = {}".format(k, v)

def parse_position(entry):
	""" Given a blob of JSON data (as a dict) that descibres a position,
		return a dictionary with the important data. """
	position = {
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
	position['positionData'].update(entry['gf$positionData'])
	for key in position['positionData']:
		position['positionData'][key] = float(position['positionData'][key])
	return position
def print_position(posData):
	""" Given a position, pretty-print it."""
	print "{}:{} - {}".format(posData['exchange'], posData['symbol'], posData['title'])
	print "  Last Updated:", posData['updated']
	print "  Link to feed:", posData['feedLink']
	for k, v in posData['positionData'].iteritems():
		print "    {} = {}".format(k, v)


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
		if response.status_code == 200:
			SID, LSID, Auth = map(lambda x:x.split('=')[1], response.content.split('\n')[0:3])
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
		for title, port in self.portfolios.iteritems():
			print_portfolio(port)
		print "-----------"
	
	def create_portfolio(self, title, currencyCode):
		""" Create a new portfolio with a given title and base currency. """
		if not self.Auth:
			print "Not authenticated!"
			return False

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
		
		_headers = self.headers
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
	
	def delete_portfolio(self, title):
		""" If a portfolio with the given title currently exists: delete it. """
		if not self.Auth:
			print "Not authenticated!"
			return False

		if title in self.portfolios:
			r = requests.delete(self.portfolios[title]['link'], headers=self.headers)
			if r.status_code == 200:
				print "Successfully deleted portfolio: '{}'".format(title)
				del self.portfolios[title]
				return True
			else:
				print "Unable to delete portfolio '{}' due to a request or server error.".format(title)
				print "Status code: {}\nServer resp: {}".format(r.status_code, r.content)
		else:
			print "Portfolio '{}' does not exist.".format(title)
			print "Deletion failed."
		return False

	def get_positions(self, port_title):
		""" Get all of the current positions of a given portfolio. """
		if not self.Auth:
			print "Not authenticated!"
			return False

		if port_title in self.portfolios:
			pf = self.portfolios[port_title]
			target = "{}?alt=json".format(pf['feedLink'])
			r = requests.get(target, headers=self.headers)
			if r.status_code == 200:
				pos_resp = json.loads(r.content)
				feed = pos_resp['feed']
				entries = feed['entry']
				for entry in entries:
					position = parse_position(entry)
					pf['positions'][position['title']] = position
					self.portfolios[port_title] = pf # unnecessary? not sure if pf is a reference or copy
				#TODO: print success?
				return True
			else:
				print "Unable to fetch positions for portfolio '{}'".format(port_title)
				print "Status code: {}\nServer resp: {}".format(r.status_code, r.content)
		else:
			print "Portfolio '{}' does not exist.".format(title)
			print "Unable to fetch positions for nonexistent portfolio"
		return False
	
	def show_positions(self, port_title):
		""" For a given portfolio, show all of the positions held within it. """
		if not self.portfolios[port_title]:
			print "Portfolio '{}' does not exist.".format(port_title)
			return False
		if not self.portfolios[port_title]['positions']:
			self.get_positions(port_title)
		
		print "Portfolio: {}".format(port_title)
		print "Positions:"
		print "-----------"
		for title, pos in self.portfolios[port_title]['positions'].iteritems():
			print_position(pos)
		print "-----------"

def test_session():
	fs = FinanceSession(raw_input("Email: "), getpass("Password: "))
	fs.get_portfolios()
	fs.show_portfolios()
	import time
	p_name = "Testing (FS) "+str(time.time())
	fs.create_portfolio(p_name, "USD")
	fs.show_portfolios()
	fs.delete_portfolio(p_name)
	for pf in fs.portfolios:
		fs.show_positions(pf)
	
	print "................"
	print "Done."

if __name__=="__main__":
	test_session()
