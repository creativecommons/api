"""
Creative Commons Web Services Test Harness
Copyright (c) 2005-2006,
     Nathan R. Yergler, 
     Creative Commons (software@creativecommons.org)

Based on test code from the CherryPy Project, 
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

See docs/LICENSE for redistribution restrictions.

"""

import os
import sys
import unittest
import operator
from StringIO import StringIO
import random

# fix up the PYTHON PATH to include the directory we're running from
sys.path.insert(0, os.getcwd())

from rest_api import *

cherrypy.config.update({
    'global': {
        'server.logToScreen': False,
        'server.environment': "production",
    }
})

RELAX_PATH = './relax'
QUESTIONS_XML = (os.path.join('license_xsl', 'questions.xml'),
                 'questions.relax.xml')
LICENSES_XML = (os.path.join('license_xsl', 'licenses.xml'),
                'licenses.relax.xml')

import cherrypy.test.helper as helper

def RelaxValidate(schemaFileName, instanceFile): #PORTED

    relaxng = lxml.etree.RelaxNG(lxml.etree.parse(schemaFileName))
    instance = lxml.etree.parse(instanceFile)

    if not(relaxng.validate(instance)):
        print relaxng.error_log.last_error
        return False
    else:
        return True

def permute(Lists): #PORTED
    if Lists:
        result = map(lambda I: (I,), Lists[0])
    
        for list in Lists[1:]:
            curr = []
            for item in list:
                new = map(operator.add, result, [(item,)]*len(result))
                curr[len(curr):] = new
            result = curr
    else:
        result = []
  
    return result

class TestXmlFiles(unittest.TestCase):

    def testQuestionsXml(self): #PORTED
        """Make sure questions.xml is compliant."""
        self.assert_(RelaxValidate(os.path.join(RELAX_PATH, QUESTIONS_XML[1]), 
                                   QUESTIONS_XML[0]),
                    "questions.xml does not comply to the Relax-NG schema.")

    def testLicensesXml(self): #PORTED
        """Make sure licenses.xml is compliant."""
        self.assert_(RelaxValidate(os.path.join(RELAX_PATH, LICENSES_XML[1]), 
                                   LICENSES_XML[0]),
                    "licenses.xml does not comply to the Relax-NG schema.")
                    

