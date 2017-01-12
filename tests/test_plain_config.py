#!/usr/bin/python
# coding: utf-8

import copy
import tempfile
import unittest
from collections import Counter, namedtuple

try:
    from configparser import ConfigParser, DEFAULTSECT
except ImportError:
    from ConfigParser import ConfigParser, DEFAULTSECT

import context
from yaconf import PlainConfig, ParsingError
from yaconf.utils import bool2str, str2bool, iter2str, str2iter
from yaconf.utils import ON_OFF, YES_NO, TRUE_FALSE, ONE_ZERO


__fake_usage__ = [context]


class PlainConfigTest(unittest.TestCase):

    def setUp(self):
        Case = namedtuple('Case', 'lines, dict, error')
        self.cases = [
            Case(['base = x', '', 'base.opt0 = y', 'base.opt1 = 123', '',
                  'base.opt.subopt = z', ''],
                 {'base': 'x', 'base.opt0': 'y', 'base.opt1': '123',
                  'base.opt.subopt': 'z'},
                 None),
            Case(['', 'opt0 =', '',
                  'opt1 = ', '  line_1  ', '', 'line_3', '',
                  'opt2 = line_0', '', 'line_2'],
                 {'opt0': '', 'opt1': '\nline_1\nline_3',
                  'opt2': 'line_0\nline_2'},
                 None),
            Case(['base = val', '.opt = 123'],
                 {'base': 'val', '.opt': '123'},
                 ParsingError),
            Case(['base = val', 'opt. = 123'],
                 {'base': 'val', 'opt.': '123'},
                 ParsingError),
        ]

    def test_set_get(self):
        config = PlainConfig()

        self.assertEqual(config.set('set_opt', 'set_value'), 'set_value')
        self.assertEqual(config.get('set_opt'), 'set_value')

        self.assertEqual(config.get('bad_opt', default='def_val'), 'def_val')
        self.assertEqual(config.get('bad_opt', default=123), 123)
        self.assertEqual(config.get('bad_opt', 'pos_arg'), 'pos_arg')

    def test_setitem_getitem(self):
        config = PlainConfig()

        retval = config['setitem_opt'] = 'setitem_value'
        self.assertEqual(retval, 'setitem_value')
        self.assertEqual(config['setitem_opt'], 'setitem_value')

        config['base.old_opt'] = 'old_val'
        subconfig = {'opt': '123', 'sub.opt': 'test'}
        config['base':] = subconfig
        self.assertFalse('base.old_opt' in config)
        self.assertEqual(Counter(config['base':].items()),
                         Counter(subconfig.items()))

    def test_subconfig(self):
        data = {'opt': '0', 'base.opt': '1', 'sub.opt0': '2', 'sub.opt1': '3'}
        config = PlainConfig(data)
        self.assertEqual(Counter(config.items()), Counter(data.items()))
        self.assertEqual(Counter(config.subconfig('sub').items()),
                         Counter(config.items('sub')))
        self.assertEqual(len(config.subconfig('null')), 0)

    def test_bool(self):
        config = PlainConfig()
        self.assertFalse(bool(config))
        config['opt'] = 'val'
        self.assertTrue(bool(config))

    def test_delitem(self):
        data = {'imm': 'val', 'opt': '1', 'sub.opt0': '2', 'sub.opt1': '3'}
        config = PlainConfig(data)
        self.assertEqual(Counter(config.items()), Counter(data.items()))

        del config['opt']
        del data['opt']
        self.assertEqual(Counter(config.items()), Counter(data.items()))

        del config['sub':]
        del_opts = [opt for opt in data if opt.startswith('sub.')]
        for opt in del_opts:
            del data[opt]
        self.assertEqual(Counter(config.items()), Counter(data.items()))

    def test_converters(self):
        config = PlainConfig()

        self.assertEqual(config.set('bool', True), 'True')
        self.assertTrue(config.get('bool', converter=str2bool))
        self.assertEqual(config.set('bool', False), 'False')
        self.assertFalse(config.get('bool', converter=str2bool))

        for mode, true, false in [(ON_OFF, 'on', 'off'),
                                  (YES_NO, 'yes', 'no'),
                                  (TRUE_FALSE, 'true', 'false'),
                                  (ONE_ZERO, '1', '0')]:
            self.assertEqual(config.set('bool', True,
                                        lambda x: bool2str(x, mode)), true)
            self.assertTrue(config.get('bool', converter=str2bool))
            self.assertEqual(config.set('bool', False,
                                        lambda x: bool2str(x, mode)), false)
            self.assertFalse(config.get('bool', converter=str2bool))

        self.assertEqual(config.set('float', 3.14), '3.14')
        self.assertEqual(config.get('float', converter=float), 3.14)
        self.assertEqual(config.set('int', 123), '123')
        self.assertEqual(config.get('int', converter=int), 123)

        self.assertEqual(config.set('list', [1, 2, 3], converter=iter2str),
                         '1, 2, 3')
        self.assertEqual(config.get('list', converter=str2iter),
                         ['1', '2', '3'])
        self.assertEqual(
            config.get('list', converter=lambda x: str2iter(x, converter=int)),
            [1, 2, 3]
        )

    def test_items(self):
        config = PlainConfig()

        base_dict = {}
        for opt in ('opt' + str(idx) for idx in range(3)):
            base_dict[opt] = config[opt] = opt

        sub_dict = {}
        for opt in ('opt.sub' + str(idx) for idx in range(3)):
            base_dict[opt] = config[opt] = opt
            sub_dict[opt.split('.', 1)[1]] = opt

        self.assertEqual(Counter(config.items()),
                         Counter(base_dict.items()))
        self.assertEqual(Counter(config.items('opt')),
                         Counter(sub_dict.items()))

    def test_update_dict(self):
        opts = {}
        config = PlainConfig()

        for case in self.cases:
            if case.error is None:
                config.update(case.dict)
                opts.update(case.dict)
            else:
                with self.assertRaises(case.error):
                    config.update(case.dict)
            self.assertEqual(Counter(config.items()), Counter(opts.items()))

    def test_update_plain_config(self):
        config_dict = {'base': 'x', 'base.opt': 'y', 'base.opt.subopt': 'z'}
        old_config = PlainConfig()
        old_config.update(config_dict)

        new_config = copy.deepcopy(old_config)
        new_config.update(config_dict)
        self.assertEqual(new_config, old_config)

        new_config.update(old_config)
        self.assertEqual(new_config, old_config)

        config_dict = {'new.opt': 'val'}
        old_config.update(config_dict)
        self.assertNotEqual(new_config, old_config)
        new_config.update(old_config)
        self.assertEqual(new_config, old_config)

    def test_update_raw_config(self):
        plain_config = PlainConfig()
        defaults = {'def.opt0': 'val', 'def.opt1': '123'}
        config = ConfigParser(defaults)
        plain_opts = {'{}.{}'.format(DEFAULTSECT, opt): val
                      for opt, val in defaults.items()}
        plain_config.update(config)
        self.assertEqual(Counter(plain_config.items()),
                         Counter(plain_opts.items()))

        sections = {'sec0': {'opt0': 'val0', 'opt.sub0': 'sub-val0'},
                    'sec1': {'opt0': 'val1', 'opt.sub1': 'new-sub'}}
        for section_name, section in sections.items():
            config.add_section(section_name)
            plain_opts.update({'{}.{}'.format(section_name, opt): val
                               for opt, val in defaults.items()})
            for opt, val in section.items():
                plain_opts['{}.{}'.format(section_name, opt)] = val
                config.set(section_name, opt, val)
        plain_config.update(config)
        self.assertEqual(Counter(plain_config.items()),
                         Counter(plain_opts.items()))

    def test_update_file(self):
        opts = {}
        config = PlainConfig()

        for case in self.cases:
            if case.error is None:
                opts.update(case.dict)
                with tempfile.TemporaryFile(mode='w+') as fileobj:
                    fileobj.write('\n'.join(case.lines))
                    fileobj.flush(), fileobj.seek(0)
                    config.update(fileobj)
            else:
                with self.assertRaises(case.error):
                    with tempfile.TemporaryFile(mode='w+') as fileobj:
                        fileobj.write('\n'.join(case.lines))
                        fileobj.flush(), fileobj.seek(0)
                        config.update(fileobj)
            self.assertEqual(Counter(config.items()), Counter(opts.items()))

    def test_update_path(self):
        opts = {}
        config = PlainConfig()

        config.update('/bad/path/to/config')

        for case in self.cases:
            if case.error is None:
                opts.update(case.dict)
                with tempfile.NamedTemporaryFile(mode='w+') as fileobj:
                    fileobj.write('\n'.join(case.lines))
                    fileobj.flush()
                    config.update(fileobj.name)
            else:
                with self.assertRaises(case.error):
                    with tempfile.NamedTemporaryFile(mode='w+') as fileobj:
                        fileobj.write('\n'.join(case.lines))
                        fileobj.flush()
                        config.update(fileobj.name)
            self.assertEqual(Counter(config.items()), Counter(opts.items()))

    def test_ctor(self):
        opts = {}

        opts.update({'plain.opt0': 'old_val', 'plain.opt1': 'dict_val'})
        plain_config = PlainConfig(opts)
        self.assertEqual(Counter(plain_config.items()), Counter(opts.items()))

        self.assertEqual(Counter(PlainConfig(plain_config).items()),
                         Counter(plain_config.items()))

        raw_config = ConfigParser()
        raw_opts = {'raw.opt0': 'raw_val', 'raw.opt1': '123'}
        opts.update(raw_opts)
        for plain_opt, val in raw_opts.items():
            section_name, opt = plain_opt.split('.', 1)
            if not raw_config.has_section(section_name):
                raw_config.add_section(section_name)
            raw_config.set(section_name, opt, val)
        self.assertEqual(Counter(PlainConfig(raw_config).items()),
                         Counter(raw_opts.items()))

        dict_data = {'dict.opt': 'dict'}
        opts.update(dict_data)
        with tempfile.TemporaryFile(mode='w+') as fileobj, \
                tempfile.NamedTemporaryFile(mode='w+') as named_file:
            fileobj_opts = {}
            for case in (c for i, c in enumerate(self.cases)
                         if i % 2 == 0 and c.error is None):
                fileobj.write('\n'.join(case.lines))
                fileobj_opts.update(case.dict)
            fileobj.flush(), fileobj.seek(0)

            self.assertEqual(Counter(PlainConfig(fileobj).items()),
                             Counter(fileobj_opts.items()))
            opts.update(fileobj_opts)
            fileobj.seek(0)

            named_file_opts = {}
            for case in (c for i, c in enumerate(self.cases)
                         if i % 2 != 0 and c.error is None):
                named_file.write('\n'.join(case.lines))
                named_file_opts.update(case.dict)
            named_file.flush()
            self.assertEqual(Counter(PlainConfig(named_file.name).items()),
                             Counter(named_file_opts.items()))
            opts.update(named_file_opts)

            data = [dict_data, fileobj, named_file.name,
                    plain_config, raw_config]
            config = PlainConfig(data)
            self.assertEqual(Counter(config.items()), Counter(opts.items()))

    def test_contains(self):
        config = PlainConfig({'opt0': 'test', 'opt1': 123})
        self.assertTrue('opt0' in config)
        self.assertTrue('opt1' in config)
        self.assertFalse('bad_opt' in config)

    def test_iter(self):
        data_dict = {'opt0': 'test', 'opt1': 123}
        config = PlainConfig(data_dict)
        self.assertEqual(Counter(config), Counter(data_dict.keys()))


if __name__ == '__main__':
    unittest.main()
