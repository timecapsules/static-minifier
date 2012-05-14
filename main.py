#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import urlfetch
from google.appengine.api import memcache



import css
import js

SERVER = "http://timecapsules-live.appspot.com/"

STATIC_ROOT = "static/"


def build_url(filename, filetype):
	return SERVER + STATIC_ROOT + filetype + "/" + filename


def get_minified(filename, filetype):
	# make the full url of the resource
	url = build_url(filename, filetype)
	# check if we have in memcache
	minified = memcache.get(url)
	if not minified:
		# not in memcache, so get the original
		result = urlfetch.fetch(url)
		if result.status_code == 200:
			# successful request, now choose which minifier to use
			if filetype == "css":
  				minifiedstr = css.minify(result.content)
  			elif filetype == "js":
  				minifiedstr = js.minify(result.content)
  			# and store a dict of the minified string, filetype and the etag of the original file	
  			minified = {
  				"content":minifiedstr,
  				"type":filetype,
  				"etag":result.headers["etag"].replace("\"", "")
  			}
  			# then cache the dictionary in memcache for 60 minutes
			memcache.add(url, minified, 3600)
  		# return the status code we got from urlfetch
  		status_code = result.status_code
  	else:
  		# this is the file from the cache so the status code is always 200
  		status_code = 200
  	return minified, status_code




class MinifyHandler(webapp.RequestHandler):
    def get(self, filetype, filename):
		status_code = 404
		minified, status_code = get_minified(filename, filetype)
		logging.warn(minified)
		logging.warn(status_code)
		if minified:
			logging.warn("WE HAVE A MINIFIED " + filetype)
			if "If-None-Match" in self.request.headers:
				logging.warn("GOT A IF NONE MATCH")
				if minified["etag"] in self.request.headers["If-None-Match"]:
					logging.warn(self.request.headers["If-None-Match"])
					logging.warn("MATCHING ETAG 304")
					status_code = 304
				else:
					status_code = 200
			else:
				status_code = 200
		if status_code == 200:
			if filetype == "css":
				self.response.headers['Content-Type'] = 'text/css'  				
			elif filetype == "js":
				self.response.headers['Content-Type'] = 'text/javascript'  				
  			self.response.headers['Cache-Control'] = "public, max-age=86400"
  			self.response.headers['ETag'] = '"%s"' % (minified["etag"],)
  			self.response.out.write(minified["content"])
  		else:
  			if status_code == 304:
  				self.response.headers['ETag'] = '"%s"' % (minified["etag"],)
			logging.warn("SETTING STATUS AS " + str(status_code))
  			self.response.set_status(status_code)







def main():
    application = webapp.WSGIApplication([
		('/static/(js)/(.*)', MinifyHandler),
		('/static/(css)/(.*)', MinifyHandler)
	], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
