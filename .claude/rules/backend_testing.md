# Backend Testing Rules

## Test Location
Each app has its own `tests.py`. Tests for `food_app` go in `food_app/tests.py`, etc.

## Run Commands
```bash
# All apps
python manage.py test food_app shelter_app medical_app rehab_app map_app

# Single app
python manage.py test food_app

# Single test case
python manage.py test food_app.tests.SearchFoodViewTests.test_returns_elements_on_success
```

## Mocking Strategy
Always mock `execute_overpass_query` at the view module level — never let tests hit the real Overpass API.

```python
@patch('food_app.views.execute_overpass_query')
def test_name(self, mock_query):
    mock_query.return_value = [...]
```

## Required Test Cases Per App
Each category app must cover:
1. **Success** — mock returns elements, assert 200 + correct `elements` list
2. **Empty results** — mock returns `[]`, assert 200 + empty list (not an error)
3. **Invalid radius** — pass a non-integer radius string, assert 200 (parse_radius defaults to 2000)
4. **Overpass failure** — mock raises `RuntimeError`, assert 500 + `error` key in response

## Shared Utility Tests
Tests for `map_app/overpass.py` live in `map_app/tests.py` and must mock `requests.post`.
