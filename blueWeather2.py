# -*- encoding: utf-8 -*-
####################################################################################################
####################################################################################################
#                                                                                                  #
#    Weatherconverter for VU+                                                                      #
#    Coded by tsiegel (c) 2019                                                                     #
#    THX NaseDC, schomi, Nathanael2316, gordon55, Maggy                                            #
#    Support: www.vuplus-support.com                                                               #
#                                                                  	                           #
#    This converter is licensed under the Creative Commons                                         #
#    Attribution-NonCommercial-ShareAlike 3.0 Unported License.                                    #
#    To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/       #
#    or send a letter to Creative Commons, 559 Nathan Abbott Way, Stanford, California 94305, USA. #
#                                                                                                  #
#    This plugin is NOT free software. It is open source, you are allowed to                       #
#    modify it (if you keep the license), but it may not be commercially                           #
#    distributed other than under the conditions noted above.                                      #
#                                                                                                  #
#...........................................R27....................................................#
####################################################################################################
####################################################################################################
from __future__ import absolute_import, division
from __future__ import print_function
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Components.Language import language
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll
from Components.config import config, ConfigSelection, ConfigText, ConfigClock, ConfigDateTime, getConfigListEntry, ConfigInteger, configfile, fileExists
from Screens.MessageBox import MessageBox
from Tools import Notifications
from twisted.web.client import getPage
from operator import itemgetter
from enigma import eTimer
from time import time, localtime, mktime, strftime, sleep, strptime
from datetime import timedelta, datetime
from math import pi, cos
import datetime
import json
import os
from os import remove, path
import gettext
import re
import string
import stat

from six.moves.urllib.request import Request, urlopen
from six.moves.urllib.error import URLError, HTTPError
from six.moves.urllib.parse import quote
import six

PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, 'Extensions/MyBlueMetal')
PluginLanguageDomain = 'MyBlueMetal'

def localeInit():
	gettext.bindtextdomain(PluginLanguageDomain, PLUGIN_PATH + '/locale')

def _(txt):
	if gettext.dgettext(PluginLanguageDomain, txt):
		return gettext.dgettext(PluginLanguageDomain, txt)
	else:
		return gettext.gettext(txt)

language.addCallback(localeInit())

weather_data = None
wdays = [_('Sunday'), _('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday')]
swdays = [_('Sun'), _('Mon'), _('Tue') ,_('Wed'), _('Thu'), _('Fri'), _('Sat')]
refreshInterval = 60
dsunits = 'si'
astro_Sunrise = None
countrycode = config.plugins.blueMetal.CountryCode.value

log = True
numbers = '.' + str(config.plugins.blueMetal.numbers.value) + 'f'

if config.plugins.blueMetal.weather_place.value == '1':
	lat = config.plugins.blueMetal.Darksky_lat1.value
	lon = config.plugins.blueMetal.Darksky_lon1.value
	city = config.plugins.blueMetal.namecity1.value
	location = config.plugins.blueMetal.OpenWeathermap_idcity1.value
if config.plugins.blueMetal.weather_place.value == '2':
	lat = config.plugins.blueMetal.Darksky_lat2.value
	lon = config.plugins.blueMetal.Darksky_lon2.value
	city = config.plugins.blueMetal.namecity2.value
	location = config.plugins.blueMetal.OpenWeathermap_idcity2.value
if config.plugins.blueMetal.weather_place.value == '3':
	lat = config.plugins.blueMetal.Darksky_lat3.value
	lon = config.plugins.blueMetal.Darksky_lon3.value
	city = config.plugins.blueMetal.namecity3.value
	location = config.plugins.blueMetal.OpenWeathermap_idcity3.value

def write_log(svalue):
	if log:
		t = localtime()
		logtime = '%02d:%02d:%02d' % (t.tm_hour, t.tm_min, t.tm_sec)
		blueMetal_log = open('/tmp/blueMetal.log', "a")
		blueMetal_log.write(str(logtime) + " - " + str(svalue) + "\n")
		blueMetal_log.close()


class blueWeather2(Poll, Converter, object):
	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)
		global weather_data
		if weather_data == None:
			weather_data = WeatherData()
		self.type = type
		self.poll_interval = 600000
		self.poll_enabled = True


	@cached
	def getText(self):
		WeatherInfo = weather_data.WeatherInfo
		try:
			if str(self.type) in WeatherInfo:
				return WeatherInfo[self.type]
			else:
				return " "
		except Exception as ex:
			write_log(_('Error in WeatherInfo : ') + str(ex))
			return " "

	text = property(getText)


	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)


