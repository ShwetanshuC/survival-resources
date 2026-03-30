import requests as req_lib
from django.test import TestCase, LiveServerTestCase
from unittest.mock import patch, MagicMock


class SearchFoodViewTests(TestCase):

    def setUp(self):
        # Prevent real network calls to 211 API / Nominatim in all view tests.
        patcher = patch('food_app.views.fetch_211_resources', return_value=[])
        self.mock_211 = patcher.start()
        self.addCleanup(patcher.stop)

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


class FoodScraperAccuracyTests(TestCase):
    """Tests for food_app scraper accuracy rules (mirrors medical_app pattern)."""

    def _make_source(self):
        return {
            "name": "Test Food Org",
            "url": "http://example.com/food-events",
            "event_selectors": [".event"],
            "service_area_lat": 34.2357,
            "service_area_lon": -77.9457,
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

    @patch('food_app.scraper.geocode_address')
    def test_event_with_no_address_match_is_dropped(self, mock_geo):
        from food_app.scraper import _scrape_source
        driver = self._make_driver_with_blocks(["Free Food Event\nCome get groceries\nNo address here"])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])
        mock_geo.assert_not_called()

    @patch('food_app.scraper.geocode_address', return_value=None)
    def test_event_dropped_when_geocoding_fails(self, mock_geo):
        from food_app.scraper import _scrape_source
        text = "Free Groceries Event\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])

    @patch('food_app.scraper.geocode_address', return_value=(40.7128, -74.0060))  # NYC — outside service area
    def test_event_dropped_when_outside_service_area(self, mock_geo):
        from food_app.scraper import _scrape_source
        text = "Food Distribution\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])

    @patch('food_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_valid_event_included_with_source_attribution(self, mock_geo):
        from food_app.scraper import _scrape_source
        text = "Fresh Produce Giveaway\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        source = self._make_source()
        result = _scrape_source(driver, source)
        self.assertEqual(len(result), 1)
        event = result[0]
        self.assertIn('lat', event)
        self.assertIn('lon', event)
        self.assertEqual(event['tags']['source_label'], source['name'])
        self.assertEqual(event['tags']['event_url'], source['url'])

    @patch('food_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_event_with_short_name_is_dropped(self, mock_geo):
        from food_app.scraper import _scrape_source
        text = "Fd\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])

    @patch('food_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_no_fallback_coords_in_output(self, mock_geo):
        from food_app.scraper import _scrape_source
        text = "Community Food Pantry\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        source = self._make_source()
        result = _scrape_source(driver, source)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]['lat'], 34.2250)
        self.assertAlmostEqual(result[0]['lon'], -77.9450)

    @patch('food_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_event_date_extracted_when_present(self, mock_geo):
        """DATE_RE finds a future date and stores it in tags['event_date']."""
        from food_app.scraper import _scrape_source
        text = "Free Groceries Giveaway\nDecember 15, 2099\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['tags']['event_date'], 'December 15, 2099')

    @patch('food_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_event_included_without_date(self, mock_geo):
        """Events without a date are still returned; tags must not have 'event_date' key."""
        from food_app.scraper import _scrape_source
        text = "Community Pantry Pickup\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(len(result), 1)
        self.assertNotIn('event_date', result[0]['tags'])

    @patch('food_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_past_dated_event_is_dropped(self, mock_geo):
        """An event with a date clearly in the past must be silently dropped."""
        from food_app.scraper import _scrape_source
        # January 1, 2000 is unambiguously in the past
        text = "Food Pantry Giveaway\nJanuary 1, 2000\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])

    @patch('food_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_undated_event_is_kept(self, mock_geo):
        """Events with no detectable date are kept (assume ongoing/recurring)."""
        from food_app.scraper import _scrape_source
        text = "Weekly Produce Pickup\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(len(result), 1)


class FoodLiveServerTests(LiveServerTestCase):
    """Integration tests that spin up a real HTTP server and hit it with requests.
    These catch issues that the Django test client masks: JSON parse failures,
    routing gaps, and real response content-type."""

    @patch('food_app.views.fetch_211_resources', return_value=[])
    @patch('food_app.views.execute_overpass_query')
    def test_api_returns_valid_json_content_type(self, mock_query, mock_211):
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

    def test_events_endpoint_returns_elements_key(self):
        """Events endpoint must always return {'elements': [...]} even when scraper fails."""
        r = req_lib.get(f'{self.live_server_url}/api/food/events/', timeout=45)
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/json', r.headers.get('Content-Type', ''))
        data = r.json()
        self.assertIn('elements', data)
