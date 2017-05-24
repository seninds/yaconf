# coding: utf-8

import copy
import io
import itertools
import logging
import os.path
import re

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

try:
    from configparser import DEFAULTSECT
except ImportError:
    from ConfigParser import DEFAULTSECT

try:
    basestring
except NameError:
    basestring = unicode = str


from .exceptions import Error, ParsingError


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
            except Error:
                for item in data:
                    self.update(item)

    def update(self, data):
        if (isinstance(data, PlainConfig) or
                (hasattr(data, 'sections') and hasattr(data, 'items'))):
            self._update_config(data)
        elif isinstance(data, Mapping):
            self._update_dict(data)
        elif isinstance(data, basestring):
            self._update_path(data)
        elif hasattr(data, 'read'):
            self._update_file(data)
        else:
            type_str = type(data).__name__
            raise Error('unknown data type: {}'.format(type_str))

    def get(self, opt, default=None, conv=str):
        if opt in self._data:
            return conv(self._data[opt])
        if default is not None:
            return default
        raise KeyError(opt)

    def set(self, opt, value, conv=str):
        value = self._data[opt] = conv(value)
        return value

    def items(self, prefix=None):
        prefix_len = 0
        opt_gen = self._data.keys()

        if prefix is not None:
            prefix_len = len(prefix + '.')
            opt_gen = (x for x in self._data if x.startswith(prefix + '.'))

        for opt in opt_gen:
            yield opt[prefix_len:], self.get(opt)

    def subconfig(self, prefix):
        return self[prefix:]

    def __repr__(self):
        return '<{}: {:d} opts>'.format(type(self).__name__, len(self._data))

    def __str__(self):
        return '\n'.join('{} = {}'.format(opt, val)
                         for opt, val in sorted(self._data.items()))

    def __eq__(self, config):
        return self._data == config._data

    def __getitem__(self, index):
        if isinstance(index, slice):
            kwargs = {'strict': self._strict, 'encoding': self._encoding}
            return type(self)(data=dict(self.items(index.start)), **kwargs)
        return self.get(index)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            if not isinstance(value, Mapping):
                msg = '{} is not Mapping instance'.format(type(value).__name__)
                raise Error(msg)

            kwargs = {'strict': self._strict, 'encoding': self._encoding}
            config = type(self)(data=value, **kwargs)

            del self[index]
            for k, v in config.items():
                self.set('{}.{}'.format(index.start, k), v)
            return value

        return self.set(index, value)

    def __delitem__(self, index):
        if isinstance(index, slice):
            prefix = index.start + '.'
            del_opts = [opt for opt in self if opt.startswith(prefix)]
            for opt in del_opts:
                del self[opt]
        else:
            del self._data[index]

    def __contains__(self, opt):
        return opt in self._data

    def __iter__(self):
        return iter(self._data)

    def __bool__(self):
        return bool(self._data)

    def __len__(self):
        return len(self._data)

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

        for section in itertools.chain((DEFAULTSECT,), config.sections()):
            for opt, val in config.items(section):
                self._data['{}.{}'.format(section, opt)] = val

    def _update_dict(self, dict_data, conv=str):
        data = {}
        cum_error = []

        for opt, value in dict_data.items():
            if self._VALID_OPT.match(opt) is None:
                msg = 'update by dict: invalid option name: {}'
                cum_error.append(msg.format(opt))
            else:
                data[opt] = conv(value)

        if cum_error:
            raise ParsingError('\n'.join(cum_error))
        self._data.update(data)

    def _update_path(self, path):
        if not os.path.exists(path):
            return
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
