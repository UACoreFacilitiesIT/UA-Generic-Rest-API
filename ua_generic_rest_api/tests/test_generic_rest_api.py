import math
import json
import string
import unittest
import requests
from nose.tools import raises
from ua_generic_rest_api import ua_generic_rest_api


class TestRestApi(ua_generic_rest_api.GenericRestApi):
    def __init__(self, host, content_type):
        super().__init__(host, content_type, "page")


class TestGenericRestApi(unittest.TestCase):
    def setUp(self):
        json_host = "https://api.openaq.org/v1/"
        self.json_api = TestRestApi(
            json_host, {"Content-Type": "application/json"})

    def test_get_no_urls(self):
        assert self.json_api.get([]) == []

    def test_get_string_and_list(self):
        str_response = self.json_api.get("https://api.openaq.org/v1/cities")
        list_response = self.json_api.get(["https://api.openaq.org/v1/cities"])
        assert str_response[0].text == list_response[0].text

    def test_get_endpoint_with_and_without_host(self):
        with_host = self.json_api.get("https://api.openaq.org/v1/countries")
        without_host = self.json_api.get("countries")
        assert with_host[0].text == without_host[0].text

    def test_get_multiple_queries(self):
        query_response = self.json_api.get(
            "https://api.openaq.org/v1/cities", {"limit": "1", "page": "2"})

        json_response = json.loads(query_response[0].text)
        assert int(json_response["meta"]["page"]) == 2
        assert len(json_response["results"]) == 1

    def test_get_multiple_queries_with_multiple_values(self):
        query_response = self.json_api.get(
            "https://api.openaq.org/v1/cities",
            {"country": ["BR", "CA"], "limit": "10000"})

        json_response = json.loads(query_response[0].text)
        assert int(json_response["meta"]["limit"]) == 10000
        for entry in json_response["results"]:
            assert entry["country"] in ["BR", "CA"]

    def test_batch_get_with_multiple_queries(self):
        endpoints = ["https://api.openaq.org/v1/cities"]
        query_response = self.json_api.get(
            endpoints, {"limit": "1", "page": "2"})

        json_responses = json.loads(query_response[0].text)
        assert int(json_responses["meta"]["page"]) == 2
        assert len(json_responses["results"]) == 1

    def test_batch_get_more_than_max_pool_threads(self):
        first_country_response = self.json_api.get(
            "https://api.openaq.org/v1/countries", {"limit": "1", "page": "1"})
        first_country_json = json.loads(first_country_response[0].text)
        max_countries = int(first_country_json["meta"]["found"])

        urls = ["https://api.openaq.org/v1/countries"] * max_countries
        urls = [f"{url}?limit=1&page={i + 1}" for i, url in enumerate(urls)]
        all_responses = self.json_api.get(urls)
        all_jsons = [json.loads(response.text) for response in all_responses]

        country_codes = [entry["results"][0]["code"] for entry in all_jsons]
        assert len(country_codes) == len(set(country_codes)) == max_countries

    def test_multithread_all_pages_without_existing_parameters(self):
        responses = self.json_api.get("https://api.openaq.org/v1/cities")
        single_json = json.loads(responses[0].text)
        total_pages = math.ceil(
            int(single_json["meta"]["found"])
            / int(single_json["meta"]["limit"]))
        assert total_pages > 1

        responses = self.json_api.get(
            "https://api.openaq.org/v1/cities", total_pages=total_pages)
        city_jsons = [json.loads(response.text) for response in responses]
        num_cities = sum([len(entry["results"]) for entry in city_jsons])
        assert int(city_jsons[0]["meta"]["found"]) == num_cities

    def test_multithread_all_pages_with_existing_parameters(self):
        responses = self.json_api.get("https://api.openaq.org/v1/cities")
        single_json = json.loads(responses[0].text)
        default_limit = int(single_json["meta"]["limit"])
        total_pages = math.ceil(
            int(single_json["meta"]["found"]) / default_limit)
        assert total_pages > 1

        responses = self.json_api.get(
            "https://api.openaq.org/v1/cities",
            parameters={"limit": default_limit},
            total_pages=total_pages)

        city_jsons = [json.loads(response.text) for response in responses]
        num_cities = sum([len(entry["results"]) for entry in city_jsons])
        assert int(city_jsons[0]["meta"]["found"]) == num_cities
        for city in city_jsons:
            assert city["meta"]["limit"] == default_limit

    def test_get_xml_format(self):
        sources_response = self.json_api.get(
            "https://api.openaq.org/v1/sources")
        sources_json = json.loads(sources_response[0].text)
        xml_url = None
        for entry in sources_json["results"]:
            if entry["url"].endswith(".xml"):
                xml_url = entry["url"]
                break

        xml_api = TestRestApi("", {"Content-Type": "application/xml"})
        xml_response = xml_api.get(xml_url)
        assert xml_response[0].status_code == 200

    @raises(requests.exceptions.HTTPError)
    def test_get_fail(self):
        self.json_api.get("get fail!")

    def test_get_url_too_long(self):
        countries = list()
        for letter_one in string.ascii_uppercase:
            for letter_two in string.ascii_uppercase:
                for letter_three in string.ascii_uppercase:
                    countries.append(letter_one + letter_two)
                    countries.append(letter_one + letter_two + letter_three)

        # Make sure that we get a 414 error with this endpoint.
        parameters = {"country": countries[:10000]}
        get_endpoint = "https://api.openaq.org/v1/cities"
        get_endpoint += ua_generic_rest_api._query_builder(parameters)
        try:
            requests.get(get_endpoint)
        except requests.exceptions.HTTPError as error:
            assert error.status == 414

        responses = self.json_api.get(
            "https://api.openaq.org/v1/cities", parameters=parameters)

        for response in responses:
            # Some of these gets are not well-formed, but it doesn't return a
            # 414 error.
            assert response.status_code in [200, 400]

    def test_put_endpoint_with_and_without_host(self):
        # NOTE: To test the put function, write a test for your api that
        # extends GenericRestApi; this test api doesn't have any
        # unauthenticated put endpoints.
        pass

    def test_delete(self):
        # NOTE: To test the delete function, write a test for your api that
        # extends GenericRestApi; this test api doesn't have any
        # unauthenticated delete endpoints.
        pass

    def test_post(self):
        # NOTE: To test the post function, write a test for your api that
        # extends GenericRestApi; this test api doesn't have any
        # unauthenticated post endpoints.
        pass