class WeatherData:
	def __init__(self):
		self.WeatherInfo = WeatherInfo = { 
			'W-Info': ' ',
			'W-Info-h': ' ',
			'timezone': _('N/A'),
			'alerts': _('N/A'),
			'windChill': _('N/A'),
			'windDirection': _('N/A'),
			'atmoHumidity': _('N/A'),
			'dewPoint': _('N/A'),
			"atmoVisibility": _('N/A'),
			"astroSunrise": _('N/A'),
			"astroSunset": _('N/A'),
			'astroDaySoltice': _('N/A'),
			'astroDayLength': _('N/A'),
			'uvIndex': _('N/A'),
			"geoData": _('N/A'),
			"geoLat": _('N/A'),
			"geoLong": _('N/A'),
			"downloadDate": _('N/A'),
			"downloadTime": _('N/A'),

			'currentCity': ' ',

			'currentCountry': _('N/A'),
			'currentWeatherCode': "(",
			'currentPressure': _('N/A'),
			'currentlywindSpeed': _('N/A'),
			'currentlywindGust': _('N/A'),
			'currentLocation': _('N/A'),
			"currentRegion": _('N/A'),
			"currentWeatherText": _('N/A'),
			"currentWeatherTemp": "0",
			"currentWeatherPicon": "3200",
			'currentProbability': _('N/A'),
			'currentPrecip': _('N/A'),
			'currentlyIntensity': _('N/A'),
			'currentOzoneText': _('N/A'),
			'currentcloudCover': '0',

			"currentMoonPicon": "3200",
			"currentMoonPhase": "N/A",

			'forecastTodayPressure': _('N/A'),
			"forecastTodayCode": "(",
			"forecastTodayDay": _('N/A'),
			"forecastTodayDate": _('N/A'),
			"forecastTodayTempMin": "0",
			"forecastTodayTempMax": "0",
			"forecastTodayText": _('N/A'),
			"forecastTodayPicon": "3200",
			'forecastTodaywindSpeed': _('N/A'),
			'forecastTodaywindGust': _('N/A'),
			'forecastTodaymoonPhase': _('N/A'),
			'forecastTodayProbability': _('N/A'),
			'forecastTodayIntensity': _('N/A'),
			'forecastTodaycloudCover': '0',
			'forecastTodayHumidity': _('N/A'),

			'forecastTomorrowPressure': _('N/A'),
			"forecastTomorrowCode": "(",
			"forecastTomorrowDay": _('N/A'),
			"forecastTomorrowDate": _('N/A'),
			"forecastTomorrowTempMin": "0",
			"forecastTomorrowTempMax": "0",
			"forecastTomorrowText": _('N/A'),
			"forecastTomorrowPicon": "3200",
			'forecastTomorrowwindSpeed': _('N/A'),
			'forecastTomorrowwindGust': _('N/A'),
			"forecastTomorrowProbability": _('N/A'),
			'forecastTomorrowIntensity': _('N/A'),
			'forecastTomorrowcloudCover': '0',
			'forecastTomorrowHumidity': _('N/A'),

			'forecastTomorrow1Pressure': _('N/A'),
			"forecastTomorrow1Code": "(",
			"forecastTomorrow1Day": _('N/A'),
			"forecastTomorrow1Date": _('N/A'),
			"forecastTomorrow1TempMin": "0",
			"forecastTomorrow1TempMax": "0",
			"forecastTomorrow1Text": _('N/A'),
			"forecastTomorrow1Picon": "3200",
			'forecastTomorrow1windSpeed': _('N/A'),
			'forecastTomorrow1windGust': _('N/A'),
			"forecastTomorrow1Probability": _('N/A'),
			'forecastTomorrow1Intensity': _('N/A'),
			'forecastTomorrow1cloudCover': '0',
			'forecastTomorrow1Humidity': _('N/A'),

			'forecastTomorrow2Pressure': _('N/A'),
			"forecastTomorrow2Code": "(",
			"forecastTomorrow2Day": _('N/A'),
			"forecastTomorrow2Date": _('N/A'),
			"forecastTomorrow2TempMin": "0",
			"forecastTomorrow2TempMax": "0",
			"forecastTomorrow2Text": _('N/A'),
			"forecastTomorrow2Picon": "3200",
			'forecastTomorrow2windSpeed': _('N/A'),
			'forecastTomorrow2windGust': _('N/A'),
			"forecastTomorrow2Probability": _('N/A'),
			'forecastTomorrow2Intensity': _('N/A'),
			'forecastTomorrow2cloudCover': '0',
			'forecastTomorrow2Humidity': _('N/A'),

			'forecastTomorrow3Pressure': _('N/A'),
			"forecastTomorrow3Code": "(",
			"forecastTomorrow3Day": _('N/A'),
			"forecastTomorrow3Date": _('N/A'),
			"forecastTomorrow3TempMin": "0",
			"forecastTomorrow3TempMax": "0",
			"forecastTomorrow3Text": _('N/A'),
			"forecastTomorrow3Picon": "3200",
			'forecastTomorrow3windSpeed': _('N/A'),
			'forecastTomorrow3windGust': _('N/A'),
			"forecastTomorrow3Probability": _('N/A'),
			'forecastTomorrow3Intensity': _('N/A'),
			'forecastTomorrow3cloudCover': '0',
			'forecastTomorrow3Humidity': _('N/A'),

			'forecastTomorrow4Pressure': _('N/A'),
			"forecastTomorrow4Code": "(",
			"forecastTomorrow4Day": _('N/A'),
			"forecastTomorrow4Date": _('N/A'),
			"forecastTomorrow4TempMin": "0",
			"forecastTomorrow4TempMax": "0",
			"forecastTomorrow4Text": _('N/A'),
			"forecastTomorrow4Picon": "3200",
			'forecastTomorrow4windSpeed': _('N/A'),
			'forecastTomorrow4windGust': _('N/A'),
			"forecastTomorrow4Probability": _('N/A'),
			'forecastTomorrow4Intensity': _('N/A'),
			'forecastTomorrow4cloudCover': '0',
			'forecastTomorrow4Humidity': _('N/A'),

			'forecastTomorrow5Pressure': _('N/A'),
			"forecastTomorrow5Code": "(",
			"forecastTomorrow5Day": _('N/A'),
			"forecastTomorrow5Date": _('N/A'),
			"forecastTomorrow5TempMin": "0",
			"forecastTomorrow5TempMax": "0",
			"forecastTomorrow5Text": _('N/A'),
			"forecastTomorrow5Picon": "3200",
			'forecastTomorrow5windSpeed': _('N/A'),
			'forecastTomorrow5windGust': _('N/A'),
			"forecastTomorrow5Probability": _('N/A'),
			'forecastTomorrow5Intensity': _('N/A'),
			'forecastTomorrow5cloudCover': '0',
			'forecastTomorrow5Humidity': _('N/A'),

			'forecastTomorrow6Pressure': _('N/A'),
			"forecastTomorrow6Code": "(",
			"forecastTomorrow6Day": _('N/A'),
			"forecastTomorrow6Date": _('N/A'),
			"forecastTomorrow6TempMin": "0",
			"forecastTomorrow6TempMax": "0",
			"forecastTomorrow6Text": _('N/A'),
			"forecastTomorrow6Picon": "3200",
			'forecastTomorrow6windSpeed': _('N/A'),
			'forecastTomorrow6windGust': _('N/A'),
			"forecastTomorrow6Probability": _('N/A'),
			'forecastTomorrow6Intensity': _('N/A'),
			'forecastTomorrow6cloudCover': '0',
			'forecastTomorrow6Humidity': _('N/A'),

			'forecastHourlyHour': _('N/A'),
			'forecastHourlyTemp': '0',
			'forecastHourlywindSpeed': _('N/A'),
			'forecastHourlyPressure': _('N/A'),
			'forecastHourlyHumidity': _('N/A'),
			'forecastHourlyText': _('N/A'),
			'forecastHourlyPicon': '3200',
			'forecastHourlyCloud': '0',
			'forecastHourlyIntensity': '0' + _(' mm/3h'),

			'forecastHourly1Hour': _('N/A'),
			'forecastHourly1Temp': '0',
			'forecastHourly1windSpeed': _('N/A'),
			'forecastHourly1Pressure': _('N/A'),
			'forecastHourly1Humidity': _('N/A'),
			'forecastHourly1Text': _('N/A'),
			'forecastHourly1Picon': '3200',
			'forecastHourly1Cloud': '0',
			'forecastHourly1Intensity': '0' + _(' mm/3h'),

			'forecastHourly2Hour': _('N/A'),
			'forecastHourly2Temp': '0',
			'forecastHourly2windSpeed': _('N/A'),
			'forecastHourly2Pressure': _('N/A'),
			'forecastHourly2Humidity': _('N/A'),
			'forecastHourly2Text': _('N/A'),
			'forecastHourly2Picon': '3200',
			'forecastHourly2Cloud': '0',
			'forecastHourly2Intensity': '0' + _(' mm/3h'),

			'forecastHourly3Hour': _('N/A'),
			'forecastHourly3Temp': '0',
			'forecastHourly3windSpeed': _('N/A'),
			'forecastHourly3Pressure': _('N/A'),
			'forecastHourly3Humidity': _('N/A'),
			'forecastHourly3Text': _('N/A'),
			'forecastHourly3Picon': '3200',
			'forecastHourly3Cloud': '0',
			'forecastHourly3Intensity': '0' + _(' mm/3h'),

			'forecastHourly4Hour': _('N/A'),
			'forecastHourly4Temp': '0',
			'forecastHourly4windSpeed': _('N/A'),
			'forecastHourly4Pressure': _('N/A'),
			'forecastHourly4Humidity': _('N/A'),
			'forecastHourly4Text': _('N/A'),
			'forecastHourly4Picon': '3200',
			'forecastHourly4Cloud': '0',
			'forecastHourly4Intensity': '0' + _(' mm/3h'),

			'forecastHourly5Hour': _('N/A'),
			'forecastHourly5Temp': '0',
			'forecastHourly5windSpeed': _('N/A'),
			'forecastHourly5Pressure': _('N/A'),
			'forecastHourly5Humidity': _('N/A'),
			'forecastHourly5Text': _('N/A'),
			'forecastHourly5Picon': '3200',
			'forecastHourly5Cloud': '0',
			'forecastHourly5Intensity': '0' + _(' mm/3h'),

			'forecastHourly6Hour': _('N/A'),
			'forecastHourly6Temp': '0',
			'forecastHourly6windSpeed': _('N/A'),
			'forecastHourly6Pressure': _('N/A'),
			'forecastHourly6Humidity': _('N/A'),
			'forecastHourly6Text': _('N/A'),
			'forecastHourly6Picon': '3200',
			'forecastHourly6Cloud': '0',
			'forecastHourly6Intensity': '0' + _(' mm/3h'),

			'forecastHourly7Hour': _('N/A'),
			'forecastHourly7Temp': '0',
			'forecastHourly7windSpeed': _('N/A'),
			'forecastHourly7Pressure': _('N/A'),
			'forecastHourly7Humidity': _('N/A'),
			'forecastHourly7Text': _('N/A'),
			'forecastHourly7Picon': '3200',
			'forecastHourly7Cloud': '0',
			'forecastHourly7Intensity': '0' + _(' mm/3h'),

			'forecastHourly8Hour': _('N/A'),
			'forecastHourly8Temp': '0',
			'forecastHourly8windSpeed': _('N/A'),
			'forecastHourly8Pressure': _('N/A'),
			'forecastHourly8Humidity': _('N/A'),
			'forecastHourly8Text': _('N/A'),
			'forecastHourly8Picon': '3200',
			'forecastHourly8Cloud': '0',

			'PiconMoon': '3200',
		}

		if refreshInterval > 0:
			self.timer = eTimer()
			self.timer.callback.append(self.GetWeather)
			self.GetWeather()

	def downloadError(self, error = None):
		write_log("Error : " + str(error))

	def GetWeather(self):
		timeout = (refreshInterval * 1000 * 60)
		if timeout > 0:
			if os.path.isfile("/tmp/blueMetal.log"):
				os.remove("/tmp/blueMetal.log")

	# Calculation moon phase
			self.WeatherInfo["currentMoonPhase"] = self.moonphase()[0]
			self.WeatherInfo["currentMoonPicon"] = self.moonphase()[1]

			self.timer.start(timeout, True)

			if config.plugins.blueMetal.Provider.value == "Darksky":
				apikey = config.plugins.blueMetal.Darksky_apikey.value
				url = "https://api.darksky.net/forecast/" + apikey + "/" + lat + "," + lon + "?&lang=" + countrycode + "&units=" + dsunits
				if log:
					write_log("DARKSKY-URL : " + str(url))
				url = six.ensure_binary(url)
				getPage(url).addCallback(self.GotDarkskyWeatherData).addErrback(self.downloadError)

			elif config.plugins.blueMetal.Provider.value == "OpenWeathermap":
				apikey = config.plugins.blueMetal.OpenWeathermap_apikey.value
				geolocation = "id=" + location
				url = "http://api.openweathermap.org/data/2.5/forecast?" + geolocation + "&APPID=" + apikey + "&units=metric&lang=" + countrycode
				write_log("OWM-URL : " + str(url))

