import pprint
import json
import requests
import core

url = "https://www.zumper.com/api/t/1/bundle"
session = requests.session()

fields = (
    ('name','firstname'),
    ('email','email'),
    ('phone','phone'),
    ('listing','listing'),
)


def request_authentication():
    headers = {
        'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
        'content-type': "application/json",
        'accept': "*/*",
        'cache-control': "no-cache"
    }

    response = session.get(url, headers=headers)
    json_res = json.loads(response.text)

    auth_headers = {
        'origin': "https://www.zumper.com",
        'referer': "https://www.zumper.com",
        'x-csrftoken': json_res['csrf'],
        'x-zumper-xz-token': json_res['xz_token'],
        'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
        'content-type': "application/json",
        'accept': "*/*",
        'cache-control': "no-cache"
    }

    return auth_headers


def authenticate(headers):
    payload = json.dumps({ 'username' : 'stlrentals1@gmail.com' , 'password' : 'H0m3v35t!' })
    response = session.put(url, data=payload, headers=headers)
    return response


def get_user():
    response = session.get(url)
    pprint.pprint(json.loads(response.text))


def leads(headers):
    response = session.get('https://www.zumper.com/api/p/1/users/0/leads', headers=headers)
    json_res = json.loads(response.text)

    list(map(get_listing_info, json_res))
    x = list(map(contact_fields, json_res))
    import ipdb; ipdb.set_trace(context=25)


def get_listing(listing_id):
    global listings
    for listing in listings:
        if listing['listing_id'] == listing_id:
            return listing

    # TODO remove!!
    raise Exception('!!!' * 10)


def get_listing_info(lead):
    listings = []
    for candidate in lead['candidates']:
        listing = get_listing(candidate['listing_id'])
        listings.append(', '.join([candidate['title'], listing['city'], listing['country']]))
    lead['listing'] = ';'.join(listings)

    return lead


def listing(headers):
    response = session.get('https://www.zumper.com/api/p/1/minlistings?floorplans=false&is_pro=true&limit=1000&offset=0&statuses=1,2,3,9,10', headers=headers)
    json_res = json.loads(response.text)
    return json_res


def contact_fields(contact):

    return_fields = [
        {'property' : 'lead', 'value' : 'zumper'}
    ]

    for field in fields:
        value = core.deep_get(contact, field[0])

        if value is not None:
            return_fields.append({
                'property' : field[1],
                'value' : value
            })

    return return_fields


auth_headers = request_authentication()
authenticate(auth_headers)
listings = listing(auth_headers)


leads(auth_headers)