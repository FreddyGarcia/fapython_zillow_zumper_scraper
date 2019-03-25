
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