#				getPage(url, method = "GET", timeout = 20).addCallback(self.GotOpenWeatherMapWeatherData).addErrback(self.downloadError)

				url = six.ensure_binary(url)
				getPage(url).addCallback(self.GotOpenWeatherMapWeatherData).addErrback(self.downloadError)

				url = "http://api.openweathermap.org/data/2.5/weather?" + geolocation + "&APPID=" + apikey + "&units=metric&lang=" + countrycode
				write_log("COWMURL : " + str(url))

				url = six.ensure_binary(url)
				getPage(url).addCallback(self.GotCurrentOpenWeatherMapWeatherData).addErrback(self.downloadError)
#method = "GET"
#Darksky
	def GotDarkskyWeatherData(self, data = None):
		write_log("Data : " + str(data))
		if data is not None:
			try:
				parsed_json = json.loads(data)
				for k, v in list(parsed_json.items()):
					write_log(str(k) + ":" + str(v))

#				self.WeatherInfo["W-Info"] = str(parsed_json['daily']['summary'])
#				self.WeatherInfo["W-Info-h"] = str(parsed_json['hourly']['summary'])
				self.WeatherInfo["timezone"] = _(str(parsed_json['timezone']))
				self.WeatherInfo['currentCity'] = city

				self.WeatherInfo['astroDayLength'] = self.convertAstroDayLength(float((parsed_json['daily']['data'][0]['sunsetTime']) - (parsed_json['daily']['data'][0]['sunriseTime'])) - 10800)
# -- Location --
				self.WeatherInfo["currentLocation"] = format(float(parsed_json['latitude']), '.4f') + " / " + format(float(parsed_json['longitude']), '.4f')
				self.WeatherInfo["geoLat"] = format(float(parsed_json['latitude']), '.4f')
				self.WeatherInfo["geoLong"] = format(float(parsed_json['longitude']), '.4f')
				self.WeatherInfo["geoData"] = format(float(parsed_json['latitude']), '.4f') + " / " + format(float(parsed_json['longitude']), '.4f')
# -- Wind Direction--
				if config.plugins.blueMetal.winddirection.value == 'short':
					self.WeatherInfo['windDirection'] = str(self.ConvertDirectionShort(parsed_json['currently']['windBearing']))
				else:
					self.WeatherInfo["windDirection"] = str(self.ConvertDirectionLong(parsed_json['currently']['windBearing']))
				self.WeatherInfo["atmoHumidity"] = format(float(parsed_json['currently']['humidity']) * 100, '.0f') + ' %'

				if config.plugins.blueMetal.windspeedUnit.value == 'mp/h':
					self.WeatherInfo["atmoVisibility"] = format(float(parsed_json['currently']['visibility']) * 0.62137, str(numbers)) + _(' miles')
				else:
					self.WeatherInfo["atmoVisibility"] = format(float(parsed_json['currently']['visibility']), str(numbers)) + _(' km')
				self.WeatherInfo["astroSunrise"] = self.convertAstroSun(parsed_json['daily']['data'][0]['sunriseTime'])
				self.WeatherInfo["astroSunset"] = self.convertAstroSun(parsed_json['daily']['data'][0]['sunsetTime'])
				self.WeatherInfo['astroDaySoltice'] = self.convertAstroSun(float((parsed_json['daily']['data'][0]['sunsetTime']) + (parsed_json['daily']['data'][0]['sunriseTime'])) * 0.5) 

				self.WeatherInfo['uvIndex'] = format(float(parsed_json['currently']['uvIndex']), '.0f') + ' / 10'

				self.WeatherInfo["downloadDate"] = self.convertCurrentDate(parsed_json['currently']['time'])
				self.WeatherInfo["downloadTime"] = self.convertCurrentTime(parsed_json['currently']['time'])

# --- Current ---
				self.WeatherInfo["windChill"] = self.convertTemperature(parsed_json['currently']['apparentTemperature'])
				self.WeatherInfo["dewPoint"] = self.convertTemperature(parsed_json['currently']['dewPoint'])
				self.WeatherInfo["currentWeatherTemp"] = self.convertTemperature(parsed_json['currently']['temperature'])
				self.WeatherInfo['currentlywindSpeed'] = self.convertwindSpeed(parsed_json['currently']['windSpeed'])
				self.WeatherInfo['currentlywindGust'] = self.convertwindSpeed(parsed_json['currently']['windGust'])
				self.WeatherInfo["currentPressure"] = self.convertPressure(parsed_json['currently']['pressure'])
				self.WeatherInfo["currentWeatherCode"] = self.ConvertIconCode(parsed_json['currently']['icon'])
#				self.WeatherInfo["currentWeatherText"] = str(parsed_json['currently']['summary'])
				self.WeatherInfo['currentWeatherPicon'] = self.convertIconName(parsed_json['currently']['icon'])
				self.WeatherInfo['currentProbability'] = format(float(parsed_json['currently']['precipProbability']) * 100, str(numbers)) + ' %'
				self.WeatherInfo['currentcloudCover'] = format(float(parsed_json['currently']['cloudCover']) * 100, str(numbers)) + ' %'
				self.WeatherInfo['currentlyIntensity'] = format(float(parsed_json['currently']['precipIntensity']), '.4f') + _(' mm/h')
				self.WeatherInfo['currentOzoneText'] = format(float(parsed_json['currently']['ozone']), str(numbers)) + _(' DU')
# --- Today ---
				self.WeatherInfo["forecastTodayTempMax"] = self.convertTemperature(parsed_json['daily']['data'][0]['temperatureMax'])
				self.WeatherInfo["forecastTodayTempMin"] = self.convertTemperature(parsed_json['daily']['data'][0]['temperatureMin'])
				self.WeatherInfo['forecastTodaywindSpeed'] = self.convertwindSpeed(parsed_json['daily']['data'][0]['windSpeed'])
				self.WeatherInfo['forecastTodaywindGust'] = self.convertwindSpeed(parsed_json['daily']['data'][0]['windGust'])
				self.WeatherInfo["forecastTodayPressure"] = self.convertPressure(parsed_json['daily']['data'][0]['pressure'])
				self.WeatherInfo["forecastTodayCode"] = self.ConvertIconCode(parsed_json['daily']['data'][0]['icon'])
				self.WeatherInfo["forecastTodayDay"] = self.convertCurrentDay(parsed_json['daily']['data'][0]['time'])
				self.WeatherInfo["forecastTodayDate"] = self.convertCurrentDate(parsed_json['daily']['data'][0]['time'])
