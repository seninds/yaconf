# coding: utf-8


try:
    basestring
except NameError:
    basestring = unicode = str


ON_OFF = 'on off'
YES_NO = 'yes no'
TRUE_FALSE = 'true false'
ONE_ZERO = '1 0'


def str2bool(string):
    if isinstance(string, basestring):
        if string.lower() in ('off', 'no', 'false', '0'):
            return False
        return True
    raise ValueError('illegal string value: {}'.format(string))


def bool2str(boolean, type=TRUE_FALSE):
    return type.split()[0 if boolean else 1]


def iter2str(iterable, conv=str):
    return ', '.join(map(conv, iterable))


def str2iter(string, container=list, conv=None):
    string = string.replace(',', '')
    if conv is None:
        return container(string.split())
    return container(map(conv, string.split()))
