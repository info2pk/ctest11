from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from .models import Redirect
from .middleware import RedirectMiddleware

# Mock get_absolute_url method
setattr(Site, 'get_absolute_url', lambda site: 'http://example.com/')
setattr(User, 'get_absolute_url', lambda user: '/users/mockuser/')


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
        self.mock_user = User.objects.create(username='test_user',
                                            first_name='test_user',
                                            last_name='test_user',
                                            email='test@test.com')
        self.user_redirect = Redirect.objects.create(site=self.site,
                                                    from_url='/usertest/',
                                                    content_object=self.mock_user)

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

    def test_deleted_object_redirect(self):
        # Make sure that the redirect works correctly the first time
        response = self.middleware.process_response(MockRequest('/usertest/'),
                                                    MockResponse(301))
        self.assertEqual(response.status_code, 301)
        self.mock_user.delete()
        # Test that the redirect is Gone
        response = self.middleware.process_response(MockRequest('/usertest/'),
                                                    MockResponse(410))
        self.assertEqual(response.status_code, 410)

    def test_url_redirect_unicode(self):
        self.assertEqual(unicode(self.basic_redirect), u'/a ---> /b/')

    def test_object_redirect_unicode(self):
        self.assertEqual(unicode(self.user_redirect), u'/usertest/ ---> /users/mockuser/')

    def test_object_deleted_redirect_unicode(self):
        self.mock_user.delete()
        self.assertEqual(unicode(self.user_redirect), u'/usertest/ ---> None')
