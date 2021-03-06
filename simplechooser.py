from StringIO import StringIO
import sys

import cherrypy
import cherrypy._cperror as cperror
import lxml.etree 

import support
import cgi

class SimpleChooser(object):

    def __init__(self):
        pass

    @cherrypy.expose
    def chooser(self, jurisdiction='-', exclude=[], locale='en', language=None,
                select=None, version=None, **kwargs):

        # backward compatibility for the language parameter
        if language is None:
            language = locale
            
        # determine our actual functional locale
        language = support.actualLocale(language)
        
        # make sure exclude is a list
        try:
            exclude.append(None)
            del exclude[-1]
        except AttributeError:
            exclude = [exclude]

        # check if we should include the <select> element
        if select:
            yield('<select name="%s">\n' % select)
            
        # just delegate to the chooser generator
        licenses = self.__getLicenses(
            jurisdiction = support.actualJurisdiction(jurisdiction),
            language = language, exclude=exclude, version=version)

        for l in licenses:
            yield('<option value="%s">%s</option>\n' % (l[0], cgi.escape(l[1])))

        if select:
            yield('</select>')
            

    @cherrypy.expose
    def chooser_js(self, jurisdiction='-', exclude=[], locale='en',
                   language=None, select=None, **kwargs):

        # set the content type
        cherrypy.response.headers['Content-Type'] = 'text/javascript'

        # delegate to the basic method
        for line in self.chooser(jurisdiction, exclude,
                                 locale, language, select):
            yield("document.write('%s');\n" % line.strip())

    def __getLicenses(self, jurisdiction='', exclude=[], language='en',
                      version=None):
        """Return a list of license (uri, name) tuples for a particular 
        jurisdiction, language, etc."""

        # load the licenses file
        all_licenses = lxml.etree.parse(support.LICENSES_XML)

        # determine the current version of licenses for the jurisdiction
        # note this assumes that a jurisdiction's licenses are revved as a group
        juris_versions = all_licenses.xpath(
            '//licenseclass[@id="standard"]/license/jurisdiction[@id="%s"]/'
            'version/@id' % jurisdiction)

        if version is not None:
            # a particular version was requested; make sure this is a valid
            # version for this jurisdiction
            if str(version).strip() in juris_versions:
                curr_version = str(version).strip()
        else:
            curr_version = max(juris_versions)

        # get the list of licenses for the specified domain
        domain_licenses = all_licenses.xpath(
            '//licenseclass[@id="standard"]/license/jurisdiction[@id="%s"]/'
            'version[@id="%s"]/@uri' % (jurisdiction, curr_version)) + \
            all_licenses.xpath(
            '//licenseclass[@id="publicdomain"]/license/jurisdiction[@id="-"]/'
            'version[@id="-"]/@uri')

        # get the latest version of each license found
        licenses = []
        for l in domain_licenses:

            details = lxml.etree.fromstring(
                support.license_details(l, language))

            l_uri = details.xpath('//license-uri')[0].text
            l_name = details.xpath('//license-name')[0].text

            # check if this URI should be excluded
            exclusions = [n for n in exclude if l_uri.find(n) > -1]
            if len(exclusions) == 0:
                licenses.append( (l_uri, l_name) )

        # sort the license list
        licenses.sort(key=lambda x: x[0].split('/')[x[0].split('/').index('licenses') + 1],)

        # return a sequence of two-tuples: (uri, name)
        return licenses

if __name__ == '__main__':

    cherrypy.root = SimpleChooser()
    cherrypy.config.update(file='rest_api.cfg')

    cherrypy.server.start()
