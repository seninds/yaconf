# coding: utf-8


class ConfigError(Exception):
    """Common PlainConfig Error."""


class ParsingError(ConfigError):
    """Error which is raised during parsing config file."""
