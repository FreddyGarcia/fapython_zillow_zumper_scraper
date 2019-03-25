'''
    This script gets the contacts in the properties
    from the Zillow site and insert them in a hubspot account.

    To run this script please install the dependencies
    in the requirements.txt file:

    `$ pip install -r requirements.txt`

    author: Freddy Garcia Abreu
    email: freddie-wpy@outlook.es
    date: 03/23/2019
'''
import sys
import click
import json
import logging
import requests


logging.basicConfig(#filename='zillow.log',
                    level=logging.INFO,
                    format='%(asctime)s %(name)-5s %(levelname)-8s %(message)s')
session = requests.session()


# Disable urllib3 logging
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.CRITICAL)

# Credentials
ZILLOW_ACCOUNT = { 'email' : 'stlrentals1%40gmail.com', 'password' : 'H0m3v35t!'}
HUBSPOT_KEY = '9a30206a-0b12-4934-9f59-dc4ea2503497'

properties_url = 'https://www.zillow.com/rental-manager/proxy/rental-manager-api/api/v2/users/properties/listings?active=true&inactive=true&searchText=&feeds=true&manual=true&ascending=true&sort=created&featured=all&startKeyExclusive={0}&limit=60&includeListingDetails=false&includeListingRestrictions=true&includeMaintenancePartner=true&includeArchived=false&includeUnarchived=true'
contacts_url = 'https://www.zillow.com/rental-manager/proxy/rental-manager-api/api/v1/users/leads/leadsForListing?listingId={0}&start=0&limit=100'
login_url = "https://www.zillow.com/user/account/services/Login.htm"

# This is a field mapping:
# (zillow, hubspot)
# Add here the fields you want to take from zillow
# and save them into hubspot
fields = (
    ('name','firstname'),
    ('email','email'),
    ('phone','phone'),
    ('message','message'),
    ('attributes.employer','employer'),
    ('attributes.credit','score'),
    ('attributes.moveInTimeframe','move_in_timeframe'),
    ('attributes.isSmoker','is_smoker'),
    ('attributes.numOccupants','num_occupants'),
)

# Headers need to perform the requests
headers = {
    'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36",
    'accept': "*/*",
    'content-type': "application/x-www-form-urlencoded",
    'cache-control': "no-cache"
}


def handle_error(exception, message):
    logging.debug(exception)
    logging.error(message)
    sys.exit()


def authenticate():
    data = "ap=&email={email}&password={password}".format(**ZILLOW_ACCOUNT)
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
        handle_error(e, 'Properties list cannot be retrieved')


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
        handle_error(e, 'Contact list cannot be retrieved')


def deep_get(dct, dotted_path, default=None):
    '''
        get nested dict values
    '''
    for key in dotted_path.split('.'):
        try:
            dct = dct[key]
        except KeyError:
            return default
    return dct


def get_contact_field(listing, contact):

    listing_info = listing.get('street') + ', ' + \
                   listing.get('city') + ', ' + \
                   listing.get('state') + ' ' + \
                   listing.get('zip')

    return_fields = [
        {'property' : 'listing', 'value' : listing_info},
        {'property' : 'lead', 'value' : 'zillow'}
    ]

    for field in fields:
        value = deep_get(contact, field[0])

        if value is not None:
            return_fields.append({
                'property' : field[1],
                'value' : value
            })

    return return_fields


def insert_contact(contact_info):
    endpoint = f'https://api.hubapi.com/contacts/v1/contact/?hapikey={HUBSPOT_KEY}'
    headers = {}
    headers["Content-Type"] = "application/json"

    try:
        data = json.dumps({'properties' : contact_info})
        r = requests.post(url=endpoint, data=data, headers=headers)
        json_res = json.loads(r.text)
        return json_res.get('vid') is not None
    except Exception as e:
        logging.warning('Couldn\'t insert conctact')
        logging.warning(contact_info[:2])


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
                    succeeded = insert_contact(contact_info)
                    succeeded_count += 1 if succeeded else 0

        logging.info(f'{succeeded_count} new contacts inserted')
    else:
        logging.error('Bad credentials')


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit) as e:
        handle_error(e, 'Script execution finished by the user')
