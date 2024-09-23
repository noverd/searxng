# SPDX-License-Identifier: AGPL-3.0-or-later
"""Yandex (Web, images)"""

from json import loads
from urllib.parse import urlencode, quote
from html import unescape
from lxml import html
from searx.exceptions import SearxEngineCaptchaException
from searx.utils import humanize_bytes, eval_xpath, eval_xpath_list, extract_text, extr


# Engine metadata
about = {
    "website": 'https://yandex.ru/',
    "wikidata_id": 'Q5281',
    "official_api_documentation": "?",
    "use_official_api": False,
    "require_api_key": False,
    "results": 'HTML',
}

# Engine configuration
categories = ['general', 'web']
paging = False
safesearch = True
search_type = ""

# Search URL
base_url_web = 'https://yandex.ru/yandsearch'
base_url_images = 'https://yandex.ru/images/search'

# Search xPath
results_xpath = '//li[contains(@class, "serp-item")]'
url_xpath = './/a[@class="OrganicTitle-Link"]/@href'
title_xpath = './/h2[@class="OrganicTitle-LinkText"]/a[@class="OrganicTitle-Link"]/span'
content_xpath = './/div[@class="Organic-ContentWrapper"]//div[@class="OrganicText"]'


# Proxy URL
proxy_url_web = "https://www.etools.ch"
proxy_search_path = (
    # fmt: off
    '/searchAdvancedSubmit.do'
    '?query={search_term}'
    '&pageResults=20'
    '&safeSearch={safesearch}'
    '&dataSources=mySettings'
    # fmt: on
)

# Proxy xPath
proxy_results_xpath = '//table[@class="result"]//td[@class="record"]'
proxy_url_xpath = './a/@href'
proxy_title_xpath = './a//text()'
proxy_content_xpath = './/div[@class="text"]//text()'


def catch_bad_response(resp):
    if resp.url.path.startswith('/showcaptcha'):
        raise SearxEngineCaptchaException()


def request(query, params):
    if params['safesearch']:
        safesearch = 'true'
    else:
        safesearch = 'false'

    query_params_images = {
        "text": query,
        "uinfo": "sw-1920-sh-1080-ww-1125-wh-999",
    }

    # Settings set to only allow Yandex, and some other stuff
    params['cookies']['searchSettings'] = 'VER_3.3-autocomplete_true-country_web-customerId_-dataSourceResults_20-dataSources_mySettings-excludeQuery_-language_all-markKeyword_false-openNewWindow_true-pageResults_20-queryAutoFocus_true-rankCalibration_%28Base_0%29%28Bing_0%29%28Brave_0%29%28DuckDuckGo_0%29%28Google_0%29%28Lilo_0%29%28Mojeek_0%29%28Qwant_0%29%28Search_0%29%28Tiger_0%29%28Wikipedia_0%29%28Yahoo_0%29%28Yandex_4%29-redirectLinks_false-safeSearch_false-showAdvertisement_true-showSearchStatus_true-timeout_4000-usePost_false'

    if search_type == 'web':
        params['url'] = proxy_url_web + proxy_search_path.format(search_term=quote(query), safesearch=safesearch)
    elif search_type == 'images':
        params['url'] = f"{base_url_images}?{urlencode(query_params_images)}"

    return params


def response(resp):
    if search_type == 'web':

        catch_bad_response(resp)

        dom = html.fromstring(resp.text)

        results = []

        for result in eval_xpath(dom, proxy_results_xpath):
            # Check if the result contains an affiliate link
            if eval_xpath(result, './/span[@class="affiliate"]'):
                continue  # Likely hit a node that is an ad
            url_list = eval_xpath(result, proxy_url_xpath)
            if not url_list:
                continue  # Likely hit a node that is an ad
            url = url_list[0]
            title = extract_text(eval_xpath(result, proxy_title_xpath))
            content = extract_text(eval_xpath(result, proxy_content_xpath))

            results.append({'url': url, 'title': title, 'content': content})

        return results


    if search_type == 'images':

        catch_bad_response(resp)

        html_data = html.fromstring(resp.text)
        html_sample = unescape(html.tostring(html_data, encoding='unicode'))

        content_between_tags = extr(
            html_sample, '{"location":"/images/search/', 'advRsyaSearchColumn":null}}', default="fail"
        )
        json_data = '{"location":"/images/search/' + content_between_tags + 'advRsyaSearchColumn":null}}'

        if content_between_tags == "fail":
            content_between_tags = extr(html_sample, '{"location":"/images/search/', 'false}}}')
            json_data = '{"location":"/images/search/' + content_between_tags + 'false}}}'

        json_resp = loads(json_data)

        results = []
        for _, item_data in json_resp['initialState']['serpList']['items']['entities'].items():
            title = item_data['snippet']['title']
            source = item_data['snippet']['url']
            thumb = item_data['image']
            fullsize_image = item_data['viewerData']['dups'][0]['url']
            height = item_data['viewerData']['dups'][0]['h']
            width = item_data['viewerData']['dups'][0]['w']
            filesize = item_data['viewerData']['dups'][0]['fileSizeInBytes']
            humanized_filesize = humanize_bytes(filesize)

            results.append(
                {
                    'title': title,
                    'url': source,
                    'img_src': fullsize_image,
                    'filesize': humanized_filesize,
                    'thumbnail_src': thumb,
                    'template': 'images.html',
                    'resolution': f'{width} x {height}',
                }
            )

        return results

    return []