class CcApiTest(helper.CPWebCase):
    def testLocales(self): #PORTED
        """Test that /locales returns a list of supported languages."""
        self.getPage('/locales')

        assert RelaxValidate(os.path.join(RELAX_PATH,
                                          'locales.relax.xml'),
                             StringIO(self.body))

    def testLocalesExtraArgs(self): #PORTED
        """Test the /locales method with extra non-sense arguments;
        extra arguments should be ignored."""

        self.getPage('/locales?foo=bar')

        assert RelaxValidate(os.path.join(RELAX_PATH,
                                          'locales.relax.xml'),
                             StringIO(self.body))
        
        self.getPage('/locales?lang=en_US&blarf=%s' % hash(self))

        assert RelaxValidate(os.path.join(RELAX_PATH,
                                          'locales.relax.xml'),
                             StringIO(self.body))

    def testClasses(self): #PORTED
        """Test that /classes and / are synonyms."""
        self.getPage('/')
        root_body = self.body
        
        self.getPage('/classes')
        classes_body = self.body

        assert root_body == classes_body

    def testInvalidClass(self): #PORTED
        """An invalid license class name should return an explicit error."""
        
        self.getPage('/license/noclass')

        assert RelaxValidate(os.path.join(RELAX_PATH,
                                          'error.relax.xml'),
                             StringIO(self.body))

    def testClassesStructure(self): #PORTED
        """Test the return value of /classes to ensure it fits with our
        claims."""
        self.getPage('/classes')

        assert RelaxValidate(os.path.join(RELAX_PATH, 'classes.relax.xml'),
                             StringIO(self.body))

    def __getLocales(self): #PORTED
        """Return a list of supported locales."""

        self.getPage('/locales')

        locale_doc = lxml.etree.parse(StringIO(self.body))
        return [n for n in locale_doc.xpath('//locale/@id') if n not in ('he',)]
    
    def __getLicenseClasses(self): #PORTED
        """Get the license classes."""
        self.getPage('/classes')

        classes = []
        classdoc = lxml.etree.parse(StringIO(self.body))
        for license in classdoc.xpath('//license/@id'):
            classes.append(license)

        return classes

    def __fieldEnums(self, lclass): #PORTED
        """Retrieve the license information for this class, and generate
        a set of answers for use with testing."""


        self.getPage('/license/%s' % lclass)

        all_answers = []
        classdoc = lxml.etree.parse(StringIO(self.body))

        for field in classdoc.xpath('//field'):
            field_id = field.get('id')
            
            answer_values = []
            for e in field.xpath('./enum'):
                answer_values.append(e.get('id'))

            all_answers.append((field_id, answer_values))

        return all_answers

    def __testAnswersXml(self, lclass): #PORTED

        all_answers = self.__fieldEnums(lclass)
        all_locales = self.__getLocales()

        for answer_comb in permute([n[1] for n in all_answers]):

            for locale in all_locales:
                answers_xml = lxml.etree.Element('answers')
                locale_node = lxml.etree.SubElement(answers_xml, 'locale')
                locale_node.text = locale
                
                class_node = lxml.etree.SubElement(answers_xml, 'license-%s' % lclass)


                for a in zip([n[0] for n in all_answers], answer_comb):
                    a_node = lxml.etree.SubElement(class_node, a[0])
                    a_node.text = a[1]

                yield lxml.etree.tostring(answers_xml)

    def __testAnswerQueryStrings(self, lclass): #PORTED

        all_answers = self.__fieldEnums(lclass)
        all_locales = self.__getLocales()
        
        for answer_comb in permute([n[1] for n in all_answers]):

            for locale in all_locales:
                
                params = zip([n[0] for n in all_answers], answer_comb)
                param_strs = ["=".join(n) for n in params]

                # append each locale in turn
                param_strs.append('locale=%s' % locale)

                # generate the query string
                result = "?" + "&".join(param_strs)

                # yield each
                yield result
        
    def testLicenseClassStructure(self): #PORTED
        """Test that each license class returns a valid XML chunk."""

        for lclass in self.__getLicenseClasses():
            self.getPage('/license/%s' % lclass)

            try:
                assert RelaxValidate(os.path.join(RELAX_PATH, 
                                              'licenseclass.relax.xml'),
                                 StringIO(self.body))
            except AssertionError:
                print self.body
                print "Returned value for %s does not comply with " \
                      "RelaxNG schema." % lclass
                raise AssertionError
                    
    def testIssue(self): #PORTED
        """Test that every license class will be successfully issued via
        the /issue method."""

        for lclass in self.__getLicenseClasses():

            for answers in self.__testAnswersXml(lclass):
              print >> sys.stderr, '*',
              try:
                
                self.getPage('/license/%s/issue?answers=%s' %
                             (lclass, answers))
              
                assert RelaxValidate(os.path.join(RELAX_PATH, 
                                               'issue.relax.xml'),
                                     StringIO(self.body))

              except AssertionError:
                print "Issue license failed for:\nlicense class: %s\n" \
                      "answers: %s\n" % (lclass, answers)

                raise AssertionError

    def testGet(self): #PORTED
        """Test that every license class will be successfully issued
        via the /get method."""

        for lclass in self.__getLicenseClasses():

            for queryString in self.__testAnswerQueryStrings(lclass):
                print >> sys.stderr, '-',
                try:
                    
                    self.getPage('/license/%s/get%s' % (lclass, queryString))
      
                    assert RelaxValidate(os.path.join(RELAX_PATH, 'issue.relax.xml'),
                                         StringIO(self.body))
    
                except AssertionError:
                    print "Get license failed for:\nlicense class: %s\n" \
                          "answers: %s\n" % (lclass, queryString)
      
                    raise AssertionError
                except Exception, e:
                    print "Get license failed with an exception for:\nlicense class: %s\n" \
                          "answers: %s\n" % (lclass, queryString)
      
                    raise e

    def testGetExtraArgs(self): #PORTED
        """Test the /get method with extra non-sense arguments; extra
        arguments should be ignored."""


        for lclass in self.__getLicenseClasses():

            for queryString in self.__testAnswerQueryStrings(lclass):
              print >> sys.stderr, '-',
              try:
                
                self.getPage('/license/%s/get%s&foo=bar' % (lclass, queryString))

                assert RelaxValidate(os.path.join(RELAX_PATH, 
                                               'issue.relax.xml'),
                                     StringIO(self.body))

              except AssertionError:
                print "Get license failed for:\nlicense class: %s\n" \
                      "answers: %s\n" % (lclass, queryString)

                raise AssertionError

        
    def testIssueError(self): #PORTED
        """Issue with no answers or empty answers should return an error."""

        for lclass in self.__getLicenseClasses():
            self.getPage('/license/%s/issue' % lclass)

            assert RelaxValidate(os.path.join(RELAX_PATH,
                                              'error.relax.xml'),
                                 StringIO(self.body))

    def testIssueInvalidClass(self): #PORTED
        """/issue should return an error with an invalid class."""

        self.getPage('/license/blarf/issue?answers=<foo/>')

        assert RelaxValidate(os.path.join(RELAX_PATH, 'error.relax.xml'),
                             StringIO(self.body))

    def testGetInvalidClass(self): #PORTED
        """/get should return an error with an invalid class."""

        self.getPage('/license/%s/get' % hash(self))

        assert RelaxValidate(os.path.join(RELAX_PATH, 'error.relax.xml'),
                             StringIO(self.body))

    def testI18n(self): #NOTED on todo list
        """Make sure i18n calls work right."""

    def testLicenseDetails(self): #PORTED
        """Test that the license details call responds appropriately."""

        # test valid URIs
        TEST_URIS = ('http://creativecommons.org/licenses/by-nc-nd/2.5/',
                     'http://creativecommons.org/licenses/by-nc-sa/2.5/',
                     'http://creativecommons.org/licenses/by-sa/2.5/',
                     'http://creativecommons.org/licenses/by/2.0/nl/',
                    )

        for uri in TEST_URIS:
            self.getPage('/details?license-uri=%s' % uri)

            try:              
                assert RelaxValidate(os.path.join(RELAX_PATH, 
                                               'issue.relax.xml'),
                                     StringIO(self.body))

            except AssertionError:
                print "License details failed for the URI %s" % uri
                raise AssertionError

        # test that an invalid URI raises an error
        uri = "http://creativecommons.org/licenses/blarf"
        self.getPage('/details?license-uri=%s' % uri)

        assert RelaxValidate(os.path.join(RELAX_PATH,
                                          'error.relax.xml'),
                             StringIO(self.body))

    def testDetailsError(self): #PORTED
        """A call to /details with no license-uri should return a
        missingparam error."""

        self.getPage('/details')

        assert RelaxValidate(os.path.join(RELAX_PATH,
                                          'error.relax.xml'),
                             StringIO(self.body))

def runTests():

    cherrypy.tree.mount(RestApi())
    cherrypy.tree.mount(simplechooser.SimpleChooser(), "/simple")
    cherrypy.tree.mount(supportapi.SupportApi(), "/support")
    
    helper.testmain()
    
if __name__ == "__main__":
    runTests()
    
