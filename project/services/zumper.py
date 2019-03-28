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
from project.services import core

auth_url = "https://www.zumper.com/api/t/1/bundle"
leads_url = 'https://www.zumper.com/api/p/1/users/0/leads'
listing_url = 'https://www.zumper.com/api/p/1/minlistings?floorplans=false&' \
              'is_pro=true&limit=1000&offset=0&statuses=1,2,3,9,10'


class Zumper:

    def __init__(self):
        self.request = requests.session()
        self.is_authenticated = False

    def request_authentication(self):
        headers = {
            'user-agent': core.USER_AGENT,
            'content-type': "application/json",
            'accept': "*/*",
            'cache-control': "no-cache"
        }

        response = self.request.get(auth_url, headers=headers)
        json_res = json.loads(response.text)

        csrf = json_res.get('csrf')
        xz_token = json_res.get('xz_token')

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

        self.auth_headers = auth_headers

    def authenticate(self):
        credentials = core.ZUMPER['CREDENTIALS']
        payload = json.dumps(credentials)
        response = self.request.put(auth_url, data=payload, headers=self.auth_headers)

        self.is_authenticated = response.status_code == 200
        return self.is_authenticated

    @core.check_authentication
    def get_contacts(self):
        response = self.request.get(leads_url, headers=self.auth_headers)
        json_res = json.loads(response.text)

        list(map(self.get_listing_info, json_res))

        return json_res

    @core.check_authentication
    def get_listing(self, listing_id):
        global listings
        for listing in listings:
            if listing['listing_id'] == listing_id:
                return listing

    @core.check_authentication
    def get_listing_info(self, lead):
        listings = []
        for candidate in lead['candidates']:
            listing = self.get_listing(candidate['listing_id'])
            listings.append(', '.join([candidate['title'], listing['city'], listing['country']]))
        lead['listing'] = ';'.join(listings)

        return lead

    @core.check_authentication
    def get_listings(self):
        response = self.request.get(listing_url, headers=self.auth_headers)
        json_res = json.loads(response.text)
        return json_res

    @staticmethod
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

    def __repr__(self):
        return f'Zumper(is_authenticated={self.is_authenticated})'


def main():
    zumper = Zumper()

    logging.info('Authenticating...')
    zumper.request_authentication()
    zumper.authenticate()

    logging.info('Getting listing')

    global listings
    listings = zumper.get_listings()
    contacts = zumper.get_contacts()

    logging.info('Getting contacts')
    logging.info(f'{len(contacts)} contacts found')

    with click.progressbar(contacts, label='Saving contacts') as bar:
        for contact in bar:
            contact_info = Zumper.contact_fields(contact)
            succeeded = core.insert_contact(contact_info)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit) as e:
        core.handle_error(e, 'Script execution finished by the user')
