import flask
import googlemaps
from flask import Flask, Response, request, render_template, redirect, url_for
from yelp.client import Client
from yelp.oauth1_authenticator import Oauth1Authenticator
import math
import urllib
import requests
import json
import numpy


# This client code can run on Python 2.x or 3.x.  Your imports can be
# simpler if you only need one of those.
try:
    # For Python 3.0 and later
    from urllib.error import HTTPError
    from urllib.parse import quote
    from urllib.parse import urlencode
except ImportError:
    # Fall back to Python 2's urllib2 and urllib
    from urllib2 import HTTPError
    from urllib import quote
    from urllib import urlencode

# Distances are measured in miles.
# Longitudes and latitudes are measured in degrees.
# Earth is assumed to be perfectly spherical.

earth_radius = 3960.0
degrees_to_radians = math.pi/180.0
radians_to_degrees = 180.0/math.pi

app = Flask(__name__)

gmaps = googlemaps.Client(key='AIzaSyALbYMcE_18JVpkD2jCDUhWpKJQGTedZBc')


#YELP
CLIENT_ID= 'ar5107laaWwnc1t4i5YECA'
CLIENT_SECRET='rbSXrUevS5vHFfdQoFCLYHD3JkcXRolfgzMj6WiNZLGS7fvHKYAyN62ES0se2YDq'

API_HOST = 'https://api.yelp.com'
SEARCH_PATH = '/v3/businesses/search'
BUSINESS_PATH = '/v3/businesses/'  # Business ID will come after slash.
TOKEN_PATH = '/oauth2/token'
GRANT_TYPE = 'client_credentials'


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/search",methods=["POST"])
def search():

	query = request.form.get('address') + " " + request.form.get('city') + " " + request.form.get('state') 
	geocode_result = gmaps.geocode(query)
	print(geocode_result)

	radius = float(request.form.get('radius'))
	# lat = geocode_result[0]['geometry']['location']['lat']
	# lng = geocode_result[0]['geometry']['location']['lng']
	yelpResults = search(obtain_bearer_token(API_HOST,SEARCH_PATH), query , radius)
	bns = []
	for b in yelpResults["businesses"]:
		if b["distance"] < radius * 1609:
			bns.append(b)
	if len(bns) > 0:
		
		stars = rate(bns, radius)
		st =''
		for s in stars:
			st += s[0] + ": " + str(s[1]) + "<br>" 
		return st + "<br>" 
	else:
		return str("No Results for given radius")


def rate(businesses, radius):
	quality = rateQuality(businesses)
	diversity = rateDiversity(businesses)
	num = rateNum(businesses, radius)
	price = ratePrice(businesses)
	accessibility = rateAccessibility(businesses, radius)
	return [["quality", quality], ["diversity", diversity], ["num", num], ["price", price],["accessibility", accessibility]]

def rateQuality(businesses):
	quality = 0 
	ratings = []
	total = len(businesses)
	for b in businesses:
		quality += b["rating"]
		ratings.append(b["rating"])
	return (quality/total) # average yelp rating 

def rateDiversity(businesses):
	types = []
	for b in businesses:
		for c in b["categories"]:
			if c["title"] not in types:
				types.append(c["title"])
	print(types)
	print(businesses)
	return len(types)/float(len(businesses))  


def rateNum(businesses, radius):
	total = len(businesses)
	area = math.pi * math.pow(radius, 2)
	return total/area 


def ratePrice(businesses):
	prices = 0
	for b in businesses:
		if  b["price"] == "$":
			prices += 1
		elif b["price"] == "$$":
			prices += 2
		elif b["price"] == "$$$":
			prices += 3
		elif b["price"] == "$$$$":
			prices += 4
	return prices/ float(len(businesses)) 

def rateAccessibility(businesses, radius):
	dist = 0
	for b in businesses:
		dist += b["distance"]/float(1609)
	return dist/len(businesses)


def change_in_latitude(miles):
    "Given a distance north, return the change in latitude."
    return (miles/earth_radius)*radians_to_degrees

def change_in_longitude(latitude, miles):
    "Given a latitude and a distance west, return the change in longitude."
    # Find the radius of a circle around the earth at given latitude.
    r = earth_radius*math.cos(latitude*degrees_to_radians)
    return (miles/r)*radians_to_degrees



def obtain_bearer_token(host, path):
    """Given a bearer token, send a GET request to the API.
    Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        url_params (dict): An optional set of query parameters in the request.
    Returns:
        str: OAuth bearer token, obtained using client_id and client_secret.
    Raises:
        HTTPError: An error occurs from the HTTP request.
    """
    url = 'https://api.yelp.com/oauth2/token'

    data = urlencode({
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': GRANT_TYPE,
    })
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }
    response = requests.request('POST', url, data=data, headers=headers)
    print(response.text)
    bearer_token = response.json()['access_token']
    return bearer_token

def requestYelp(host, path, bearer_token, url_params=None):
    """Given a bearer token, send a GET request to the API.
    Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        bearer_token (str): OAuth bearer token, obtained using client_id and client_secret.
        url_params (dict): An optional set of query parameters in the request.
    Returns:
        dict: The JSON response from the request.
    Raises:
        HTTPError: An error occurs from the HTTP request.
    """
    url_params = url_params or {}
    print(url_params)
    url = '{0}{1}'.format(host, quote(path.encode('utf8')))
    headers = {
        'Authorization': 'Bearer %s' % bearer_token,
    }

    print(u'Querying {0} ...'.format(url))

    response = requests.request('GET', url, headers=headers, params=url_params)

    return response.json()


def search(bearer_token, location, radius):
    """Query the Search API by a search term and location.
    Args:
        term (str): The search term passed to the API.
        location (str): The search location passed to the API.
    Returns:
        dict: The JSON response from the request.
    """

    url_params = {
        'term': 'food',
        'location': location.replace(' ', '+'),
        'radius' : int(radius) * 1609

    }
    return requestYelp(API_HOST, SEARCH_PATH, bearer_token, url_params=url_params)