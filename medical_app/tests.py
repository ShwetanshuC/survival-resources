import json
import requests as req_lib
from django.test import TestCase, LiveServerTestCase
from unittest.mock import patch


class SearchMedicalViewTests(TestCase):

    @patch('medical_app.views.execute_overpass_query')
    def test_returns_elements_on_success(self, mock_query):
        mock_query.return_value = [
            {'type': 'node', 'id': 1, 'lat': 34.22, 'lon': -77.94, 'tags': {'name': 'City Hospital'}}
        ]
        response = self.client.get('/api/medical/', {'lat': '34.22', 'lon': '-77.94', 'radius': '2000'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('elements', data)
        self.assertEqual(len(data['elements']), 1)

    @patch('medical_app.views.execute_overpass_query')
    def test_normalizes_way_center_coordinates(self, mock_query):
        """Ways returned by 'out center' have center.lat/lon — must be lifted to top-level."""
        mock_query.return_value = [
            {'type': 'way', 'id': 2, 'center': {'lat': 34.22, 'lon': -77.94}, 'tags': {'name': 'Regional Medical Center'}}
        ]
        response = self.client.get('/api/medical/', {'lat': '34.22', 'lon': '-77.94', 'radius': '2000'})
        self.assertEqual(response.status_code, 200)
        elements = response.json()['elements']
        self.assertEqual(len(elements), 1)
        self.assertIn('lat', elements[0])
        self.assertIn('lon', elements[0])
        self.assertEqual(elements[0]['lat'], 34.22)

    @patch('medical_app.views.execute_overpass_query')
    def test_returns_empty_list_when_no_results(self, mock_query):
        mock_query.return_value = []
        response = self.client.get('/api/medical/', {'lat': '34.22', 'lon': '-77.94'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['elements'], [])

    @patch('medical_app.views.execute_overpass_query')
    def test_defaults_radius_on_invalid_input(self, mock_query):
        mock_query.return_value = []
        response = self.client.get('/api/medical/', {'lat': '34.22', 'lon': '-77.94', 'radius': 'bad'})
        self.assertEqual(response.status_code, 200)
        # Verify the raw=True flag was used (query must start with [out:json])
        call_args = mock_query.call_args
        self.assertTrue(call_args[0][0].startswith('[out:json]'))
        self.assertTrue(call_args[1].get('raw') or call_args[0][1] is True)

    @patch('medical_app.views.execute_overpass_query')
    def test_500_on_overpass_failure(self, mock_query):
        mock_query.side_effect = RuntimeError("Overpass API error 429")
        response = self.client.get('/api/medical/', {'lat': '34.22', 'lon': '-77.94'})
        self.assertEqual(response.status_code, 500)
        self.assertIn('error', response.json())

    @patch('medical_app.views.execute_overpass_query')
    def test_query_uses_raw_overpassql(self, mock_query):
        """Verify the view sends a union query with nwr and no regex."""
        mock_query.return_value = []
        self.client.get('/api/medical/', {'lat': '34.22', 'lon': '-77.94', 'radius': '5000'})
        query = mock_query.call_args[0][0]
        self.assertIn('nwr[amenity=hospital]', query)
        self.assertIn('nwr[healthcare=hospital]', query)
        self.assertIn('out center qt', query)
        self.assertNotIn('Regex', query)

    def test_events_endpoint_returns_elements_key(self):
        """Events endpoint must always return {'elements': [...]} even when scraper fails."""
        response = self.client.get('/api/medical/events/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('elements', response.json())


class MedicalLiveServerTests(LiveServerTestCase):
    """Integration tests that spin up a real HTTP server and hit it with requests.
    These catch issues that the Django test client masks: JSON parse failures,
    routing gaps, static-file regressions, and real response content-type."""

    @patch('medical_app.views.execute_overpass_query')
    def test_api_returns_valid_json_content_type(self, mock_query):
        """Real HTTP GET must return application/json, not HTML (e.g. a 404 page)."""
        mock_query.return_value = []
        r = req_lib.get(
            f'{self.live_server_url}/api/medical/',
            params={'lat': '34.22', 'lon': '-77.94', 'radius': '2000'},
            timeout=10,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/json', r.headers.get('Content-Type', ''))
        data = r.json()   # raises if body is HTML, catching the old cache-break bug
        self.assertIn('elements', data)

    @patch('medical_app.views.execute_overpass_query')
    def test_api_old_endpoint_gone(self, mock_query):
        """The removed /api/search_resources/ endpoint must return 404 — not silently
        re-appear — so we catch any accidental re-registration."""
        mock_query.return_value = []
        r = req_lib.get(
            f'{self.live_server_url}/api/search_resources/',
            params={'category': 'medical', 'lat': '34.22', 'lon': '-77.94'},
            timeout=5,
        )
        self.assertEqual(r.status_code, 404)

    def test_events_endpoint_live(self):
        """Events endpoint must return valid JSON even via real HTTP."""
        r = req_lib.get(f'{self.live_server_url}/api/medical/events/', timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/json', r.headers.get('Content-Type', ''))
        data = r.json()
        self.assertIn('elements', data)
