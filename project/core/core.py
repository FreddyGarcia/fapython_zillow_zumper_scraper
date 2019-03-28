import sys
import logging
import json
import requests


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-5s %(levelname)-8s %(message)s')

HUBSPOT_KEY = '9a30206a-0b12-4934-9f59-dc4ea2503497'

# This is a field mapping:
# (zillow, hubspot)
# (zumper, hubspot)
# Add here the fields you want to take from zillow
# and save them into hubspot
ZILLOW = {
    'CREDENTIALS' : {'email' : 'stlrentals1%40gmail.com', 'password' : 'H0m3v35t!'},
    'FIELDS' : (
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
}

ZUMPER = {
    'CREDENTIALS' : {'username' : 'stlrentals1@gmail.com', 'password' : 'H0m3v35t!'},
    'FIELDS' : (
        ('name','firstname'),
        ('email','email'),
        ('phone','phone'),
        ('listing','interested_properties'),
    )
}


USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' \
             '(KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'


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


def insert_contact(contact_info):
    endpoint = f'https://api.hubapi.com/contacts/v1/contact/?hapikey={HUBSPOT_KEY}'
    headers = {}
    headers["Content-Type"] = "application/json"

    try:
        data = json.dumps({'properties' : contact_info})
        r = requests.post(url=endpoint, data=data, headers=headers)
        json_res = json.loads(r.text)
        return json_res
    except Exception as e:
        logging.warning('Couldn\'t insert conctact')
        logging.warning(contact_info[:2])


def handle_error(exception, message):
    logging.debug(exception)
    logging.error(message)
    sys.exit()


def check_authentication(func):
    def wrapper(self, *args, **kwargs):
        if not self.is_authenticated:
            raise Exception('No autheticated')
            return False
        return func(self, *args, **kwargs)

    return wrapper
