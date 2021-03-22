#################################
# Name: Renzhong Lu
##### Uniqname:  lurz
#################################

from bs4 import BeautifulSoup
import requests
import json
import secrets  # file that contains your API key

CACHE_FILENAME = 'nps_cache.json'
URL = "https://www.nps.gov"
API_KEY = secrets.API_KEY
API_URL = "http://www.mapquestapi.com/search/v2/radius"


class NationalSite:
    '''a national site

    Instance Attributes
    -------------------
    category: string
        the category of a national site (e.g. 'National Park', '')
        some sites have blank category.

    name: string
        the name of a national site (e.g. 'Isle Royale')

    address: string
        the city and state of a national site (e.g. 'Houghton, MI')

    zipcode: string
        the zip-code of a national site (e.g. '49931', '82190-0168')

    phone: string
        the phone of a national site (e.g. '(616) 319-7906', '307-344-7381')
    '''

    def __init__(self, stored=None):
        if stored:
            self.category = stored['category']
            self.name = stored['name']
            self.address = stored['address']
            self.zipcode = stored['zipcode']
            self.phone = stored['phone']
        else:
            pass

    def info(self):
        return f"{self.name} ({self.category}): {self.address} {self.zipcode}"


def build_state_url_dict():
    ''' Make a dictionary that maps state name to state page url from "https://www.nps.gov"

    Parameters
    ----------
    None

    Returns
    -------
    dict
        key is a state name and value is the url
        e.g. {'michigan':'https://www.nps.gov/state/mi/index.htm', ...}
    '''
    cache_dict = open_cache()
    if cache_dict and 'state_url_dict' in cache_dict:
        print('Using Cache')
        return cache_dict['state_url_dict']

    print("Fetching")
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    list_parent = soup.find(class_='dropdown-menu SearchBar-keywordSearch')
    list_children = list_parent.find_all('li', recursive=False)

    state_url_dict = {}
    for state in list_children:
        a_div = state.find('a')
        state_url_dict[a_div.text.strip().lower()] = URL + a_div.get('href')

    cache_dict['state_url_dict'] = state_url_dict
    save_cache(cache_dict)
    return state_url_dict