#				self.WeatherInfo["forecastTodayText"] = self.convertWeatherText(parsed_json['daily']['data'][0]['summary'])
				self.WeatherInfo["forecastTodayPicon"] = self.convertIconName(parsed_json['daily']['data'][0]['icon'])
				self.WeatherInfo['forecastTodayProbability'] = format(float(parsed_json['daily']['data'][0]['precipProbability']) * 100, str(numbers)) + ' %'
				self.WeatherInfo['forecastTodaycloudCover'] = format(float(parsed_json['daily']['data'][0]['cloudCover']) * 100, str(numbers)) + ' %'
				self.WeatherInfo['forecastTodayIntensity'] = format(float(parsed_json['daily']['data'][0]['precipIntensity']), str(numbers)) + _(' mm')
				self.WeatherInfo['forecastTodayOzoneText'] = format(float(parsed_json['daily']['data'][0]['ozone']), str(numbers)) + _(' DU')
				self.WeatherInfo['forecastTodaymoonPhase'] = self.convertMoon(float(parsed_json['daily']['data'][0]['moonPhase']))
				self.WeatherInfo['PiconMoon'] = self.convertPiconMoon(float(parsed_json['daily']['data'][0]['moonPhase']))

				days = ['0', '1', '2', '3', '4', '5','6']
				for day in days:
					aday = int(day)+1
					if day == "0":
						day = ""

					self.WeatherInfo['forecastTomorrow' + day + 'TempMax'] = self.convertTemperature(parsed_json['daily']['data'][aday]['temperatureMax'])
					self.WeatherInfo['forecastTomorrow' + day + 'TempMin'] = self.convertTemperature(parsed_json['daily']['data'][aday]['temperatureMin'])
					self.WeatherInfo['forecastTomorrow' + day + 'windSpeed'] = self.convertwindSpeed(parsed_json['daily']['data'][aday]['windSpeed'])
					self.WeatherInfo['forecastTomorrow' + day + 'Pressure'] = self.convertPressure(parsed_json['daily']['data'][aday]['pressure'])
					self.WeatherInfo['forecastTomorrow' + day + 'Day'] = self.convertCurrentDay(parsed_json['daily']['data'][aday]['time'])
					self.WeatherInfo['forecastTomorrow' + day + 'Date'] = self.convertCurrentDate(parsed_json['daily']['data'][aday]['time'])
#					self.WeatherInfo['forecastTomorrow' + day + "Text"] = self.convertWeatherText(parsed_json['daily']['data'][aday]['summary'])
					self.WeatherInfo['forecastTomorrow' + day + 'Picon'] = self.convertIconName(parsed_json['daily']['data'][aday]['icon'])
					self.WeatherInfo['forecastTomorrow' + day + 'Probability'] = format(float(parsed_json['daily']['data'][aday]['precipProbability']) * 100, str(numbers)) + ' %'
					self.WeatherInfo['forecastTomorrow' + day + 'cloudCover'] = format(float(parsed_json['daily']['data'][aday]['cloudCover']) * 100, str(numbers)) + ' %'

				hourly = ['0', '1', '2', '3', '4', '5', '6', '7', '8']
				for hour in hourly:
					ahour = int(hour)+1
					if hour == "0":
						hour = ""

					self.WeatherInfo['forecastHourly' + hour + 'Hour'] = self.convertAstroSun(parsed_json['hourly']['data'][ahour]['time'])
					self.WeatherInfo['forecastHourly' + hour + 'Temp'] = self.convertTemperature(parsed_json['hourly']['data'][ahour]['temperature'])

					self.WeatherInfo['forecastHourly' + hour + 'windSpeed'] = self.convertwindSpeed(parsed_json['hourly']['data'][ahour]['windSpeed'])
					self.WeatherInfo['forecastHourly' + hour + 'Pressure'] = self.convertPressure(parsed_json['hourly']['data'][ahour]['pressure'])
					self.WeatherInfo['forecastHourly' + hour + 'Humidity'] = format(float(parsed_json['hourly']['data'][ahour]['humidity']) * 100, '.0f') + ' %'
					self.WeatherInfo['forecastHourly' + hour + 'Cloud'] = format(float(parsed_json['hourly']['data'][ahour]['cloudCover']) * 100, str(numbers)) + ' %'
#					self.WeatherInfo['forecastHourly' + hour + 'Text'] = self.convertWeatherText(parsed_json['hourly']['data'][ahour]['summary'])
					self.WeatherInfo['forecastHourly' + hour + 'Picon'] = self.convertIconName(parsed_json['hourly']['data'][ahour]['icon'])
				
				for k, v in list(self.WeatherInfo.items()):
					write_log("WeatherInfo : " + str(k) + ":" + str(v))
			except Exception as ex:
				write_log(_("Error in GotWeatherData : ") + str(ex))


#OpenWeatherMap
	def GotOpenWeatherMapWeatherData(self, data = None):
		write_log("###################################### OpenWeatherMap Data ################################################")
		write_log("Data : " + str(data))
		if data is not None:
			try:
				parsed_json = json.loads(data)
				for k, v in list(parsed_json.items()):
					write_log(str(k) + ":" + str(v))
				write_log(str(len(parsed_json["list"])))

				write_log("###################################### OpenWeatherMap ################################################")
				for k, v in list(parsed_json["list"][0].items()):
					write_log(str(k) + ":" + str(v))

				self.WeatherInfo["forecastTomorrow4Date"] = " "
				self.WeatherInfo["forecastTomorrow4Day"] = " "
				self.WeatherInfo["forecastTomorrow4Code"] = " "
				self.WeatherInfo["forecastTomorrow4Picon"] = " "
				self.WeatherInfo["forecastTomorrow4TempMax"] = " "
				self.WeatherInfo["forecastTomorrow4TempMin"] = " "
				self.WeatherInfo["forecastTomorrow4Text"] = " "

#-------------------- hourly -------------------------------------------------------------------------------------------

				hourly = ['0', '1', '2', '3', '4', '5', '6', '7']
				for hour in hourly:
					ahour = int(hour)
					if hour == "0":
						hour = ""
					self.WeatherInfo['forecastHourly' + hour + 'Hour'] = str(parsed_json['list'][ahour]['dt_txt'])
					self.WeatherInfo['forecastHourly' + hour + 'Temp'] = self.convertTemperature(parsed_json['list'][ahour]['main']['temp'])
					self.WeatherInfo['forecastHourly' + hour + 'Humidity'] = format(float(parsed_json['list'][ahour]['main']['humidity']), '.0f') + ' %'
					self.WeatherInfo['forecastHourly' + hour + 'Cloud'] = format(float(parsed_json['list'][ahour]['clouds']['all'])) + ' %'
					self.WeatherInfo['forecastHourly' + hour + 'windSpeed'] = self.convertwindSpeed(parsed_json['list'][ahour]['wind']['speed'])
					self.WeatherInfo['forecastHourly' + hour + 'Picon'] = self.convertOWMIconName(parsed_json['list'][ahour]['weather'][0]['icon'])
					self.WeatherInfo['forecastHourly' + hour + 'Text'] = str(parsed_json['list'][ahour]['weather'][0]['description'])
					self.WeatherInfo['forecastHourly' + hour + 'Pressure'] = self.convertPressure(parsed_json['list'][ahour]['main']['pressure'])

					if "rain" in parsed_json['list'][ahour]:
						self.WeatherInfo['forecastHourly' + hour + 'Intensity'] = str(parsed_json['list'][ahour]['rain']['3h']) + _(' mm/3h')
					elif "snow" in parsed_json['list'][ahour]:
						self.WeatherInfo['forecastHourly' + hour + 'Intensity'] = str(parsed_json['list'][ahour]['snow']['3h']) + _(' mm/3h')
					else:
						self.WeatherInfo['forecastHourly' + hour + 'Intensity'] = '0' + _(' mm/3h')

