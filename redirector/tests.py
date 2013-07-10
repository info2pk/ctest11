from django.test import TestCase
from django.contrib.sites.models import Site

from .models import Redirect
from .middleware import RedirectMiddleware

# Mock get_absolute_url method
setattr(Site, 'get_absolute_url', lambda site: 'http://example.com/')


class MockRequest(object):
    def __init__(self, path):
        self.path = path

    def get_full_path(self):
        return self.path


class MockResponse(object):
    def __init__(self, status_code=200):
        self.status_code = status_code


class RedirectTest(TestCase):
    """
    Redirector tests to test isolated functionality of middleware
    """
    def setUp(self):
        self.middleware = RedirectMiddleware()
        self.site = Site.objects.get_current()
        self.basic_redirect = Redirect.objects.create(site=self.site, from_url='/a', to_url='/b/')
        self.object_redirect = Redirect.objects.create(site=self.site, from_url='/site/', content_object=self.site)
        self.bad_redirect = Redirect.objects.create(site=self.site, from_url='/bad/')

    def test_no_op(self):
        mock_response = MockResponse()
        response = self.middleware.process_response(MockRequest('/content/'), mock_response)
        self.assertEqual(mock_response, response)

    def test_basic_redirect(self):
        response = self.middleware.process_response(MockRequest('/a'), MockResponse(404))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['location'], '/b/')

    def test_query_redirect(self):
        response = self.middleware.process_response(MockRequest('/a?foo=bar'), MockResponse(404))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['location'], '/b/?foo=bar')

    def test_slash_redirect(self):
        response = self.middleware.process_response(MockRequest('/a/'), MockResponse(404))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['location'], '/b/')

    def test_object_redirect(self):
        response = self.middleware.process_response(MockRequest('/site/'), MockResponse(404))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['location'], 'http://example.com/')

    def test_bad_redirect(self):
        response = self.middleware.process_response(MockRequest('/bad/'), MockResponse(404))
        self.assertEqual(response.status_code, 410)