def get_site_instance(site_url):
    '''Make an instances from a national site URL.

    Parameters
    ----------
    site_url: string
        The URL for a national site page in nps.gov

    Returns
    -------
    instance
        a national site instance
    '''
    cache_dict = open_cache()
    if cache_dict and site_url in cache_dict:
        print('Using Cache')
        return NationalSite(stored=cache_dict[site_url])

    print('Fetching')
    response = requests.get(site_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    cache = {}
    cache['name'] = soup.find(
        class_='Hero-title').text.strip() if soup.find(class_='Hero-title') else 'No Name'
    cache['category'] = soup.find(
        class_='Hero-designation').text.strip() if soup.find(
        class_='Hero-designation') else 'No Category'
    if soup.find(itemprop='addressLocality') and soup.find(
            itemprop='addressRegion'):
        cache['address'] = soup.find(itemprop='addressLocality').text.strip(
        ) + ', ' + soup.find(itemprop='addressRegion').text.strip()
    else:
        cache['address'] = 'No Address'
    cache['zipcode'] = soup.find(
        itemprop='postalCode').text.strip() if soup.find(
        itemprop='postalCode') else 'No Zipcode'
    cache['phone'] = soup.find(
        itemprop='telephone').text.strip() if soup.find(
        itemprop='telephone') else 'No Phone'
    cache_dict[site_url] = cache
    save_cache(cache_dict)

    return NationalSite(stored=cache)


def get_sites_for_state(state_url):
    '''Make a list of national site instances from a state URL.

    Parameters
    ----------
    state_url: string
        The URL for a state page in nps.gov

    Returns
    -------
    list
        a list of national site instances
    '''
    cache_dict = open_cache()
    site_url = []
    if cache_dict and state_url in cache_dict:
        print('Using Cache')
        site_url = cache_dict[state_url]
    else:
        print("Fetching")
        response = requests.get(state_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        list_park = soup.find(id='list_parks').find_all('li', recursive=False)
        for park in list_park:
            site_url.append(URL + park.find('a').get('href'))
        cache_dict[state_url] = site_url
        save_cache(cache_dict)

    site_list = []
    for url in site_url:
        site_list.append(get_site_instance(url))
    return site_list


def get_nearby_places(site_object):
    '''Obtain API data from MapQuest API.

    Parameters
    ----------
    site_object: object
        an instance of a national site

    Returns
    -------
    dict
        a converted API return from MapQuest API
    '''
    cache_dict = open_cache()
    if cache_dict and site_object.zipcode in cache_dict:
        print('Using Cache')
        return cache_dict[site_object.zipcode]

    print('Fetching')
    params = {
        'key': API_KEY,
        'origin': site_object.zipcode,
        'radius': 10,
        'maxMatches': 10,
        'ambiguities': "ignore",
        "outFormat": "json"
    }
    response = requests.get(API_URL, params=params)
    data = json.loads(response.text)
    cache_dict[site_object.zipcode] = data
    save_cache(cache_dict)
    return data


def print_nearby_places(place_list):
    '''Print out the nearby places from MapQuest API.

    Parameters
    ----------
    dict
        a converted API return from MapQuest API

    Returns
    -------
    None
    '''
    for place in place_list['searchResults']:
        output = "- "
        output += place['name'] + " ("
        output += place['fields']['group_sic_code_name'] if len(
            place['fields']['group_sic_code_name']) > 0 else "no category"
        output += "): " + (place['fields']['address']
                           if len(place['fields']['address']) > 0 else "no address")
        output += ", " + \
            (place['fields']['city'] if len(
                place['fields']['city']) > 0 else "no city")
        print(output)
    return


def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    the CACHE_DICT dictionary.
    if the cache file doesn't exist, creates a new cache dictionary

    Parameters
    ----------
    None

    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except BaseException:
        cache_dict = {}
    return cache_dict


def save_cache(cache_dict):
    ''' Saves the current state of the cache to disk

    Parameters
    ----------
    cache_dict: dict
        The dictionary to save

    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME, "w")
    fw.write(dumped_json_cache)
    fw.close()


def main():
    ''' Interactive search interface

    Parameters
    ----------
    None

    Returns
    -------
    None
    '''
    invalid_str = "[Error] Invalid input"
    state_url_dict = build_state_url_dict()
    while True:
        state_name = input(
            'Enter a state name (e.g. Michigan, michigan) or "exit": ')
        state_name = state_name.lower()
        if state_name == 'exit':
            return
        elif state_name not in state_url_dict:
            print('[Error] Enter proper state name\n')
            continue
        else:
            site_list = get_sites_for_state(state_url_dict[state_name])
            prompt = "List of national sites in " + state_name
            print('-' * len(prompt))
            print(prompt)
            print('-' * len(prompt))
            for i in range(0, len(site_list)):
                print(f'[{str(i+1)}] ' + site_list[i].info())

            while True:
                print('-' * 35)
                site_num = input(
                    'Choose the number for detail search or "exit" or "back": ')
                if site_num == "exit":
                    return
                elif site_num == "back":
                    break
                elif site_num.isnumeric():
                    try:
                        current_index = int(site_num) - 1
                        if current_index < 0 or current_index >= len(
                                site_list):
                            print(invalid_str)
                            continue
                        else:
                            current_site = site_list[current_index]
                            place_list = get_nearby_places(current_site)
                            prompt = "Places near " + current_site.name
                            print('-' * len(prompt))
                            print(prompt)
                            print('-' * len(prompt))
                            print_nearby_places(place_list)
                            continue
                    except ValueError:
                        print(invalid_str)
                        continue
                else:
                    print(invalid_str)
                    continue


if __name__ == "__main__":
    main()
