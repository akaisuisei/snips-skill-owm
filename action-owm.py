#!/usr/bin/env python2
# -*-: coding utf-8 -*-

from concierge_python.concierge import Concierge
import ConfigParser
from datetime import datetime
import datetime as dt
from dateutil.parser import parse
from hermes_python.hermes import Hermes
import hermes_python
import io
import os
from snipsowm.snipsowm import SnipsOWM
import threading
import unicodedata

CONFIGURATION_ENCODING_FORMAT = "utf-8"
CONFIG_INI = "config.ini"

MQTT_IP_ADDR = "localhost"
MQTT_PORT = 1883
MQTT_ADDR = "{}:{}".format(MQTT_IP_ADDR, str(MQTT_PORT))

DIR = os.path.dirname(os.path.realpath(__file__)) + '/alarm/'
_id = "snips-skill-owm"
alive = 0;
lang = "EN"

client = None
pingTopic = 'concierge/apps/live/ping'
pongTopic = 'concierge/apps/live/pong'
c = Concierge(MQTT_IP_ADDR)

def on_ping(client):
    if (alive > 0):
        c.publishPong(_id)

def on_view(client):
    pass

def setTimer():
    global alive
    alive += 1
    t = threading.Timer(300, runTimer)
    t.start()

def runTimer():
    global alive
    alive -= 1

class SnipsConfigParser(ConfigParser.SafeConfigParser):
    def to_dict(self):
        return {section: {option_name : option for option_name, option in self.items(section)} for section in self.sections()}

def read_configuration_file(configuration_file):
    try:
        with io.open(configuration_file, encoding=CONFIGURATION_ENCODING_FORMAT) as f:
            conf_parser = SnipsConfigParser()
            conf_parser.readfp(f)
            return conf_parser.to_dict()
    except (IOError, ConfigParser.Error) as e:
        return dict()

def to_unicode(val):
    res = unicodedata.normalize('NFKD', val.decode('utf-8'))
    return unicode(res.encode('ascii', 'ignore'))

def getCondition(snips):
      # Determine condition
    if snips.slots.forecast_condition_name:
        res = snips.slots.forecast_condition_name[0].slot_value.value.value
        return to_unicode(res)
    return None

def getLocality(snips):
    if snips.slots.forecast_locality:
        res = snips.slots.forecast_locality[0].slot_value.value.value
        return to_unicode(res)
    return None

def getRegion(snips):
    if snips.slots.forecast_region:
        res = snips.slots.forecast_region[0].slot_value.value.value
        return to_unicode(res)
    return None

def getCountry(snips):
    if snips.slots.forecast_country :
        res = snips.slots.forecast_country[0].slot_value.value.value
        return to_unicode(res)
    return None

def getPOI(snips):
    if snips.slots.forecast_geographical_poi:
        res = snips.slots.forecast_geographical_poi[0].slot_value.value.value
        return to_unicode(res)
    return None

def getItemName(snips):
    if snips.slots.forecast_item:
        res = snips.slots.forecast_item[0].slot_value.value.value
        return to_unicode(res)
    return None

def getDateTime(snips):
    # Determine datetime
    if snips.slots.forecast_start_datetime:
        tmp = snips.slots.forecast_start_datetime[0].slot_value.value
        if tmp is None:
            return None
        if isinstance(tmp, hermes_python.ontology.InstantTimeValue ):
            val = tmp.value[:-7]
            return datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
        elif isinstance(tmp, hermes_python.ontology.TimeIntervalValue ):
            t0 = tmp.from_date[:-7]
            t0 = datetime.strptime(t0, '%Y-%m-%d %H:%M:%S')
            t1 = tmp.to_date[:-7]
            t1 = datetime.strptime(t1, '%Y-%m-%d %H:%M:%S')
            delta = t1 - t0
            return t0 + delta / 2
    return None

def getAnyLocality(snips):
    locality = None
    try:
        locality = snips.slots.forecast_locality \
            or snips.slots.forecast_country \
            or snips.slots.forecast_region \
            or snips.slots.forecast_geographical_poi

        if locality:
            res = (locality[0].slot_value.value.value)
            return to_unicode(res)
    except Exception:
        return None