#-----------------------------------------------------------------------------------------------------------------------
			# find next day
				i = 0
				next_day = 0
				sNOW = datetime.datetime.now().strftime('%d.%m.%Y')		# get the current date and compare timestamps to that.
				while i < 8:
					if str(self.convertCurrentDateLong(parsed_json["list"][i]['dt'])) != sNOW:
						next_day = i
						write_log("morgen startet bei Index " + str(next_day))
						break
					i += 1
				self.WeatherInfo["forecastTodayDay"] = self.convertCurrentDay(parsed_json['list'][0]['dt'])
				self.WeatherInfo["forecastTodayDate"] = self.convertCurrentDate(parsed_json['list'][0]['dt'])

				i = 0
				icons = []
				description = []
				clouds = []
				wspeed = []
				pressure = []
				humidity = []
				tempmin = 100
				tempmax = -100
				if int(next_day) > 0:
					while i < int(next_day):
						icons.append(parsed_json["list"][i]['weather'][0]['icon'])
						description.append(parsed_json["list"][i]['weather'][0]['description'])
						clouds.append(format(float(parsed_json['list'][i]['clouds']['all'])))
						wspeed.append(parsed_json["list"][i]['wind']['speed'])
						pressure.append(parsed_json["list"][i]['main']['pressure'])
						humidity.append(format(float(parsed_json["list"][i]['main']['humidity'])))
						if float(parsed_json["list"][i]['main']['temp']) < tempmin:
							tempmin = float(parsed_json["list"][i]['main']['temp'])
						if float(parsed_json["list"][i]['main']['temp']) > tempmax:
							tempmax = float(parsed_json["list"][i]['main']['temp'])
						i += 1
					self.WeatherInfo["forecastTodayCode"] = str(self.ConvertIconCode(icons[int(len(icons)/2)]))
					self.WeatherInfo["forecastTodayPicon"] = str(self.convertOWMIconName(icons[int(len(icons)/2)]))
					self.WeatherInfo["forecastTodayText"] = str(description[int(len(description)/2)])
					self.WeatherInfo['forecastTodayTempMax'] = self.convertTemperature(tempmax)
					self.WeatherInfo['forecastTodayTempMin'] = self.convertTemperature(tempmin)
					self.WeatherInfo['forecastTodaycloudCover'] = str(clouds[int(len(clouds)/2)]) + ' %'
					self.WeatherInfo['forecastTodaywindSpeed'] = str(self.convertwindSpeed(wspeed[int(len(wspeed)/2)]))
					self.WeatherInfo['forecastTodayPressure'] = str(self.convertPressure(pressure[int(len(pressure)/2)]))
					self.WeatherInfo['forecastTodayHumidity'] = str(humidity[int(len(humidity)/2)]) + ' %'
				else:
					while i < 8:
						icons.append(parsed_json["list"][i]['weather'][0]['icon'])
						description.append(parsed_json["list"][i]['weather'][0]['description'])
						clouds.append(format(float(parsed_json['list'][i]['clouds']['all'])))
						wspeed.append(parsed_json["list"][i]['wind']['speed'])
						pressure.append(parsed_json["list"][i]['main']['pressure'])
						humidity.append(format(float(parsed_json["list"][i]['main']['humidity'])))
						if float(parsed_json["list"][i]['main']['temp']) < tempmin:
							tempmin = float(parsed_json["list"][i]['main']['temp'])
						if float(parsed_json["list"][i]['main']['temp']) > tempmax:
							tempmax = float(parsed_json["list"][i]['main']['temp'])
						i += 1
					self.WeatherInfo["forecastTodayCode"] = str(self.ConvertIconCode(icons[int(len(icons)/2)]))
					self.WeatherInfo["forecastTodayPicon"] = str(self.convertOWMIconName(icons[int(len(icons)/2)]))
					self.WeatherInfo["forecastTodayText"] = str(description[int(len(description)/2)])
					self.WeatherInfo['forecastTodayTempMax'] = self.convertTemperature(tempmax)
					self.WeatherInfo['forecastTodayTempMin'] = self.convertTemperature(tempmin)
					self.WeatherInfo['forecastTodaycloudCover'] = str(clouds[int(len(clouds)/2)]) + ' %'
					self.WeatherInfo['forecastTodaywindSpeed'] = str(self.convertwindSpeed(wspeed[int(len(wspeed)/2)]))
					self.WeatherInfo['forecastTodayPressure'] = str(self.convertPressure(pressure[int(len(pressure)/2)]))
					self.WeatherInfo['forecastTodayHumidity'] = str(humidity[int(len(humidity)/2)]) + ' %'


				if next_day == 0:
					next_day = 8
				i = next_day
				icons = []
				description = []
				clouds = []
				wspeed = []
				pressure = []
				humidity = []
				tempmin = 100
				tempmax = -100
				self.WeatherInfo["forecastTomorrowDay"] = self.convertCurrentDay(parsed_json['list'][i]['dt'])
				self.WeatherInfo["forecastTomorrowDate"] = self.convertCurrentDate(parsed_json['list'][i]['dt'])
				while i < int(next_day + 8):
					icons.append(parsed_json["list"][i]['weather'][0]['icon'])
					description.append(parsed_json["list"][i]['weather'][0]['description'])
					clouds.append(format(float(parsed_json['list'][i]['clouds']['all'])))
					wspeed.append(parsed_json["list"][i]['wind']['speed'])
					pressure.append(parsed_json["list"][i]['main']['pressure'])
					humidity.append(format(float(parsed_json["list"][i]['main']['humidity'])))
					if float(parsed_json["list"][i]['main']['temp']) < tempmin:
						tempmin = float(parsed_json["list"][i]['main']['temp'])
					if float(parsed_json["list"][i]['main']['temp']) > tempmax:
						tempmax = float(parsed_json["list"][i]['main']['temp'])
					i += 1
				self.WeatherInfo["forecastTomorrowCode"] = str(self.ConvertIconCode(icons[int(len(icons)/2)]))
				self.WeatherInfo["forecastTomorrowPicon"] = str(self.convertOWMIconName(icons[int(len(icons)/2)]))
				self.WeatherInfo["forecastTomorrowText"] = str(description[int(len(description)/2)])
				self.WeatherInfo['forecastTomorrowcloudCover'] = str(clouds[int(len(clouds)/2)]) + ' %'
				self.WeatherInfo['forecastTomorrowTempMax'] = self.convertTemperature(tempmax)
				self.WeatherInfo['forecastTomorrowTempMin'] = self.convertTemperature(tempmin)
				self.WeatherInfo['forecastTomorrowwindSpeed'] = str(self.convertwindSpeed(wspeed[int(len(wspeed)/2)]))
				self.WeatherInfo['forecastTomorrowPressure'] = str(self.convertPressure(pressure[int(len(pressure)/2)]))
				self.WeatherInfo['forecastTomorrowHumidity'] = str(humidity[int(len(humidity)/2)]) + ' %'

				if next_day == 8:
					next_day = 16
				else:
					next_day = next_day + 8
				day = 0
				for aday in range(0, 4):
					day += 1
					i = next_day + (aday * 8)
					nd = i
					icons = []
					description = []
					clouds = []
					wspeed = []
					pressure = []
					humidity = []
					tempmin = 100
					tempmax = -100
					if i < int(len(parsed_json["list"])):
						self.WeatherInfo["forecastTomorrow" + str(day) + "Day"] = self.convertCurrentDay(parsed_json['list'][i]['dt'])
						self.WeatherInfo["forecastTomorrow" + str(day) + "Date"] = self.convertCurrentDate(parsed_json['list'][i]['dt'])
						while i < int(nd + 8) and i < int(len(parsed_json["list"])):
							icons.append(parsed_json["list"][i]['weather'][0]['icon'])
							description.append(parsed_json["list"][i]['weather'][0]['description'])
							clouds.append(format(float(parsed_json['list'][i]['clouds']['all'])))
							wspeed.append(parsed_json["list"][i]['wind']['speed'])
							pressure.append(parsed_json["list"][i]['main']['pressure'])
							humidity.append(format(float(parsed_json["list"][i]['main']['humidity'])))
							if float(parsed_json["list"][i]['main']['temp']) < tempmin:
								tempmin = float(parsed_json["list"][i]['main']['temp'])
							if float(parsed_json["list"][i]['main']['temp']) > tempmax:
								tempmax = float(parsed_json["list"][i]['main']['temp'])
							i += 1

						self.WeatherInfo["forecastTomorrow" + str(day) + "Text"] = str(description[int(len(description)/2)])
						self.WeatherInfo["forecastTomorrow" + str(day) + "Code"] = str(self.ConvertIconCode(icons[int(len(icons)/2)]))
						self.WeatherInfo["forecastTomorrow" + str(day) + "Picon"] = str(self.convertOWMIconName(icons[int(len(icons)/2)]))
						self.WeatherInfo['forecastTomorrow' + str(day) + 'cloudCover'] = str(clouds[int(len(clouds)/2)]) + ' %'
						self.WeatherInfo["forecastTomorrow" + str(day) + "TempMax"] = self.convertTemperature(tempmax)		#!
						self.WeatherInfo["forecastTomorrow" + str(day) + "TempMin"] = self.convertTemperature(tempmin)		#!
						self.WeatherInfo['forecastTomorrow' + str(day) + 'windSpeed'] = str(self.convertwindSpeed(wspeed[int(len(wspeed)/2)]))
						self.WeatherInfo['forecastTomorrow' + str(day) + 'Pressure'] = str(self.convertPressure(pressure[int(len(pressure)/2)]))
						self.WeatherInfo['forecastTomorrow' + str(day) + 'Humidity'] = str(humidity[int(len(humidity)/2)]) + ' %'

			except Exception as ex:
				write_log("Mistake in GotOpenWeatherMapWeatherData : " + str(ex))


