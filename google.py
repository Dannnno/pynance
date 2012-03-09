import requests
import json
from getpass import getpass

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
		'portfolioData' : {}
	}
	portData['portfolioData'].update(entry['gf$portfolioData'])
	for key in portData['portfolioData']:
		if key != "currencyCode":
			portData['portfolioData'][key] = float(portData['portfolioData'][key])
	return portData

def print_portfolio(portData):
	print "{}:\n  Last Updated: {}\n  Link to feed: {}".format(portData['title'], portData['updated'], portData['link'])
	for k, v in portData['portfolioData'].iteritems():
		print "    {}  = {}".format(k, v)

def get_portfolios(user):
	reqstr = "https://finance.google.com/finance/feeds/default/portfolios?alt=json"
	if not user or not user['Auth']:
		print "Not authenticated!"
		return
	r = requests.get(reqstr, headers=user['headers'])
	print "Status code: %d" % r.status_code
	resp_data = json.loads(r.content)
	feed = resp_data['feed']
	entries = feed['entry']
	for entry in entries:
		#print json.dumps(entry, sort_keys=True, indent=4)
		portData = make_port_from_entry(entry)
		user['portfolios'][portData['title']] = portData
		print_portfolio(portData)
	return user

def session():
	user = {
		"Email" : raw_input("Email > "),
		"Passwd" : getpass("Password > "),
		"service" : "finance",
		"source" : "downsEllis-autoStock-1.0",
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

if __name__=="__main__":
	session()
