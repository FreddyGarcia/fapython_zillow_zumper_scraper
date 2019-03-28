'''
    This script gets the contacts in the properties
    from the Zillow site and insert them in a hubspot account.

    To run this script please install the dependencies
    in the requirements.txt file:

    `$ pip install -r requirements.txt`


    Theses fields must exist in Hubspot
        - firstname
        - email
        - phone
        - message
        - employer
        - score
        - move_in_timeframe
        - is_smoker
        - num_occupants

    author: Freddy Garcia Abreu
    email: freddie-wpy@outlook.es
    date: 03/23/2019
'''
import click
import json
import datetime
import logging
import requests
import urllib
from project.core import core

# Disable urllib3 logging
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.INFO)

api_url = 'https://www.zillow.com/rental-manager/proxy/rental-manager-api/api'
login_url = "https://www.zillow.com/user/account/services/Login.htm"
restrict_url = f'{api_url}''/v1/users/properties/locations/restrictions?fullAddress={0}&unit={1}&listingTypeCode={2}'
contacts_url = f'{api_url}''/v1/users/leads/leadsForListing?listingId={0}&start=0&limit=100'
verifica_url = f'{api_url}''/v1/properties/addresses/verification?fullAddress={0}&unit={1}'
autocomp_url = f'{api_url}''/v1/properties/addresses/autocomplete?partialAddress={0}'
property_url = f'{api_url}''/v2/users/properties/listings?active=true&inactive=true&searchText=&feeds=true&manual=' \
                 'true&ascending=true&sort=created&featured=all&startKeyExclusive={0}&limit=60&' \
                 'includeListingDetails=false&includeListingRestrictions=true&includeMaintenancePartner' \
                 '=true&includeArchived=false&includeUnarchived=true'


class Zillow:

    def __init__(self):
        self.request = requests.session()
        self.is_authenticated = False

    def authenticate(self):
        headers = {
            'user-agent': core.USER_AGENT,
            'accept': "*/*",
            'content-type': "application/x-www-form-urlencoded",
            'cache-control': "no-cache"
        }

        credentials = core.ZILLOW['CREDENTIALS']
        data = "ap=&email={email}&password={password}".format(**credentials)
        response = self.request.post(login_url, data=data, headers=headers)

        if response.status_code == 200:
            res_json = json.loads(response.text)
            self.is_authenticated = res_json.get('succeeded') is not None
            return self.is_authenticated

        return False

    @staticmethod
    def get_contact_field(listing, contact):

        listing_info = listing.get('street') + ', ' + \
                       listing.get('city') + ', ' + \
                       listing.get('state') + ' ' + \
                       listing.get('zip')

        today = datetime.date.today().isoformat()
        return_fields = [
            {'property' : 'interested_properties', 'value' : listing_info},
            {'property' : 'lead', 'value' : 'zillow'}
        ]

        for field in core.ZILLOW['FIELDS']:
            value = core.deep_get(contact, field[0])

            if value is not None:
                return_fields.append({
                    'property' : field[1],
                    'value' : value
                })

        return return_fields

    @core.check_authentication
    def get_listings(self, last_id=''):
        response = self.request.get(property_url.format(last_id))
        res_json = json.loads(response.text)

        res_cont = res_json['response']
        hasMore = res_cont['pager']['hasMore']
        endKey = res_cont['pager']['endKey']
        listings = res_cont['listings']
        # listings = list(map(lambda x: x['listingId'] , res_cont['listings'] ))

        if hasMore:
            listings += self.get_listings(endKey)

        return listings

    @core.check_authentication
    def get_contacts(self, listing):
        listing_id = listing['listingId']
        response = self.request.get(contacts_url.format(listing_id))
        res_json = json.loads(response.text)

        res_cont = res_json['response']
        total = res_cont['pager']['total']
        contacts = res_cont['inquiries']
        listing = res_cont['listing']

        return (listing, contacts)

    @core.check_authentication
    def rental_csrftoken(self):
        res = self.request.get('https://www.zillow.com/rental-manager/properties')
        token = res.cookies.get('rental_csrftoken')
        return token

    @core.check_authentication
    def create_property(self, address, property_type, listing_type, unit_number):
        token = self.rental_csrftoken()
        params = urllib.parse.urlencode({
            'propertyTypeCode' : property_type,
            'listingTypeCode' : listing_type,
            'fullAddress' : address,
            'unitNumber' : unit_number
        })

        headers = {'rental_csrftoken' : token}
        url = f'{api_url}/v1/users/properties/create?{params}'
        res = self.request.post(url, headers=headers)
        res_json = json.loads(res.text)

        success = res_json.get('success')

        return success

    @core.check_authentication
    def autocomplete_address(self, address):
        response = self.request.get(autocomp_url.format(address))
        res_json = json.loads(response.text)
        addresses = res_json['response']['addresses']
        success = res_json['success']

        return success, addresses

    @core.check_authentication
    def verificate_address(self, address, unit):
        response = self.request.get(verifica_url.format(address, unit))
        res_json = json.loads(response.text)
        property_ = res_json.get('response')
        success = res_json['success']

        return success, property_

    def check_restrictions(self, address, unit, listing_type):
        response = self.request.get(restrict_url.format(address, unit, listing_type))
        res_json = json.loads(response.text)
        property_ = res_json.get('response')
        success = res_json['success']

        return success, property_


    def __repr__(self):
        return f'Zillow(is_authenticated={self.is_authenticated})'


def main():
    zillow = Zillow()

    logging.info('Authenticating... ')
    is_authenticated = zillow.authenticate()
    succeeded_count = 0

    if is_authenticated:
        logging.info('Login succeed')

        listings = zillow.get_listings()
        logging.info(f'{len(listings)} properties found')

        with click.progressbar(listings, label='Looking for contacts') as bar:

            for listing in bar:
                listing, contacts = zillow.get_contacts(listing)

                for contact in contacts:
                    contact_info = Zillow.get_contact_field(listing, contact)
                    success = core.insert_contact(contact_info)
                    succeeded_count += 1 if success else 0

        logging.info(f'{succeeded_count} new contacts inserted')
    else:
        logging.error('Bad credentials')


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit) as e:
        core.handle_error(e, 'Script execution finished by the user')