def getGranurality(datetime):
      # Determine granularity
      if datetime:  # We have an information about the date.
        now = dt.datetime.now().replace(tzinfo=None)
        delta_days = abs((datetime - now).days)
        if delta_days > 10: # There a week difference between today and the date we want the forecast.
            return 2 # Give the day of the forecast date, plus the number of the day in the month.
        elif delta_days > 5: # There a 10-day difference between today and the date we want the forecast.
          return 1 # Give the full date
        else:
          return 0 # Just give the day of the week
      else:
        return 0

def searchWeatherForecastTemperature(hermes, intent_message):
    setTimer()
    datetime = getDateTime(intent_message)
    granularity = getGranurality(datetime)
    locality = getAnyLocality(intent_message)
    res, led = hermes.skill.speak_temperature(locality, datetime, granularity)
    current_session_id = intent_message.session_id
    hermes.publish_end_session(current_session_id, res)
    c.publishWeather(led[0], led[1], intent_message.site_id)
    print(res)

def searchWeatherForecastCondition(hermes, intent_message):
    setTimer()
    datetime = getDateTime(intent_message)
    granularity = getGranurality(datetime)
    condition = getCondition(intent_message)
    locality = getLocality(intent_message)
    region = getRegion(intent_message)
    country = getCountry(intent_message)
    geographical_poi = getPOI(intent_message)
    res, led = hermes.skill.speak_condition(condition, datetime,
                               granularity=granularity, Locality=locality,
                               Region=region, Country=country,
                               POI=geographical_poi)
    current_session_id = intent_message.session_id
    hermes.publish_end_session(current_session_id, res)
    c.publishWeather(led[0], led[1], intent_message.site_id)
    print(res)

def searchWeatherForecast(hermes, intent_message):
    setTimer()
    datetime = getDateTime(intent_message)
    granularity = getGranurality(datetime)
    # No condition in this intent so initialized to None
    condition_name = None
    locality = getLocality(intent_message)
    region = getRegion(intent_message)
    country = getCountry(intent_message)
    geographical_poi = getPOI(intent_message)
    res, led = hermes.skill.speak_condition(condition_name, datetime,
                               granularity=granularity, Locality=locality,
                               Region=region, Country=country,
                               POI=geographical_poi)
    current_session_id = intent_message.session_id
    hermes.publish_end_session(current_session_id, res)
    c.publishWeather(led[0], led[1], intent_message.site_id)
    print(res)

def searchWeatherForecastItem(hermes, intent_message):
    setTimer()
    datetime = getDateTime(intent_message)
    granularity = getGranurality(datetime)
    item_name = getItemName(intent_message)
    locality = getLocality(intent_message)
    region = getRegion(intent_message)
    country = getCountry(intent_message)
    geographical_poi = getPOI(intent_message)
    res, led = hermes.skill.speak_item(item_name,
                                  datetime,
                                  granularity=granularity,
                                 Locality=locality,
                                 Region=region,
                                 Country=country,
                                 POI=geographical_poi)
    current_session_id = intent_message.session_id
    hermes.publish_end_session(current_session_id, res)

    send_to_led(led)
    c.publishWeather(led[0], led[1], intent_message.site_id)
    print(res)

if __name__ == "__main__":
    c.subscribePing(on_ping)
    c.subscribeView(_id, on_view)
    config = read_configuration_file("config.ini")

    if config.get("secret").get("api_key") is None:
        print "No API key in config.ini, you must setup an OpenWeatherMap API key for this skill to work"
    elif len(config.get("secret").get("api_key")) == 0:
        print "No API key in config.ini, you must setup an OpenWeatherMap API key for this skill to work"

    skill_locale = config["global"].get("locale", "en_US")

    skill = SnipsOWM(config["secret"]["api_key"],
                     config["secret"]["default_location"],locale=skill_locale)
    lang = "EN"
    with Hermes(MQTT_ADDR) as h:
        h.skill = skill
        h.subscribe_intent("searchWeatherForecastItem",
                           searchWeatherForecastItem) \
        .subscribe_intent("searchWeatherForecastTemperature",
                          searchWeatherForecastTemperature) \
        .subscribe_intent("searchWeatherForecastCondition",
                          searchWeatherForecastCondition) \
        .subscribe_intent("searchWeatherForecast", searchWeatherForecast) \
        .loop_forever()
