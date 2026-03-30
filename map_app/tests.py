from django.test import TestCase
from unittest.mock import patch, MagicMock
from map_app.overpass import execute_overpass_query, normalize_elements, parse_radius
from map_app.api_211 import fetch_211_resources, _merge_dedup, _get_zip_for_coords
from django.core.cache import cache as django_cache


class ParseRadiusTests(TestCase):
    def test_valid_integer_string(self):
        self.assertEqual(parse_radius('2000'), 2000)

    def test_invalid_string_returns_default(self):
        self.assertEqual(parse_radius('bad'), 2000)

    def test_none_returns_default(self):
        self.assertEqual(parse_radius(None), 2000)

    def test_custom_default(self):
        self.assertEqual(parse_radius('xyz', default=5000), 5000)

    def test_valid_integer(self):
        self.assertEqual(parse_radius(3000), 3000)


class NormalizeElementsTests(TestCase):
    def test_node_unchanged(self):
        el = {'type': 'node', 'lat': 34.0, 'lon': -77.0, 'tags': {'name': 'Test Place'}}
        result = normalize_elements([el])
        self.assertEqual(result[0]['lat'], 34.0)
        self.assertEqual(result[0]['lon'], -77.0)

    def test_way_center_lifted(self):
        el = {'type': 'way', 'center': {'lat': 34.0, 'lon': -77.0}, 'tags': {'name': 'Test Way'}}
        result = normalize_elements([el])
        self.assertEqual(result[0]['lat'], 34.0)
        self.assertEqual(result[0]['lon'], -77.0)

    def test_existing_lat_not_overwritten(self):
        el = {'type': 'node', 'lat': 10.0, 'lon': -10.0, 'center': {'lat': 99.0, 'lon': -99.0}, 'tags': {'name': 'Named Node'}}
        result = normalize_elements([el])
        self.assertEqual(result[0]['lat'], 10.0)

    def test_empty_list(self):
        self.assertEqual(normalize_elements([]), [])

    def test_unnamed_element_dropped(self):
        named = {'type': 'node', 'lat': 34.0, 'lon': -77.0, 'tags': {'name': 'Food Bank'}}
        unnamed = {'type': 'node', 'lat': 34.1, 'lon': -77.1, 'tags': {}}
        no_tags = {'type': 'node', 'lat': 34.2, 'lon': -77.2}
        blank_name = {'type': 'node', 'lat': 34.3, 'lon': -77.3, 'tags': {'name': '   '}}
        result = normalize_elements([named, unnamed, no_tags, blank_name])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['tags']['name'], 'Food Bank')