#CurrentOpenWeatherMap
	def GotCurrentOpenWeatherMapWeatherData(self, data = None):
		write_log("###################################### Current OpenWeatherMap Data ################################################")
		write_log("Data : " + str(data))
		if data is not None:
			try:
				parsed_json = json.loads(data)

				self.WeatherInfo["currentLocation"] = _(str(parsed_json['name']))						
				self.WeatherInfo["currentCountry"] = str(parsed_json['sys']["country"])

				if "deg" in parsed_json['wind']:
					if config.plugins.blueMetal.winddirection.value == 'short':
						self.WeatherInfo['windDirection'] = str(self.ConvertDirectionShort(parsed_json['wind']['deg']))
					else:
						self.WeatherInfo["windDirection"] = str(self.ConvertDirectionLong(parsed_json['wind']['deg']))
				else:
					self.WeatherInfo["windDirection"] = "--"

				self.WeatherInfo['currentlywindSpeed'] = self.convertwindSpeed(parsed_json['wind']['speed'])
				self.WeatherInfo["currentPressure"] = self.convertPressure(parsed_json['main']['pressure'])
				self.WeatherInfo['currentcloudCover'] = format(float(parsed_json['clouds']['all'])) + ' %'
				self.WeatherInfo["atmoHumidity"] = format(float(parsed_json['main']['humidity']), '.0f') + ' %'

				if "visibility" in parsed_json:
					if config.plugins.blueMetal.windspeedUnit.value == 'mp/h':
						self.WeatherInfo["atmoVisibility"] = format(float(parsed_json['visibility']) / 1000 * 0.62137, str(numbers)) + _(' miles')
					else:
						self.WeatherInfo["atmoVisibility"] = format(float(parsed_json['visibility']) / 1000, str(numbers)) + _(' km')
				else:
					self.WeatherInfo["atmoVisibility"] = "--"

				self.WeatherInfo["astroSunrise"] = self.convertAstroSun(parsed_json['sys']['sunrise'])
				self.WeatherInfo["astroSunset"] = self.convertAstroSun(parsed_json['sys']['sunset'])
				self.WeatherInfo['astroDaySoltice'] = self.convertAstroSun(float((parsed_json['sys']['sunset']) + (parsed_json['sys']['sunrise'])) * 0.5)
				self.WeatherInfo['astroDayLength'] = self.convertAstroDayLength(float((parsed_json['sys']['sunset']) - (parsed_json['sys']['sunrise'])) - 10800)														

				self.WeatherInfo["geoLat"] = format(float(parsed_json['coord']['lat']), '.4f')
				self.WeatherInfo["geoLong"] = format(float(parsed_json['coord']['lon']), '.4f')
				self.WeatherInfo["geoData"] = format(float(parsed_json['coord']['lat']), '.4f') + " / " + format(float(parsed_json['coord']['lon']), '.4f')
				self.WeatherInfo["downloadDate"] = self.convertCurrentDateLong(parsed_json['dt'])
				self.WeatherInfo["downloadTime"] = self.convertCurrentTime(parsed_json['dt'])
				self.WeatherInfo["currentWeatherTemp"] = self.convertTemperature(parsed_json['main']['temp'])
				self.WeatherInfo['currentWeatherText'] = str(parsed_json['weather'][0]['description'])
				self.WeatherInfo["currentWeatherPicon"] = self.convertOWMIconName(parsed_json['weather'][0]['icon'])

				write_log("###################################### Current OpenWeatherMap ################################################")
				for k, v in list(parsed_json.items()):
					write_log(str(k) + ":" + str(v))
			except Exception as ex:
				write_log("Mistake in GotCurrentOpenWeatherMapWeatherData : " + str(ex))


	def convertPiconMoon(self, moonPhase):
		dir = float(moonPhase)
		if 0.0 <= dir < 0.02:
			moonPhase = '1'
		elif 0.02 <= dir < 0.05:
			moonPhase = '5'
		elif 0.05 <= dir < 0.07:
			moonPhase = '10'
		elif 0.07 <= dir < 0.10:
			moonPhase = '15'
		elif 0.10 <= dir < 0.12:
			moonPhase = '20'
		elif 0.12 <= dir < 0.15:
			moonPhase = '25'
		elif 0.15 <= dir < 0.17:
			moonPhase = '30'
		elif 0.17 <= dir < 0.20:
			moonPhase = '35'
		elif 0.20 <= dir < 0.22:
			moonPhase = '40'
		elif 0.22 <= dir < 0.24:
			moonPhase = '45'
		elif 0.24 <= dir < 0.26:
			moonPhase = '50'
		elif 0.26 <= dir < 0.30:
			moonPhase = '55'
		elif 0.30 <= dir < 0.32:
			moonPhase = '60'
		elif 0.32 <= dir < 0.35:
			moonPhase = '65'
		elif 0.35 <= dir < 0.37:
			moonPhase = '70'
		elif 0.37 <= dir < 0.40:
			moonPhase = '75'
		elif 0.40 <= dir < 0.42:
			moonPhase = '80'
		elif 0.42 <= dir < 0.45:
			moonPhase = '85'
		elif 0.45 <= dir < 0.47:
			moonPhase = '90'
		elif 0.47 <= dir < 0.49:
			moonPhase = '95'
		elif 0.49 <= dir < 0.51:
			moonPhase = '100'
		elif 0.51 <= dir < 0.53:
			moonPhase = '095'
		elif 0.53 <= dir < 0.55:
			moonPhase = '090'
		elif 0.55 <= dir < 0.58:
			moonPhase = '085'
		elif 0.58 <= dir < 0.60:
			moonPhase = '080'
		elif 0.60 <= dir < 0.63:
			moonPhase = '075'
		elif 0.63 <= dir < 0.65:
			moonPhase = '070'
		elif 0.65 <= dir < 0.68:
			moonPhase = '065'
		elif 0.68 <= dir < 0.70:
			moonPhase = '060'
		elif 0.70 <= dir < 0.73:
			moonPhase = '055'
		elif 0.73 <= dir < 0.76:
			moonPhase = '050'
		elif 0.76 <= dir < 0.78:
			moonPhase = '045'
		elif 0.78 <= dir < 0.80:
			moonPhase = '040'
		elif 0.80 <= dir < 0.83:
			moonPhase = '035'
		elif 0.83 <= dir < 0.85:
			moonPhase = '030'
		elif 0.85 <= dir < 0.88:
			moonPhase = '025'
		elif 0.88 <= dir < 0.90:
			moonPhase = '020'
		elif 0.90 <= dir < 0.93:
			moonPhase = '015'
		elif 0.93 <= dir < 0.95:
			moonPhase = '010'
		elif 0.95 <= dir < 0.98:
			moonPhase = '05'
		elif 0.98 <= dir <= 1.0:
			moonPhase = '1'
		else:
			moonPhase = '3200'
		return str(moonPhase)


	def convertMoon(self, moonPhase):
		dir = float(moonPhase)
		if 0 <= dir  < 0.02:
			moonPhase = _('New moon')
		elif 0.02 <= dir < 0.24:
			moonPhase = _('Waxing crescent')
		elif 0.24 <= dir < 0.26:
			moonPhase = _('First Quarter Moon')
		elif 0.26 <= dir < 0.48:
			moonPhase = _('Waxing gibbous')
		elif 0.48 <= dir < 0.52:
			moonPhase = _('Full moon')
		elif 0.52 <= dir < 0.74:
			moonPhase = _('Waning gibbous')
		elif 0.74 <= dir < 0.76:
			moonPhase = _('Last quarter moon')
		elif 0.76 <= dir < 0.99:
			moonPhase = _('Waning crescent')
		elif 0.99 <= dir <= 1.00:
			moonPhase = _('New moon')
		return str(moonPhase)


	def convertPressure(self, pressure):
		if config.plugins.blueMetal.pressureUnit.value == 'mmHg':
			pressure = format(((pressure) * 0.75), str(numbers)) + _(' mmHg')
		if config.plugins.blueMetal.pressureUnit.value == 'mBar':
			pressure =  format((pressure), str(numbers)) + _(' mBar')
		return str(pressure)


	def convertwindSpeed(self, windSpeed):
		if config.plugins.blueMetal.windspeedUnit.value == 'm/s':
			windSpeed = format((windSpeed), str(numbers)) + _(' m/s')
		if config.plugins.blueMetal.windspeedUnit.value == 'km/h':
			windSpeed = format((windSpeed) * 3.6, str(numbers)) + _(' km/h')
		if config.plugins.blueMetal.windspeedUnit.value == 'mp/h':
			windSpeed = format((windSpeed) * 0.447, str(numbers)) + _(' mp/h')
		if config.plugins.blueMetal.windspeedUnit.value == 'ft/s':
			windSpeed = format((windSpeed) * 0.3048, str(numbers)) + _(' ft/s')
		return str(windSpeed)


	def convertTemperature(self, temp):
		if config.plugins.blueMetal.tempUnit.value == 'Celsius':
			temp = format((temp), str(numbers)) + ' °C'
		if config.plugins.blueMetal.tempUnit.value == 'Fahrenheit':
			temp = format((temp) * 1.8 + 32, str(numbers)) + ' °F'
		return str(temp)


	def ConvertDirectionShort(self, direction):
		dir = int(direction)
		if 0 <= dir <= 20:
				direction = _('N')
		elif 21 <= dir <= 35:
				direction = _('N-NE')
		elif 36 <= dir <= 55:
				direction = _('NE')
		elif 56 <= dir <= 70:
				direction = _('E-NE')
		elif 71 <= dir <= 110:
				direction = _('E')
		elif 111 <= dir <= 125:
				direction = _('E-SE')
		elif 126 <= dir <= 145:
				direction = _('SE')
		elif 146 <= dir <= 160:
				direction = _('S-SE')
		elif 161 <= dir <= 200:
				direction = _('S')
		elif 201 <= dir <= 215:
				direction = _('S-SW')
		elif 216 <= dir <= 235:
				direction = _('SW')
		elif 236 <= dir <= 250:
				direction = _('W-SW')
		elif 251 <= dir <= 290:
				direction = _('W')
		elif 291 <= dir <= 305:
				direction = _('W-NW')
		elif 306 <= dir <= 325:
				direction = _('NW')
		elif 326 <= dir <= 340:
				direction = _('N-NW')
		elif 341 <= dir <= 360:
				direction = _('N')
		else:
				direction = _('N/A')
		return str(direction)


	def ConvertDirectionLong(self, direction):
		dir = int(direction)
		if 0 <= dir <= 20:
				direction = _('North')
		elif 21 <= dir <= 35:
				direction = _('North-Northeast')
		elif 36 <= dir <= 55:
				direction = _('Northeast')
		elif 56 <= dir <= 70:
				direction = _('East-Northeast')
		elif 71 <= dir <= 110:
				direction = _('East')
		elif 111 <= dir <= 125:
				direction = _('East-Southeast')
		elif 126 <= dir <= 145:
				direction = _('Southeast')
		elif 146 <= dir <= 160:
				direction = _('South-Southeast')
		elif 161 <= dir <= 200:
				direction = _('South')
		elif 201 <= dir <= 215:
				direction = _('South-Southwest')
		elif 216 <= dir <= 235:
				direction = _('Southwest')
		elif 236 <= dir <= 250:
				direction = _('West-Southwest')
		elif 251 <= dir <= 290:
				direction = _('West')
		elif 291 <= dir <= 305:
				direction = _('West-Northwest')
		elif 306 <= dir <= 325:
				direction = _('Northwest')
		elif 326 <= dir <= 340:
				direction = _('North-Northwest')
		elif 341 <= dir <= 360:
				direction = _('North')
		else:
				direction = _('N/A')
		return str(direction)


	def convertIconName(self, IconName):
		if IconName == "sleet":
			return "7"
		elif IconName == "wind":
			return "23"
		elif IconName == "fog":
			return "20"
		elif IconName == "partly-cloudy-night":
			return "29"
		elif IconName == "cloudy":
			return "26"
		elif IconName == "clear-night":
			return "31"
		elif IconName == "clear-day":
			return "32"
		elif IconName == "partly-cloudy-day":
			return "30"
		elif IconName == "rain":
			return "12"
		elif IconName == "snow":
			return "14"
		else:
			if log:
				write_log(_('missing IconName : ') + str(IconName))
			return "3200"


	def convertWeatherText(self, WeatherText):
		return str(_(WeatherText.replace('-',' ')))


	def convertAstroSun(self, val):
		value = datetime.datetime.fromtimestamp(int(val))
		return value.strftime(_('%H:%M'))


	def convertAstroDayLength(self, val):
		value = datetime.datetime.fromtimestamp(int(val))
		return value.strftime(_('%H h. %M min.'))


	def convertCurrentDate(self, val):
		value = datetime.datetime.fromtimestamp(int(val))
		if config.plugins.blueMetal.WeekDay.value == 'dm':
			return value.strftime(_('%d.%m'))
		else:
			return value.strftime(_('%d.%m.%Y'))


	def convertCurrentDateLong(self, val):
		value = datetime.datetime.fromtimestamp(int(val))
		return value.strftime(_('%d.%m.%Y'))


	def convertCurrentTime(self, val):
		value = datetime.datetime.fromtimestamp(int(val))
		return value.strftime(_('%H:%M:%S'))


	def convertCurrentDay(self, val):
		value = int(datetime.datetime.fromtimestamp(int(val)).strftime("%w"))
		return wdays[value]


	def convertDateTime(self, val):
		value = datetime.datetime.fromtimestamp(int(val))
		return value.strftime(_('%d.%m.%Y %H:%M:%S'))


	def ConvertIconCode(self, IconName):
		if IconName == "01d":
			return "B"
		elif IconName == "02d":
			return "H"
		elif IconName == "03d":
			return "H"
		elif IconName == "04d":
			return "N"
		elif IconName == "05d":
			return "Q"
		elif IconName == "06d":
			return "O"
		elif IconName == "07d":
			return "U"
		elif IconName == "08d":
			return "W"
		elif IconName == "09d":
			return "X"
		elif IconName == "10d":
			return "Q"
		elif IconName == "11d":
			return "S"
		elif IconName == "12d":
			return "X"
		elif IconName == "13d":
			return "W"
		elif IconName == "14d":
			return "O"
		elif IconName == "15d":
			return "N"
		elif IconName == "20d":
			return "E"
		elif IconName == "21d":
			return "E"
		elif IconName == "22d":
			return "Z"
		elif IconName == "23d":
			return "T"
		elif IconName == "30d":
			return "S"
		elif IconName == "31d":
			return "S"
		elif IconName == "32d":
			return "T"
		elif IconName == "33d":
			return "W"
		elif IconName == "34d":
			return "W"
		elif IconName == "40d":
			return "H"
		elif IconName == "46d":
			return "Q"
		elif IconName == "47d":
			return "Q"
		elif IconName == "48d":
			return "U"
		elif IconName == "49d":
			return "T"
		elif IconName == "50d":
			return "M"
		elif IconName == "01n":
			return "C"
		elif IconName == "02n":
			return "I"
		elif IconName == "03n":
			return "I"
		elif IconName == "04n":
			return "N"
		elif IconName == "05n":
			return "O"
		elif IconName == "06n":
			return "I"
		elif IconName == "07n":
			return "U"
		elif IconName == "08n":
			return "U"
		elif IconName == "09n":
			return "Q"
		elif IconName == "10n":
			return "U"
		elif IconName == "11n":
			return "I"
		elif IconName == "13n":
			return "U"
		elif IconName == "40n":
			return "Q"
		elif IconName == "41n":
			return "U"
		elif IconName == "sleet":
			return "W"
		elif IconName == "wind":
			return "F"
		elif IconName == "fog":
			return "M"
		elif IconName == "partly-cloudy-night":
			return "I"
		elif IconName == "cloudy":
			return "H"
		elif IconName == "clear-night":
			return "C"
		elif IconName == "clear-day":
			return "B"
		elif IconName == "partly-cloudy-day":
			return "H"
		elif IconName == "rain":
			return "X"
		elif IconName == "snow":
			return "W"
		else:
			return ")"


	def moonphase(self):
		picon = ''
		ptext = ''
