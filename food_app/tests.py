import requests as req_lib
from django.test import TestCase, LiveServerTestCase
from unittest.mock import patch


class SearchFoodViewTests(TestCase):

    @patch('food_app.views.execute_overpass_query')
    def test_returns_elements_on_success(self, mock_query):
        mock_query.return_value = [{'type': 'node', 'id': 1, 'lat': 40.7, 'lon': -74.0, 'tags': {'name': 'Test Food Bank'}}]
        response = self.client.get('/api/food/', {'lat': '40.7', 'lon': '-74.0', 'radius': '2000'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('elements', data)
        self.assertEqual(len(data['elements']), 1)

    @patch('food_app.views.execute_overpass_query')
    def test_normalizes_way_center_coordinates(self, mock_query):
        """Ways returned by 'out center' have center.lat/lon — must be lifted to top-level."""
        mock_query.return_value = [
            {'type': 'way', 'id': 2, 'center': {'lat': 40.7, 'lon': -74.0}, 'tags': {'name': 'Food Pantry Building'}}
        ]
        response = self.client.get('/api/food/', {'lat': '40.7', 'lon': '-74.0', 'radius': '2000'})
        self.assertEqual(response.status_code, 200)
        elements = response.json()['elements']
        self.assertEqual(len(elements), 1)
        self.assertIn('lat', elements[0])
        self.assertIn('lon', elements[0])
        self.assertEqual(elements[0]['lat'], 40.7)

    @patch('food_app.views.execute_overpass_query')
    def test_returns_empty_list_when_no_results(self, mock_query):
        mock_query.return_value = []
        response = self.client.get('/api/food/', {'lat': '40.7', 'lon': '-74.0', 'radius': '500'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['elements'], [])

    @patch('food_app.views.execute_overpass_query')
    def test_defaults_radius_on_invalid_input(self, mock_query):
        mock_query.return_value = []
        response = self.client.get('/api/food/', {'lat': '40.7', 'lon': '-74.0', 'radius': 'bad'})
        self.assertEqual(response.status_code, 200)
        # Verify the raw=True flag was used (query must start with [out:json])
        call_args = mock_query.call_args
        self.assertTrue(call_args[0][0].startswith('[out:json]'))
        self.assertTrue(call_args[1].get('raw') or call_args[0][1] is True)

    @patch('food_app.views.execute_overpass_query')
    def test_500_on_overpass_failure(self, mock_query):
        mock_query.side_effect = RuntimeError("Overpass API error 429")
        response = self.client.get('/api/food/', {'lat': '40.7', 'lon': '-74.0'})
        self.assertEqual(response.status_code, 500)
        self.assertIn('error', response.json())

    @patch('food_app.views.execute_overpass_query')
    def test_query_uses_raw_overpassql(self, mock_query):
        """Verify the view sends a union query with nwr and no overpassify artifacts."""
        mock_query.return_value = []
        self.client.get('/api/food/', {'lat': '34.22', 'lon': '-77.94', 'radius': '5000'})
        query = mock_query.call_args[0][0]
        self.assertIn('nwr[amenity=social_facility]', query)
        self.assertIn('out center qt', query)
        self.assertNotIn('Regex', query)
        self.assertNotIn('overpassify', query)


class FoodLiveServerTests(LiveServerTestCase):
    """Integration tests that spin up a real HTTP server and hit it with requests.
    These catch issues that the Django test client masks: JSON parse failures,
    routing gaps, and real response content-type."""

    @patch('food_app.views.execute_overpass_query')
    def test_api_returns_valid_json_content_type(self, mock_query):
        """Real HTTP GET must return application/json, not HTML (e.g. a 404 page)."""
        mock_query.return_value = []
        r = req_lib.get(
            f'{self.live_server_url}/api/food/',
            params={'lat': '34.22', 'lon': '-77.94', 'radius': '2000'},
            timeout=10,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/json', r.headers.get('Content-Type', ''))
        data = r.json()
        self.assertIn('elements', data)
