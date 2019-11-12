#!/usr/bin/env python
"""An abstract class that holds get, put, post, delete for any REST api."""
import re
import requests
import concurrent.futures
import asyncio
from bs4 import BeautifulSoup
import abc


class GenericRestApi(abc.ABC):
    """The object that holds the stache environment variables."""
    @abc.abstractmethod
    def __init__(self, host, header_info, page_query, page_tag="next-page"):
        self.host = host
        self.header_info = header_info
        self.page_tag = page_tag
        self.page_query = page_query
        self.session = self._setup_session()

    def _setup_session(self):
        """Returns a session set up with class' header_info."""
        session = requests.Session()
        session.verify = True
        # 'header_info' must include auth info and the content type.
        session.headers.update(self.header_info)

        return session

    def get(self, endpoints, parameters=None, get_all=True, total_pages=None):
        """Get the xml(s) of the url_endpoint(s) passed in.

        Arguments:
            endpoints (string or list):
                The ilab REST resource you want to get, with or without the
                core_url.
            parameters (dict):
                A mapping of a query-able name: value. NOTE: queries can only
                be added to a single endpoint.
            get_all (bool):
                If there are next-page tags on that resource, whether get
                should return all of the resources on all pages or just the
                first page.
            total_pages (int):
                If a get is given a total_pages keyword, then get will perform
                a multi-threaded get on all of the pages.

        Returns:
            responses (list):
                A list of all of the requests responses for each endpoint.
        """
        if not endpoints:
            return endpoints
        # If the endpoints is a str of one endpoint, turn it into a list.
        if isinstance(endpoints, str):
            endpoints = [endpoints]

        # Add the base url if it was not included on any requested endpoint.
        for i, endpoint in enumerate(endpoints):
            if self.host not in endpoint:
                endpoints[i] = f"{self.host}{endpoint}"

        # Build endpoint with query if a parameters dict is given.
        if parameters and (total_pages is None or get_all is False):
            query = _query_builder(parameters)
            endpoints[0] += query

        responses = list()
        response = self.session.get(endpoints[0], timeout=10)
        response.raise_for_status()

        next_page_tag = None
        # Find the next page tag if it exists and the request is an xml and
        # there is a page_tag.
        if (
            self.session.headers["Content-Type"] == "application/xml"
                and get_all and self.page_tag):
            response_soup = BeautifulSoup(response.text, "xml")
            next_page_tag = response_soup.find(self.page_tag)

        # Multithread get dissimilar endpoints.
        if len(endpoints) > 1:
            responses = _brute_batch_get(self.session, endpoints)

        # Harvest all of the pages of the resource if total pages are unknown.
        elif get_all and next_page_tag and total_pages is None:
            responses = self._harvest_all_resource(
                self.session, endpoints[0], list())

        # Multithread all pages of resource given the page query and total page
        # number.
        elif get_all and total_pages:
            paged_endpoints = list()
            for i in range(1, total_pages + 1):
                if parameters:
                    parameters[self.page_query] = i
                    paged_endpoints.append(
                        endpoints[0] + _query_builder(parameters))
                else:
                    paged_endpoints.append(
                        endpoints[0] + _query_builder({self.page_query: i}))
            responses = _brute_batch_get(self.session, paged_endpoints)

        else:
            response = self.session.get(endpoints[0], timeout=10)
            response.raise_for_status()
            responses.append(response)

        return responses

    def put(self, endpoint, payload):
        """Put the payload to the given endpoint, returning the response.

        Arguments:
            url_endpoint (string):
                The ilab REST resource you want to put.
            payload (string):
                The string to put to the specific endpoint.

        Returns:
            response (requests.models.response):
                Holds, among other things, the returned request information.
        """
        if self.host not in endpoint:
            endpoint = self.host + str(endpoint)
        response = self.session.put(endpoint, str(payload))
        response.raise_for_status()

        return response

    def post(self, endpoint, payload):
        """Post the payload to the given endpoint, returning the response.

        Arguments:
            endpoint (string):
                The REST endpoint to which you want to post.
            payload (string):
                The string to post to the specific endpoint.

        Returns:
            (string):
                The returned endpoint information as an xml-parsable string.
        """
        if self.host not in endpoint:
            url_endpoint = self.host + str(endpoint)
        response = self.session.post(url_endpoint, str(payload))
        response.raise_for_status()

        return response

    def delete(self, endpoint):
        """Delete the given endpoint, returning the response."""
        if self.host not in endpoint:
            endpoint = self.host + str(endpoint)
        response = self.session.delete(endpoint)
        response.raise_for_status()

        return response

    def _harvest_all_resource(self, session, next_page_uri, contents):
        """Recursively harvests gets of all pages from the given session."""
        if next_page_uri:
            response = session.get(next_page_uri, timeout=10)
            response.raise_for_status()

            response_soup = BeautifulSoup(response.text, "xml")
            contents.append(response_soup)
            next_page_tag = response_soup.find(self.page_tag)

            if next_page_tag:
                next_page_uri = re.sub(r"\?.*", "", next_page_uri)
                next_page_uri += _query_builder(
                    {self.page_query: str(next_page_tag.text)})
            else:
                next_page_uri = None

            return self._harvest_all_resource(session, next_page_uri, contents)

        else:
            return contents


def _brute_batch_get(session, urls):
    """Returns a list of multithreaded get responses from the given session."""
    # Setup event loop for async calls.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Execute calls and get responses as a list.
    responses = loop.run_until_complete(_get_async(session, urls))

    return responses


async def _get_async(session, urls):
    """Uses ThreadPoolExecutor to GET the list of uris.

    Arguments:
        uris (list):
            A list of completed uris to make using requests.
    Return:
        A list containing the HTTP responses as dictionaries.
    """
    def single_get(url):
        response = session.get(url)
        response.raise_for_status()
        return response

    # Set up executor.
    with concurrent.futures.ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()

        # Store futures to gather.
        futures = list()
        for url in urls:
            futures.append(loop.run_in_executor(
                executor,
                single_get,
                url
            ))

        # Return data when completed.
        return await asyncio.gather(*futures)


def _query_builder(parameters):
    """Converts dictionary with queries to http-able query."""
    queries = dict()
    for key in parameters:
        queries.setdefault(key, list())
        if isinstance(parameters[key], list):
            queries[key].extend(parameters[key])
        else:
            queries[key].append(parameters[key])

    final_query = ""
    for key, group in queries.items():
        for value in group:
            final_query += f"&{key}={value}"

    final_query = final_query.lstrip('&')
    return f"?{final_query}"