# constants
		syn_moon_month = 29.530589 					# synodal length of moon cycle 
		hist_fullmoon = 2018,9,25,6,1,36,0,0,1 				# base full-moon as struct time 
		moon_time = mktime(hist_fullmoon) 				# base full-moon - seconds since epoch 
		hist_fullmoon_days = moon_time/86400 				# base full-moon - days since epoch 
		now_days = mktime(localtime())/86400 				# days since eval 
		days_since_hist_fullmoon = now_days - hist_fullmoon_days   	# difference in days between base fullmoon and now 
		full_moons_since = days_since_hist_fullmoon/syn_moon_month  	# Number of full-moons that have passed since base full-moon 
		phase = round(full_moons_since,2) 				# rounded to 2 digits 
		phase = (phase-int(phase))					# trailing rest = % moon-phase 
# calculate moon phase
		if phase == 0: phase = 1
		if phase < 0.25:
			ptext= _('Waning gibbous')
		elif phase == 0.25:
			ptext= _('First Quarter Moon')
		elif 0.25 < phase < 0.50:
			ptext= _('Waning crescent')
		elif phase == 0.50:
			ptext= _('New moon')
		elif 0.50 < phase < 0.75:
			ptext= _('Waxing crescent') 
		elif phase == 0.75:
			ptext= _('Waxing gibbous')
		elif 0.75 < phase < 0.98:
			ptext= _('Waxing gibbous') 
		elif 0.98 <= phase <= 1:
			ptext = _('Full moon')

		hmoonA = float(pi/2)                          			# area of unit circle/2
