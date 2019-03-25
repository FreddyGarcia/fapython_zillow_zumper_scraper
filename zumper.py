'''
    This script gets the contacts in the properties
    from the Zumper site and insert them in a hubspot account.

    To run this script please install the dependencies
    in the requirements.txt file:

    `$ pip install -r requirements.txt`

    Theses fields must exist in Hubspot
        - firstname
        - email
        - phone
        - interested_properties

    author: Freddy Garcia Abreu
    email: freddie-wpy@outlook.es
    date: 03/23/2019
'''
import click
import json
import requests
import logging
import core

session = requests.session()

auth_url = "https://www.zumper.com/api/t/1/bundle"
leads_url = 'https://www.zumper.com/api/p/1/users/0/leads'
listing_url = 'https://www.zumper.com/api/p/1/minlistings?floorplans=false&' \
              'is_pro=true&limit=1000&offset=0&statuses=1,2,3,9,10'


def request_authentication():
    headers = {
        'user-agent': core.USER_AGENT,
        'content-type': "application/json",
        'accept': "*/*",
        'cache-control': "no-cache"
    }

    try:
        response = session.get(auth_url, headers=headers)
        json_res = json.loads(response.text)

        csrf = json_res['csrf']
        xz_token = json_res['xz_token']

        auth_headers = {
            'origin': "https://www.zumper.com",
            'referer': "https://www.zumper.com",
            'x-csrftoken': csrf,
            'x-zumper-xz-token': xz_token,
            'user-agent': core.USER_AGENT,
            'content-type': "application/json",
            'accept': "*/*",
            'cache-control': "no-cache"
        }

        return auth_headers
    except Exception as e:
        core.handle_error(e, 'Cannot authenticate')


def authenticate(headers):
    try:
        credentials = core.ZUMPER['CREDENTIALS']
        payload = json.dumps(credentials)
        response = session.put(auth_url, data=payload, headers=headers)
        return response
    except Exception as e:
        core.handle_error(e, 'Cannot authenticate')


def get_contacts(headers):
    response = session.get(leads_url, headers=headers)
    json_res = json.loads(response.text)

    list(map(get_listing_info, json_res))

    return json_res


def get_listing(listing_id):
    global listings
    for listing in listings:
        if listing['listing_id'] == listing_id:
            return listing


def get_listing_info(lead):
    listings = []
    for candidate in lead['candidates']:
        listing = get_listing(candidate['listing_id'])
        listings.append(', '.join([candidate['title'], listing['city'], listing['country']]))
    lead['listing'] = ';'.join(listings)

    return lead


def get_listings(headers):
    response = session.get(listing_url, headers=headers)
    json_res = json.loads(response.text)
    return json_res


def contact_fields(contact):

    return_fields = [
        {'property' : 'lead', 'value' : 'zumper'}
    ]

    for field in core.ZUMPER['FIELDS']:
        value = core.deep_get(contact, field[0])

        if value is not None:
            return_fields.append({
                'property' : field[1],
                'value' : value
            })

    return return_fields


def main():
    logging.info('Authenticating...')
    auth_headers = request_authentication()
    authenticate(auth_headers)

    logging.info('Getting listing')

    global listings
    listings = get_listings(auth_headers)
    contacts = get_contacts(auth_headers)

    logging.info('Getting contacts')
    logging.info(f'{len(contacts)} contacts found')

    with click.progressbar(contacts, label='Saving contacts') as bar:
        for contact in bar:
            contact_info = contact_fields(contact)
            succeeded = core.insert_contact(contact_info)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit) as e:
        core.handle_error(e, 'Script execution finished by the user')
