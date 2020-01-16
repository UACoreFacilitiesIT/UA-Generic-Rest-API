# Changelog

All notable changes to this project can be found here.
The format of this changelog is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

#### 2020/01/16[2.0.2](https://github.com/UACoreFacilitiesIT/UA-Generic-Rest-API/)

Bug fix with querying multiple values under the same tag. Previously queries for that tag would be empty and now they actually contain all of the requested values.

#### 2019/12/05[2.0.1](https://github.com/UACoreFacilitiesIT/UA-Generic-Rest-API/)

Small changes to the _query_builder function, which now builds queries based on a set of given queries to avoid repeating the same query multiple times.

#### 2019/10/08[2.0.0](https://github.com/UACoreFacilitiesIT/UA-Generic-Rest-API/)

In this new release, the get function is not as specific as it used to be. Now you can pass in the keyword "total_pages" to get all pages, but the "next_page" concept has been removed.

#### 2019/10/03 [1.0.0](https://github.com/UACoreFacilitiesIT/UA-Generic-Rest-API/commit/1854437081a4e1769b7dc6dff588c2a68703a0cb)

This is the initial start point for a University of Arizona Generic Rest API.

- Moved repo from private repo to public.
