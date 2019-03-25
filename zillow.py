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
import logging
import requests
import core

session = requests.session()

# Disable urllib3 logging
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.CRITICAL)

# Credentials
login_url = "https://www.zillow.com/user/account/services/Login.htm"
contacts_url = 'https://www.zillow.com/rental-manager/proxy/rental-manager-api/' \
               'api/v1/users/leads/leadsForListing?listingId={0}&start=0&limit=100'
properties_url = 'https://www.zillow.com/rental-manager/proxy/rental-manager-api/api/v2/users' \
                 '/properties/listings?active=true&inactive=true&searchText=&feeds=true&manual=' \
                 'true&ascending=true&sort=created&featured=all&startKeyExclusive={0}&limit=60&' \
                 'includeListingDetails=false&includeListingRestrictions=true&includeMaintenancePartner' \
                 '=true&includeArchived=false&includeUnarchived=true'


def authenticate():
    headers = {
        'user-agent': core.USER_AGENT,
        'accept': "*/*",
        'content-type': "application/x-www-form-urlencoded",
        'cache-control': "no-cache"
    }

    credentials = core.ZILLOW['CREDENTIALS']
    data = "ap=&email={email}&password={password}".format(**credentials)
    response = session.post(login_url, data=data, headers=headers)

    if response.status_code == 200:
        res_json = json.loads(response.text)

        if res_json.get('succeeded') is not None:
            return True

    return False


def get_listings(lastId=''):
    try:
        response = session.get(properties_url.format(lastId))
        res_json = json.loads(response.text)

        res_cont = res_json['response']
        hasMore = res_cont['pager']['hasMore']
        endKey = res_cont['pager']['endKey']
        listingId = list(map(lambda x: x['listingId'] , res_cont['listings'] ))

        if hasMore:
            listingId += get_listings(endKey)

        return listingId

    except Exception as e:
        core.handle_error(e, 'Properties list cannot be retrieved')


def get_contacts(listingId):
    try:
        response = session.get(contacts_url.format(listingId))
        res_json = json.loads(response.text)

        res_cont = res_json['response']
        total = res_cont['pager']['total']
        contacts = res_cont['inquiries']
        listing = res_cont['listing']

        return (listing, contacts)

    except Exception as e:
        core.handle_error(e, 'Contact list cannot be retrieved')


def get_contact_field(listing, contact):

    listing_info = listing.get('street') + ', ' + \
                   listing.get('city') + ', ' + \
                   listing.get('state') + ' ' + \
                   listing.get('zip')

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


def main():
    logging.info('Authenticating... ')
    is_authenticated = authenticate()
    succeeded_count = 0

    if is_authenticated:
        logging.info('Login succeed')

        listings = get_listings()
        logging.info(f'{len(listings)} properties found')

        with click.progressbar(listings, label='Looking for contacts') as bar:

            for listing in bar:
                listing, contacts = get_contacts(listing)

                for contact in contacts:
                    contact_info = get_contact_field(listing, contact)
                    succeeded = core.insert_contact(contact_info)
                    succeeded_count += 1 if succeeded else 0

        logging.info(f'{succeeded_count} new contacts inserted')
    else:
        logging.error('Bad credentials')


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit) as e:
        core.handle_error(e, 'Script execution finished by the user')

