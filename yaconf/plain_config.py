# coding: utf-8

import copy
import io
import logging
import re

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

try:
    basestring
except NameError:
    basestring = str


from exceptions import PlainConfigError, ParsingError


logger = logging.getLogger('plain_config')


class PlainConfig(object):

    _CONFIG_LINE = re.compile('^\s*(?P<option>.*?)\s*=\s*(?P<value>.*)$')
    _COMMENT_LINE = re.compile('^\s*#.*$')
    _VALID_OPT = re.compile('(^[^.]+$)|(^[^.].*[^.]$)')

    def __init__(self, data=None, strict=True, encoding='utf-8'):
        super(PlainConfig, self).__init__()
        self._data = {}
        self._strict = strict
        self._encoding = encoding

        if data is not None:
            try:
                self.update(data)
            except PlainConfigError:
                for item in data:
                    self.update(item)

    def update(self, data):
        if isinstance(data, (PlainConfig, ConfigParser)):
            self._update_config(data)
        elif isinstance(data, Mapping):
            self._update_dict(data)
        elif isinstance(data, basestring):
            self._update_path(data)
        elif hasattr(data, 'read'):
            self._update_file(data)
        else:
            type_str = type(data).__name__
            raise PlainConfigError('unknown data type: %s' % type_str)

    def get(self, opt, converter=None, default=None):
        if opt in self._data:
            if converter is None:
                return self._data[opt]
            return converter(self._data[opt])

        if default is not None:
            return default
        raise KeyError(opt)

    def set(self, opt, value, converter=str):
        value = self._data[opt] = converter(value)
        return value

    def items(self, prefix=None):
        prefix_len = 0
        opt_gen = self._data.keys()
        if prefix is not None:
            prefix_len = len(prefix + '.')
            opt_gen = (x for x in self._data if x.startswith(prefix + '.'))

        for opt in opt_gen:
            yield opt[prefix_len:], self.get(opt)

    def __repr__(self):
        return '<{}: {:d} opts>'.format(type(self).__name__, len(self._data))

    def __str__(self):
        return '\n'.join('{} = {}'.format(opt, val)
                         for opt, val in sorted(self._data.items()))

    def __eq__(self, config):
        return self._data == config._data

    def __getitem__(self, opt):
        return self.get(opt)

    def __setitem__(self, opt, value):
        return self.set(opt, value)

    def __copy__(self):
        cls = self.__class__
        obj = cls.__new__(cls)
        obj.__dict__.update(self.__dict__)
        return obj

    def __deepcopy__(self, memo):
        cls = self.__class__
        obj = cls.__new__(cls)
        memo[id(self)] = obj

        for key, val in self.__dict__.items():
            setattr(obj, key, copy.deepcopy(val, memo))
        return obj

    def _update_config(self, config):
        if isinstance(config, PlainConfig):
            return self._data.update(config._data)

        for section_name, section in config.items():
            for opt, val in section.items():
                self._data['{}.{}'.format(section_name, opt)] = val

    def _update_dict(self, dict_data):
        data = {}
        cum_error = []

        for opt, value in dict_data.items():
            if self._VALID_OPT.match(opt) is None:
                msg = 'invalid option name: {}'
                cum_error.append(msg.format(opt))
            else:
                data[opt] = str(value)

        if cum_error:
            raise ParsingError('\n'.join(cum_error))
        self._data.update(data)

    def _update_path(self, path):
        with io.open(path, 'r', encoding=self._encoding) as fileobj:
            self._update_file(fileobj)

    def _update_file(self, fileobj):
        last_opt = None
        data = {}
        cum_error = []

        for lineno, line in enumerate(fileobj, start=1):
            m = self._CONFIG_LINE.match(line)
            if m is not None:
                last_opt = m.group('option')
                if self._VALID_OPT.match(last_opt) is None:
                    msg = '{:d}: invalid option name: {}'
                    cum_error.append(msg.format(lineno, last_opt))
                if self._strict and last_opt in data:
                    msg = '{:d}: option duplicate: {}'
                    cum_error.append(msg.format(lineno, last_opt))
                data[last_opt] = [m.group('value').strip()]
            else:
                m = self._COMMENT_LINE.match(line)
                if line.lstrip() and m is None:
                    if last_opt is None or last_opt not in data:
                        msg = '{:d}: value without option: {}'
                        cum_error.append(msg.format(lineno, line))
                    else:
                        data[last_opt].append(line.strip())

        if cum_error:
            raise ParsingError('\n'.join(cum_error))

        data = {key: '\n'.join(items).rstrip() for key, items in data.items()}
        logger.debug('parsed %d options', len(data))
        self._data.update(data)
