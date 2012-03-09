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

def get_portfolios(__user):
	reqstr = "https://finance.google.com/finance/feeds/default/portfolios?alt=json"
	if not __user:
		print "Not authenticated!"
	r = requests.get(reqstr, headers=__user['headers'])
	print "Status code: %d" % r.status_code
	resp_data = json.loads(r.content)
	feed = resp_data['feed']
	entries = feed['entry']
	for entry in entries:
		feedData = {
			'title' : entry['title']['$t'],
			'etag' : entry['gd$etag'],
			'link' : entry['link'][1]['href'],
			'feedLink' : entry['gd$feedLink']['href'],
			'portfolioData' : {}
		}
		feedData['portfolioData'].update(entry['gf$portfolioData'])
		for key in feedData['portfolioData']:
			if key != "currencyCode":
				feedData['portfolioData'][key] = float(feedData['portfolioData'][key])
		print feedData


def session():
	""" Starts an interactive sesion """
	__COMS = {
		"show_all_ports" : get_portfolios
	}
	user = {
		"Email" : raw_input("Email > "),
		"Passwd" : getpass("Password > "),
		"service" : "finance",
		"source" : "downsEllis-autoStock-1.0",
		"Auth" : None,
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
	
	get_portfolios(user)

	while 0:
		user_input = raw_input("> ")
		print "received \"{}\"".format(user_input)

		comargs = user_input.split(' ', 1)
		if len(comargs) > 1:
			com, args = comargs
		else:
			com, args = comargs[0], None
		
		if args:
			args = args.split(' ')

		for name, func in __COMS.iteritems():
			if com.lower().strip() == name.lower().strip():
				func(args, __user=user)
		if com == 'q':
			print "Done."
			break

if __name__=="__main__":
	session()
