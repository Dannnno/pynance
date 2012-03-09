'''
Created on July 31, 2011

@author: ppa
'''
import urllib2
from BeautifulSoup import BeautifulSoup
import traceback
from operator import itemgetter
from ultrafinance.lib.util import convertGoogCSVDate, findPatthen
from ultrafinance.model import Quote, Tick
from ultrafinance.lib.errors import UfException, Errors
import copy
from ultrafinance.lib.util import string2EpochTime

import re
import logging
LOG = logging.getLogger()

class GoogleFinance(object):
    def __request(self, url):
        try:
            return urllib2.urlopen(url)
        except IOError:
            raise UfException(Errors.NETWORK_ERROR, "Can't connect to Google server at %s" % url)
        except urllib2.HTTPError:
            raise UfException(Errors.NETWORK_400_ERROR, "400 error when connect to Google server")
        except Exception:
            raise UfException(Errors.UNKNOWN_ERROR, "Unknown Error in GoogleFinance.__request %s" % traceback.format_exc())

    def getAll(self, symbol):
        """
        Get all available quote data for the given ticker symbol.
        Returns a dictionary.
        """
        url = 'http://www.google.com/finance?q=%s' % symbol
        page = self.__request(url)

        soup = BeautifulSoup(page)
        snapData = soup.find("table", { "class" : "snap-data" })
        if snapData is None:
            raise UfException(Errors.STOCK_SYMBOL_ERROR, "Can find data for stock %s, symbol error?" % symbol)
        data = {}
        for row in snapData.findAll('tr'):
            keyTd, valTd = row.findAll('td')
            data[keyTd.getText()] = valTd.getText()

        return data

    def getQuotes(self, symbol, start, end):
        """
        Get historical prices for the given ticker symbol.
        Date format is 'YYYYMMDD'

        Returns a nested list.
        """
        try:
            url = 'http://www.google.com/finance/historical?q=%s&startdate=%s&enddate=%s&output=csv' % (symbol, start, end)
            try:
                page = self.__request(url)
            except UfException as ufExcep:
                ##if symol is not right, will get 400
                if Errors.NETWORK_400_ERROR == ufExcep.getCode:
                    raise UfException(Errors.STOCK_SYMBOL_ERROR, "Can find data for stock %s, symbol error?" % symbol)
                raise ufExcep

            days = page.readlines()
            values = [day.split(',') for day in days]
            # sample values:[['Date', 'Open', 'High', 'Low', 'Close', 'Volume'], \
            #              ['2009-12-31', '112.77', '112.80', '111.39', '111.44', '90637900']...]
            data = []
            for value in values[1:]:
                date = convertGoogCSVDate(value[0])
                data.append(Quote(date,
                                  value[1].strip(),
                                  value[2].strip(),
                                  value[3].strip(),
                                  value[4].strip(),
                                  value[5].strip(),
                                  None))

            #dateValues = sorted(data, key=itemgetter(0))
            dateValues = sorted(data, key = lambda x: x.time)
            return dateValues

        except BaseException:
            raise UfException(Errors.UNKNOWN_ERROR, "Unknown Error in GoogleFinance.getHistoricalPrices %s" % traceback.format_exc())
        #sample output
        #[stockDaylyData(date='2010-01-04, open='112.37', high='113.39', low='111.51', close='113.33', volume='118944600', adjClose=None))...]

    def getFinancials(self, symbol, fields = ['Total Revenue'], annual = True):
        """
        get financials:
        google finance provide annual and quanter financials, if annual is true, we will use annual data
        Up to four lastest year/quanter data will be provided by google
        Refer to page as an example: http://www.google.com/finance?q=TSE:CVG&fstype=ii
        """
        try:
            url = 'http://www.google.com/finance?q=%s&fstype=ii' % symbol
            try:
                page = self.__request(url).read()
            except UfException as ufExcep:
                ##if symol is not right, will get 400
                if Errors.NETWORK_400_ERROR == ufExcep.getCode:
                    raise UfException(Errors.STOCK_SYMBOL_ERROR, "Can find data for stock %s, symbol error?" % symbol)
                raise ufExcep

            timeInterval = 'annual' if annual else 'interim'
            valueNum = 4 if annual else 5

            fieldValues = {}
            for field in fields:
                cPage = copy.copy(page)
                fieldContents = findPatthen(cPage, [('id', re.compile(r"(\w+)%s(\w+)" % timeInterval)), ('id', 'fs-table'), ('text', re.compile(r"^%s$" % field))])

                if 1 != len(fieldContents):
                    #raise ufException(Errors.STOCK_PARSING_ERROR, "Parse data error for symbol %s" % symbol)
                    fieldValues[field] = []
                    continue

                value = fieldContents[0]
                data = []

                for _ in range(valueNum):
                    value = value.findNext('td')
                    data.append(value.getText().replace(',', ''))

                fieldValues[field] = data

            return fieldValues
        except BaseException:
            raise UfException(Errors.UNKNOWN_ERROR, "Unknown Error in GoogleFinance.getHistoricalPrices %s" % traceback.format_exc())


    def getTicks(self, symbol, start, end):
        """
        Get tick prices for the given ticker symbol.
        @symbol: stock symbol
        @interval: interval in mins(google finance only support query till 1 min)
        @start: start date(YYYYMMDD)
        @end: end date(YYYYMMDD)

        start and end is disabled since only 15 days data will show

        @Returns a nested list.
        """
        #TODO, parameter checking
        try:
            #start = string2EpochTime(start)
            #end = string2EpochTime(end)
            #period = end - start
            period = 15
            #url = 'http://www.google.com/finance/getprices?q=%s&i=%s&p=%sd&f=d,o,h,l,c,v&ts=%s' % (symbol, interval, period, start)
            url = 'http://www.google.com/finance/getprices?q=%s&i=61&p=%sd&f=d,o,h,l,c,v' % (symbol, period)
            try:
                page = self.__request(url)
            except UfException as ufExcep:
                ##if symol is not right, will get 400
                if Errors.NETWORK_400_ERROR == ufExcep.getCode:
                    raise UfException(Errors.STOCK_SYMBOL_ERROR, "Can find data for stock %s, symbol error?" % symbol)
                raise ufExcep

            days = page.readlines()[7:] # first 7 line is document
            # sample values:'a1316784600,31.41,31.5,31.4,31.43,150911'
            values = [day.split(',') for day in days]

            data = []
            for value in values:
                data.append(Tick(value[0][1:].strip(),
                                 value[4].strip(),
                                 value[2].strip(),
                                 value[3].strip(),
                                 value[1].strip(),
                                 value[5].strip()))

            return data

        except BaseException:
            raise UfException(Errors.UNKNOWN_ERROR, "Unknown Error in GoogleFinance.getTicks %s" % traceback.format_exc())
        #sample output
        #[stockDaylyData(date='1316784600', open='112.37', high='113.39', low='111.51', close='113.33', volume='118944600', adjClose=None))...]
