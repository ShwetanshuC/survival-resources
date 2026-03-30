import requests as req_lib
from django.test import TestCase, LiveServerTestCase
from unittest.mock import patch, MagicMock


class SearchShelterViewTests(TestCase):

    def setUp(self):
        # Prevent real network calls to 211 API / Nominatim in all view tests.
        patcher = patch('shelter_app.views.fetch_211_resources', return_value=[])
        self.mock_211 = patcher.start()
        self.addCleanup(patcher.stop)

    @patch('shelter_app.views.execute_overpass_query')
    def test_returns_elements_on_success(self, mock_query):
        mock_query.return_value = [{'type': 'node', 'id': 2, 'lat': 40.7, 'lon': -74.0, 'tags': {'name': 'Test Shelter'}}]
        response = self.client.get('/api/shelter/', {'lat': '40.7', 'lon': '-74.0', 'radius': '2000'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['elements']), 1)

    @patch('shelter_app.views.execute_overpass_query')
    def test_normalizes_way_center_coordinates(self, mock_query):
        """Ways returned by 'out center' have center.lat/lon — must be lifted to top-level."""
        mock_query.return_value = [
            {'type': 'way', 'id': 3, 'center': {'lat': 40.7, 'lon': -74.0}, 'tags': {'name': 'Shelter Building'}}
        ]
        response = self.client.get('/api/shelter/', {'lat': '40.7', 'lon': '-74.0', 'radius': '2000'})
        self.assertEqual(response.status_code, 200)
        elements = response.json()['elements']
        self.assertEqual(len(elements), 1)
        self.assertIn('lat', elements[0])
        self.assertEqual(elements[0]['lat'], 40.7)

    @patch('shelter_app.views.execute_overpass_query')
    def test_returns_empty_list_when_no_results(self, mock_query):
        mock_query.return_value = []
        response = self.client.get('/api/shelter/', {'lat': '40.7', 'lon': '-74.0'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['elements'], [])

    @patch('shelter_app.views.execute_overpass_query')
    def test_defaults_radius_on_invalid_input(self, mock_query):
        mock_query.return_value = []
        response = self.client.get('/api/shelter/', {'lat': '40.7', 'lon': '-74.0', 'radius': 'bad'})
        self.assertEqual(response.status_code, 200)
        # Verify the raw=True flag was used (query must start with [out:json])
        call_args = mock_query.call_args
        self.assertTrue(call_args[0][0].startswith('[out:json]'))
        self.assertTrue(call_args[1].get('raw') or call_args[0][1] is True)

    @patch('shelter_app.views.execute_overpass_query')
    def test_500_on_overpass_failure(self, mock_query):
        mock_query.side_effect = RuntimeError("Overpass API error 504")
        response = self.client.get('/api/shelter/', {'lat': '40.7', 'lon': '-74.0'})
        self.assertEqual(response.status_code, 500)
        self.assertIn('error', response.json())

    @patch('shelter_app.views.execute_overpass_query')
    def test_query_uses_raw_overpassql(self, mock_query):
        """Verify the view sends a union query with nwr and no overpassify artifacts."""
        mock_query.return_value = []
        self.client.get('/api/shelter/', {'lat': '34.22', 'lon': '-77.94', 'radius': '5000'})
        query = mock_query.call_args[0][0]
        self.assertIn('nwr[amenity=social_facility]', query)
        self.assertIn('out center qt', query)
        self.assertNotIn('Regex', query)


class ShelterScraperAccuracyTests(TestCase):
    """Tests for shelter_app scraper accuracy rules (mirrors medical_app pattern)."""

    def _make_source(self):
        return {
            "name": "Test Shelter Org",
            "url": "http://example.com/shelter-news",
            "event_selectors": [".alert"],
            "service_area_lat": 34.2368,
            "service_area_lon": -77.9461,
        }

    def _make_driver_with_blocks(self, texts):
        blocks = []
        for t in texts:
            b = MagicMock()
            b.text = t
            blocks.append(b)
        driver = MagicMock()
        driver.execute_script.return_value = "complete"
        driver.find_elements.return_value = blocks
        return driver

    @patch('shelter_app.scraper.geocode_address')
    def test_event_with_no_address_match_is_dropped(self, mock_geo):
        from shelter_app.scraper import _scrape_source
        driver = self._make_driver_with_blocks(["Warming Center Open\nCome inside tonight\nNo address here"])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])
        mock_geo.assert_not_called()

    @patch('shelter_app.scraper.geocode_address', return_value=None)
    def test_event_dropped_when_geocoding_fails(self, mock_geo):
        from shelter_app.scraper import _scrape_source
        text = "Emergency Shelter Activation\n456 Oak Ave, Wilmington, NC 28403"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])

    @patch('shelter_app.scraper.geocode_address', return_value=(40.7128, -74.0060))  # NYC
    def test_event_dropped_when_outside_service_area(self, mock_geo):
        from shelter_app.scraper import _scrape_source
        text = "Overnight Shelter Open\n456 Oak Ave, Wilmington, NC 28403"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])

    @patch('shelter_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_valid_event_included_with_source_attribution(self, mock_geo):
        from shelter_app.scraper import _scrape_source
        text = "Warming Center Now Open\n456 Oak Ave, Wilmington, NC 28403"
        driver = self._make_driver_with_blocks([text])
        source = self._make_source()
        result = _scrape_source(driver, source)
        self.assertEqual(len(result), 1)
        event = result[0]
        self.assertIn('lat', event)
        self.assertIn('lon', event)
        self.assertEqual(event['tags']['source_label'], source['name'])
        self.assertEqual(event['tags']['event_url'], source['url'])

    @patch('shelter_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_event_with_short_name_is_dropped(self, mock_geo):
        from shelter_app.scraper import _scrape_source
        text = "Shlt\n456 Oak Ave, Wilmington, NC 28403"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])

    @patch('shelter_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_no_fallback_coords_in_output(self, mock_geo):
        from shelter_app.scraper import _scrape_source
        text = "Emergency Shelter Tonight\n456 Oak Ave, Wilmington, NC 28403"
        driver = self._make_driver_with_blocks([text])
        source = self._make_source()
        result = _scrape_source(driver, source)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]['lat'], 34.2250)
        self.assertAlmostEqual(result[0]['lon'], -77.9450)


class ShelterLiveServerTests(LiveServerTestCase):
    """Integration tests that spin up a real HTTP server and hit it with requests."""

    @patch('shelter_app.views.fetch_211_resources', return_value=[])
    @patch('shelter_app.views.execute_overpass_query')
    def test_api_returns_valid_json_content_type(self, mock_query, mock_211):
        """Real HTTP GET must return application/json, not HTML (e.g. a 404 page)."""
        mock_query.return_value = []
        r = req_lib.get(
            f'{self.live_server_url}/api/shelter/',
            params={'lat': '34.22', 'lon': '-77.94', 'radius': '2000'},
            timeout=10,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/json', r.headers.get('Content-Type', ''))
        data = r.json()
        self.assertIn('elements', data)

    def test_events_endpoint_returns_elements_key(self):
        """Events endpoint must always return {'elements': [...]} even when scraper fails."""
        r = req_lib.get(f'{self.live_server_url}/api/shelter/events/', timeout=45)
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/json', r.headers.get('Content-Type', ''))
        data = r.json()
        self.assertIn('elements', data)
