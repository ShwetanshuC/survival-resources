from django.test import TestCase
from unittest.mock import patch, MagicMock
from map_app.overpass import execute_overpass_query, normalize_elements, parse_radius


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
        el = {'type': 'node', 'lat': 34.0, 'lon': -77.0}
        result = normalize_elements([el])
        self.assertEqual(result[0]['lat'], 34.0)
        self.assertEqual(result[0]['lon'], -77.0)

    def test_way_center_lifted(self):
        el = {'type': 'way', 'center': {'lat': 34.0, 'lon': -77.0}}
        result = normalize_elements([el])
        self.assertEqual(result[0]['lat'], 34.0)
        self.assertEqual(result[0]['lon'], -77.0)

    def test_existing_lat_not_overwritten(self):
        el = {'type': 'node', 'lat': 10.0, 'lon': -10.0, 'center': {'lat': 99.0, 'lon': -99.0}}
        result = normalize_elements([el])
        self.assertEqual(result[0]['lat'], 10.0)

    def test_empty_list(self):
        self.assertEqual(normalize_elements([]), [])


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
