import json
import requests as req_lib
from django.test import TestCase, LiveServerTestCase
from unittest.mock import patch, MagicMock


class SearchMedicalViewTests(TestCase):

    def setUp(self):
        # Prevent real network calls to 211 API / Nominatim in all view tests.
        patcher = patch('medical_app.views.fetch_211_resources', return_value=[])
        self.mock_211 = patcher.start()
        self.addCleanup(patcher.stop)

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

    @patch('medical_app.views.execute_overpass_query')
    def test_query_includes_pharmacy(self, mock_query):
        """Pharmacy is a critical resource for crisis users — must be in the union query."""
        mock_query.return_value = []
        self.client.get('/api/medical/', {'lat': '34.22', 'lon': '-77.94', 'radius': '2000'})
        query = mock_query.call_args[0][0]
        self.assertIn('nwr[amenity=pharmacy]', query)

    def test_events_endpoint_returns_elements_key(self):
        """Events endpoint must always return {'elements': [...]} even when scraper fails."""
        response = self.client.get('/api/medical/events/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('elements', response.json())

    @patch('medical_app.scraper.scrape_all_sources', return_value=[
        {'type': 'event', 'lat': 34.22, 'lon': -77.94, 'tags': {'name': 'Free Clinic', 'source_label': 'CFCA'}}
    ])
    def test_events_returns_scraped_elements_on_success(self, mock_scrape):
        """When scraper returns events, they must appear in the response elements list."""
        response = self.client.get('/api/medical/events/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('elements', data)
        self.assertEqual(len(data['elements']), 1)
        self.assertEqual(data['elements'][0]['tags']['name'], 'Free Clinic')

    @patch('medical_app.scraper.scrape_all_sources', return_value=[])
    def test_events_returns_empty_list_when_scraper_finds_nothing(self, mock_scrape):
        """When scraper returns no events, response must be {'elements': []} not an error."""
        response = self.client.get('/api/medical/events/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['elements'], [])

    @patch('medical_app.scraper.scrape_all_sources', side_effect=RuntimeError("Selenium unavailable"))
    def test_events_returns_200_on_scraper_failure(self, mock_scrape):
        """Scraper exception must not bubble up — response must be 200 with elements key."""
        response = self.client.get('/api/medical/events/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('elements', response.json())


# ---------------------------------------------------------------------------
# Scraper unit tests — _scrape_source behaviour without real Selenium/network
# ---------------------------------------------------------------------------

class ScraperAccuracyTests(TestCase):
    """Tests for _scrape_source accuracy rules (no fallback coords)."""

    def _make_source(self):
        return {
            "name": "Test Org",
            "url": "http://example.com/events",
            "event_selectors": [".event"],
            "service_area_lat": 34.2368,
            "service_area_lon": -77.9461,
        }

    def _make_driver_with_blocks(self, texts):
        """Return a mock Selenium driver whose find_elements yields mock blocks."""
        from selenium.webdriver.common.by import By

        blocks = []
        for t in texts:
            b = MagicMock()
            b.text = t
            blocks.append(b)

        driver = MagicMock()
        driver.execute_script.return_value = "complete"
        driver.find_elements.return_value = blocks
        return driver

    @patch('medical_app.scraper.geocode_address')
    def test_event_with_no_address_match_is_dropped(self, mock_geo):
        """Block with no ADDRESS_RE match must be silently dropped."""
        from medical_app.scraper import _scrape_source
        driver = self._make_driver_with_blocks(["Mobile Food Pantry\nCome get food\nNo address here"])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])
        mock_geo.assert_not_called()

    @patch('medical_app.scraper.geocode_address', return_value=None)
    def test_event_dropped_when_geocoding_fails(self, mock_geo):
        """Block with address that geocoding cannot resolve must be dropped."""
        from medical_app.scraper import _scrape_source
        text = "Free Clinic Event\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])

    @patch('medical_app.scraper.geocode_address', return_value=(40.7128, -74.0060))  # New York City
    def test_event_dropped_when_outside_service_area(self, mock_geo):
        """Geocoded coords far from service area (NYC vs Wilmington NC) must be dropped."""
        from medical_app.scraper import _scrape_source
        text = "Health Fair\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])

    @patch('medical_app.scraper.geocode_address', return_value=(34.2250, -77.9450))  # local Wilmington coords
    def test_valid_event_included_with_source_attribution(self, mock_geo):
        """Valid event (address found, geocoded, plausible) must include source_label and event_url."""
        from medical_app.scraper import _scrape_source
        text = "Free Health Screening\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        source = self._make_source()
        result = _scrape_source(driver, source)
        self.assertEqual(len(result), 1)
        event = result[0]
        self.assertIn('lat', event)
        self.assertIn('lon', event)
        self.assertEqual(event['tags']['source_label'], source['name'])
        self.assertEqual(event['tags']['event_url'], source['url'])

    @patch('medical_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_event_with_short_name_is_dropped(self, mock_geo):
        """Event whose first line is fewer than 5 chars must be dropped."""
        from medical_app.scraper import _scrape_source
        text = "Mtg\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        result = _scrape_source(driver, self._make_source())
        self.assertEqual(result, [])

    @patch('medical_app.scraper.geocode_address', return_value=(34.2250, -77.9450))
    def test_no_fallback_coords_in_output(self, mock_geo):
        """Returned events must use geocoded coords, never fallback service-area coords."""
        from medical_app.scraper import _scrape_source
        text = "Free Health Screening\n123 Main St, Wilmington, NC 28401"
        driver = self._make_driver_with_blocks([text])
        source = self._make_source()
        result = _scrape_source(driver, source)
        self.assertEqual(len(result), 1)
        # coords must come from geocode_address (34.2250, -77.9450), not service area (34.2368, -77.9461)
        self.assertAlmostEqual(result[0]['lat'], 34.2250)
        self.assertAlmostEqual(result[0]['lon'], -77.9450)


class PlausibilityHelperTests(TestCase):
    """Unit tests for _haversine_km and _is_plausible."""

    def test_haversine_same_point_is_zero(self):
        from medical_app.scraper import _haversine_km
        self.assertAlmostEqual(_haversine_km(34.22, -77.94, 34.22, -77.94), 0.0)

    def test_haversine_known_distance(self):
        """Wilmington NC to Raleigh NC is roughly 200 km."""
        from medical_app.scraper import _haversine_km
        km = _haversine_km(34.2257, -77.9447, 35.7796, -78.6382)
        self.assertGreater(km, 150)
        self.assertLess(km, 250)

    def test_is_plausible_nearby(self):
        from medical_app.scraper import _is_plausible
        self.assertTrue(_is_plausible(34.22, -77.94, 34.24, -77.95, max_km=80))

    def test_is_plausible_far_away(self):
        from medical_app.scraper import _is_plausible
        # New York City vs Wilmington NC — should be implausible at 80 km
        self.assertFalse(_is_plausible(40.7128, -74.0060, 34.2368, -77.9461, max_km=80))


class MedicalLiveServerTests(LiveServerTestCase):
    """Integration tests that spin up a real HTTP server and hit it with requests.
    These catch issues that the Django test client masks: JSON parse failures,
    routing gaps, static-file regressions, and real response content-type."""

    @patch('medical_app.views.fetch_211_resources', return_value=[])
    @patch('medical_app.views.execute_overpass_query')
    def test_api_returns_valid_json_content_type(self, mock_query, mock_211):
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
        r = req_lib.get(f'{self.live_server_url}/api/medical/events/', timeout=45)
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/json', r.headers.get('Content-Type', ''))
        data = r.json()
        self.assertIn('elements', data)