# calculate percentage of moon illuminated
		if phase < 0.5:
				s = cos(phase * pi * 2)
				ellipse = (s * 1 * pi)         	       		# Ellipsenfäche = Produkt der beiden Halbachsen * Pi 
				hEllA = (ellipse / 2)             	        # Ellipse Area/2 (major half axis * minor half axis * pi)/2
				illA = hmoonA + hEllA                   	# illuminated area of moon = Half moon area plus half Ellipse
		else:
				s = -cos(phase * pi *2)  	               	# minor half axis of ellipse
				ellipse = (s * 1 * pi)
				hEllA = (ellipse / 2)             	        # Ellipse Area/2 (major half axis * minor half axis)/2
				illA = hmoonA - hEllA                   	# illuminated area = Half moon area minus half Ellipse Area

		illumperc =  (illA / pi * 100)                   	 		# illuminated area relative to full moon area (based on unit circle r=1)	
		illumperc = round(illumperc,1)
			
		if phase > 0 and illumperc > 95:
			picon = "095" 
		if phase > 0.07 and illumperc > 90:
			picon = "090" 
		if phase > 0.10 and illumperc > 85:
			picon = "085" 
		if phase > 0.12 and illumperc > 80:
			picon = "080" 
		if phase > 0.14 and illumperc > 75:
			picon = "075" 
		if phase > 0.16 and illumperc > 70:
			picon = "070" 
		if phase > 0.18 and illumperc > 65:
			picon = "065" 
		if phase > 0.20 and illumperc > 60:
			picon = "060" 
		if phase > 0.21 and illumperc > 55:
			picon = "055" 
		if phase > 0.23 and illumperc > 50:
			picon = "050" 
		if phase > 0.24 and illumperc > 45:
			picon = "045" 
		if phase > 0.26 and illumperc > 40:
			picon = "040" 
		if phase > 0.28 and illumperc > 35:
			picon = "035" 
		if phase > 0.29 and illumperc > 30:
			picon = "030" 
		if phase > 0.31 and illumperc > 25:
			picon = "025" 
		if phase > 0.33 and illumperc > 20:
			picon = "020" 
		if phase > 0.35 and illumperc > 15:
			picon = "015" 
		if phase > 0.37 and illumperc > 10:
			picon = "010" 
		if phase > 0.39 and illumperc > 5:
			picon = "05" 
		if phase > 0.42 and illumperc >= 0:
			picon = "1" 
		if phase > 0.50 and illumperc > 0:
			picon = "5" 
		if phase > 0.57 and illumperc > 5:
			picon = "10" 
		if phase > 0.60 and illumperc > 10:
			picon = "15" 
		if phase > 0.62 and illumperc > 15:
			picon = "20" 
		if phase > 0.64 and illumperc > 20:
			picon = "25" 
		if phase > 0.66 and illumperc > 25:
			picon = "30" 
		if phase > 0.68 and illumperc > 30:
			picon = "35" 
		if phase > 0.70 and illumperc > 35:
			picon = "40" 
		if phase > 0.71 and illumperc > 40:
			picon = "45" 
		if phase > 0.73 and illumperc > 45:
			picon = "50" 
		if phase > 0.75 and illumperc > 50:
			picon = "55" 
		if phase > 0.76 and illumperc > 55:
			picon = "60" 
		if phase > 0.78 and illumperc > 60:
			picon = "65" 
		if phase > 0.79 and illumperc > 65:
			picon = "70" 
		if phase > 0.81 and illumperc > 70:
			picon = "75" 
		if phase > 0.83 and illumperc > 75:
			picon = "80" 
		if phase > 0.85 and illumperc > 80:
			picon = "85" 
		if phase > 0.87 and illumperc > 85:
			picon = "90" 
		if phase > 0.89 and illumperc > 90:
			picon = "95" 
		if phase > 0.92 and illumperc > 95:
			picon = "100"
		return ptext, picon


	def convertOWMIconName(self, IconName):
		if IconName == "01d":
			return "32"
		elif IconName == "02d":
			return "34"
		elif IconName == "03d":
			return "28"
		elif IconName == "04d":
			return "26"
		elif IconName == "05d":
			return "39"
		elif IconName == "06d":
			return "37"
		elif IconName == "07d":
			return "5"
		elif IconName == "08d":
			return "13"
		elif IconName == "09d":
			return "12"
		elif IconName == "10d":
			return "12"
		elif IconName == "11d":
			return "38"
		elif IconName == "12d":
			return "5"
		elif IconName == "13d":
			return "14"
		elif IconName == "14d":
			return "17"
		elif IconName == "15d":
			return "19"
		elif IconName == "20d":
			return "37"
		elif IconName == "21d":
			return "37"
		elif IconName == "22d":
			return "3"
		elif IconName == "23d":
			return "5"
		elif IconName == "30d":
			return "38"
		elif IconName == "31d":
			return "38"
		elif IconName == "32d":
			return "5"
		elif IconName == "33d":
			return "13"
		elif IconName == "34d":
			return "14"
		elif IconName == "40d":
			return "39"
		elif IconName == "46d":
			return "11"
		elif IconName == "47d":
			return "11"
		elif IconName == "48d":
			return "5"
		elif IconName == "49d":
			return "6"
		elif IconName == "50d":
			return "20"
		elif IconName == "01n":
			return "31"
		elif IconName == "02n":
			return "29"
		elif IconName == "03n":
			return "27"
		elif IconName == "04n":
			return "26"
		elif IconName == "05n":
			return "47"
		elif IconName == "06n":
			return "47"
		elif IconName == "07n":
			return "46"
		elif IconName == "08n":
			return "46"
		elif IconName == "09n":
			return "12"
		elif IconName == "10n":
			return "12"
		elif IconName == "11n":
			return "47"
		elif IconName == "13n":
			return "14"
		elif IconName == "40n":
			return "12"
		elif IconName == "41n":
			return "46"
		elif IconName == "50n":
			return "20"
		else:
			write_log("missing IconName : " + str(IconName))
			return "3200"


	def get_most_element(self, lst):
		return max(set(lst), key=lst.count)