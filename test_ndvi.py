import requests

def test_ndvi():
    url = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
    params = {
        'latitude': 44.85,
        'longitude': 76.95,
        'band': '250m_16_days_NDVI',
        'startDate': 'A2015001',
        'endDate': 'A2015040',
        'kmAboveBelow': 0,
        'kmLeftRight': 0
    }
    response = requests.get(url, params=params)
    print(response.status_code)
    try:
        data = response.json()
        print([item['data'] for item in data.get('subset', [])])
    except Exception as e:
        print(response.text)

test_ndvi()