class ExecuteOverpassQueryTests(TestCase):

    def setUp(self):
        # Clear the Django cache between tests so cached query results don't
        # bleed across test cases (each test must hit the mock, not the cache).
        from django.core.cache import cache as django_cache
        django_cache.clear()

    @patch('map_app.overpass.requests.post')
    def test_returns_elements_on_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'elements': [{'id': 1}]}
        mock_post.return_value = mock_response

        result = execute_overpass_query('node(1);out;')
        self.assertEqual(result, [{'id': 1}])

    @patch('map_app.overpass.requests.post')
    def test_raises_on_all_endpoints_fail(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 504
        mock_post.return_value = mock_response

        with self.assertRaises(RuntimeError):
            execute_overpass_query('node(1);out;')

    @patch('map_app.overpass.requests.post')
    def test_raises_on_400_bad_query(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        with self.assertRaises(RuntimeError):
            execute_overpass_query('bad query;')

    @patch('map_app.overpass.requests.post')
    def test_raw_true_sends_query_as_is(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'elements': []}
        mock_post.return_value = mock_response

        raw_query = '[out:json][timeout:30];\nnode(1);out;'
        execute_overpass_query(raw_query, raw=True)
        kwargs = mock_post.call_args.kwargs if hasattr(mock_post.call_args, 'kwargs') else mock_post.call_args[1]
        posted_data = kwargs['data']['data']
        self.assertEqual(posted_data, raw_query)

    @patch('map_app.overpass.requests.post')
    def test_raw_false_prepends_header(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'elements': []}
        mock_post.return_value = mock_response

        execute_overpass_query('node(1);out;', raw=False)
        # call_args: (positional_args_tuple, keyword_args_dict)
        # requests.post(url, data={...}, timeout=...) — data is a kwarg
        kwargs = mock_post.call_args.kwargs if hasattr(mock_post.call_args, 'kwargs') else mock_post.call_args[1]
        posted_data = kwargs['data']['data']
        self.assertTrue(posted_data.startswith('[out:json][timeout:90]'))

    @patch('map_app.overpass.requests.post')
    def test_empty_body_tries_next_endpoint(self, mock_post):
        """HTTP 200 with invalid JSON body should try the mirror endpoint."""
        good_response = MagicMock()
        good_response.status_code = 200
        good_response.json.return_value = {'elements': [{'id': 42}]}

        bad_response = MagicMock()
        bad_response.status_code = 200
        bad_response.json.side_effect = ValueError("no JSON")

        mock_post.side_effect = [bad_response, good_response]

        result = execute_overpass_query('node(1);out;')
        self.assertEqual(result, [{'id': 42}])


# ---------------------------------------------------------------------------
# api_211.py tests — no real HTTP calls
# ---------------------------------------------------------------------------

class Fetch211ResourcesTests(TestCase):
    """Tests for map_app/api_211.py — no real HTTP calls."""

    def setUp(self):
        django_cache.clear()

    def _mock_zip_resp(self, zipcode="28403"):
        """Return a mock Nominatim reverse-geocode response."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"address": {"postcode": zipcode}}
        return resp

    def _mock_211_resp(self, results):
        """Return a mock 211 API search response."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"results": results}
        return resp

    @patch('map_app.api_211.requests.get')
    def test_returns_empty_when_nominatim_fails(self, mock_get):
        """If reverse-geocode fails to resolve a zip, return [] silently."""
        from map_app.api_211 import fetch_211_resources
        mock_get.return_value = MagicMock(status_code=500)
        result = fetch_211_resources(34.22, -77.94, 2000, "food")
        self.assertEqual(result, [])

    @patch('map_app.api_211.requests.get')
    def test_returns_elements_on_success(self, mock_get):
        """Valid 211 API response should be converted to element dicts."""
        from map_app.api_211 import fetch_211_resources
        mock_get.side_effect = [
            self._mock_zip_resp("28403"),
            self._mock_211_resp([
                {"document": {
                    "nameService": "Wilmington Food Bank",
                    "latitudeLocation": "34.22",
                    "longitudeLocation": "-77.94",
                    "address1PhysicalAddress": "123 Main St",
                    "cityPhysicalAddress": "Wilmington",
                    "statePhysicalAddress": "NC",
                }}
            ]),
        ]
        result = fetch_211_resources(34.22, -77.94, 2000, "food")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tags"]["name"], "Wilmington Food Bank")
        self.assertEqual(result[0]["tags"]["source_label"], "211 NC")
        self.assertAlmostEqual(result[0]["lat"], 34.22)

    @patch('map_app.api_211.requests.get')
    def test_returns_empty_on_api_error(self, mock_get):
        """Non-200 211 API HTTP response should return [] silently."""
        from map_app.api_211 import fetch_211_resources
        mock_get.side_effect = [
            self._mock_zip_resp("28403"),
            MagicMock(status_code=403),
        ]
        result = fetch_211_resources(34.22, -77.94, 2000, "food")
        self.assertEqual(result, [])

    @patch('map_app.api_211.requests.get')
    def test_drops_records_missing_lat_lon(self, mock_get):
        """Records without latitudeLocation/longitudeLocation must be silently dropped."""
        from map_app.api_211 import fetch_211_resources
        mock_get.side_effect = [
            self._mock_zip_resp("28403"),
            self._mock_211_resp([
                {"document": {"nameService": "No Coords Org", "address1PhysicalAddress": "456 Oak Ave"}}
            ]),
        ]
        result = fetch_211_resources(34.22, -77.94, 2000, "food")
        self.assertEqual(result, [])

    @patch('map_app.api_211.requests.get')
    def test_returns_empty_on_network_exception(self, mock_get):
        """Network exceptions must be caught and [] returned silently."""
        from map_app.api_211 import fetch_211_resources
        mock_get.side_effect = Exception("network error")
        result = fetch_211_resources(34.22, -77.94, 2000, "food")
        self.assertEqual(result, [])

    @patch('map_app.api_211.requests.get')
    def test_drops_records_with_po_box_address(self, mock_get):
        """Records whose address1PhysicalAddress contains 'PO Box' must be dropped."""
        from map_app.api_211 import fetch_211_resources
        mock_get.side_effect = [
            self._mock_zip_resp("28403"),
            self._mock_211_resp([
                {"document": {
                    "nameService": "PO Box Org",
                    "latitudeLocation": "34.22",
                    "longitudeLocation": "-77.94",
                    "address1PhysicalAddress": "PO Box 1234",
                    "cityPhysicalAddress": "Wilmington",
                    "statePhysicalAddress": "NC",
                }}
            ]),
        ]
        result = fetch_211_resources(34.22, -77.94, 2000, "food")
        self.assertEqual(result, [])

    @patch('map_app.api_211.requests.get')
    def test_keeps_records_with_normal_address(self, mock_get):
        """Records with a normal physical address must be kept."""
        from map_app.api_211 import fetch_211_resources
        mock_get.side_effect = [
            self._mock_zip_resp("28403"),
            self._mock_211_resp([
                {"document": {
                    "nameService": "Normal Address Org",
                    "latitudeLocation": "34.22",
                    "longitudeLocation": "-77.94",
                    "address1PhysicalAddress": "456 Pine St",
                    "cityPhysicalAddress": "Wilmington",
                    "statePhysicalAddress": "NC",
                }}
            ]),
        ]
        result = fetch_211_resources(34.22, -77.94, 2000, "food")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tags"]["name"], "Normal Address Org")

    @patch('map_app.api_211.requests.get')
    def test_drops_records_missing_name(self, mock_get):
        """Records with blank nameService must be silently dropped."""
        from map_app.api_211 import fetch_211_resources
        mock_get.side_effect = [
            self._mock_zip_resp("28403"),
            self._mock_211_resp([
                {"document": {
                    "nameService": "",
                    "latitudeLocation": "34.22",
                    "longitudeLocation": "-77.94",
                }}
            ]),
        ]
        result = fetch_211_resources(34.22, -77.94, 2000, "food")
        self.assertEqual(result, [])

    @patch('map_app.api_211.requests.get')
    def test_none_address_field_does_not_crash(self, mock_get):
        """Records where address1PhysicalAddress is None (key present, value null)
        must be dropped cleanly — not raise AttributeError on .strip()."""
        from map_app.api_211 import fetch_211_resources
        mock_get.side_effect = [
            self._mock_zip_resp("28403"),
            self._mock_211_resp([
                {"document": {
                    "nameService": "Null Address Org",
                    "latitudeLocation": "34.22",
                    "longitudeLocation": "-77.94",
                    "address1PhysicalAddress": None,
                    "cityPhysicalAddress": None,
                    "statePhysicalAddress": "NC",
                }}
            ]),
        ]
        result = fetch_211_resources(34.22, -77.94, 2000, "food")
        self.assertEqual(result, [])


class MergeDedupTests(TestCase):
    """Tests for _merge_dedup proximity deduplication."""

    def _el(self, lat, lon, name, extra_tags=None):
        tags = {'name': name}
        if extra_tags:
            tags.update(extra_tags)
        return {'type': 'node', 'lat': lat, 'lon': lon, 'tags': tags}

    def test_no_duplicates_passes_through(self):
        """Elements far apart should all be kept."""
        els = [
            self._el(34.22, -77.94, 'A'),
            self._el(35.50, -78.90, 'B'),
        ]
        result = _merge_dedup(els)
        self.assertEqual(len(result), 2)

    def test_nearby_duplicates_merged(self):
        """Two elements within 50m should be deduplicated to one."""
        # 0.0001 degree ≈ 11m apart — well within 50m threshold
        els = [
            self._el(34.22000, -77.94000, 'Place A'),
            self._el(34.22001, -77.94001, 'Place B'),
        ]
        result = _merge_dedup(els)
        self.assertEqual(len(result), 1)

    def test_richer_record_wins(self):
        """When deduplicating, the record with more populated tag fields is kept."""
        sparse = self._el(34.22000, -77.94000, 'Sparse')
        rich = self._el(34.22001, -77.94001, 'Rich', {'address': '123 Main', 'source_label': '211 NC'})
        result = _merge_dedup([sparse, rich])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['tags']['name'], 'Rich')

    def test_empty_list_returns_empty(self):
        self.assertEqual(_merge_dedup([]), [])

    def test_single_element_unchanged(self):
        els = [self._el(34.22, -77.94, 'Only')]
        result = _merge_dedup(els)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['tags']['name'], 'Only')


# ---------------------------------------------------------------------------
# googlemaps.py tests — no real HTTP calls
# ---------------------------------------------------------------------------

class FetchNearbyGoogleMapsTests(TestCase):

    def setUp(self):
        django_cache.clear()

    def test_returns_empty_list_when_no_key(self):
        """fetch_nearby must return [] silently if GOOGLE_MAPS_API_KEY is not set."""
        import os
        from map_app.googlemaps import fetch_nearby
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_MAPS_API_KEY", None)
            result = fetch_nearby(34.22, -77.94, 2000, "hospital")
        self.assertEqual(result, [])

    @patch('map_app.googlemaps.requests.get')
    def test_returns_elements_on_success(self, mock_get):
        """Valid Places API response should be converted to element dicts."""
        import os
        from map_app.googlemaps import fetch_nearby
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "name": "New Hanover Regional Medical Center",
                    "geometry": {"location": {"lat": 34.22, "lng": -77.94}},
                    "vicinity": "2131 S 17th St, Wilmington",
                }
            ],
        }
        mock_get.return_value = mock_resp
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "testkey"}):
            result = fetch_nearby(34.22, -77.94, 2000, "hospital")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tags"]["name"], "New Hanover Regional Medical Center")
        self.assertEqual(result[0]["tags"]["source_label"], "Google Maps")

    @patch('map_app.googlemaps.requests.get')
    def test_returns_empty_on_zero_results(self, mock_get):
        """ZERO_RESULTS status should return [] (not an error)."""
        import os
        from map_app.googlemaps import fetch_nearby
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ZERO_RESULTS", "results": []}
        mock_get.return_value = mock_resp
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "testkey"}):
            result = fetch_nearby(34.22, -77.94, 2000, "hospital")
        self.assertEqual(result, [])

    @patch('map_app.googlemaps.requests.get', side_effect=Exception("timeout"))
    def test_returns_empty_on_network_exception(self, mock_get):
        """Network exceptions must be caught and [] returned silently."""
        import os
        from map_app.googlemaps import fetch_nearby
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "testkey"}):
            result = fetch_nearby(34.22, -77.94, 2000, "hospital")
        self.assertEqual(result, [])
