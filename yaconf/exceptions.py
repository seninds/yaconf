# coding: utf-8


class PlainConfigError(Exception):
    """Common PlainConfig Error."""


class ParsingError(PlainConfigError):
    """Error which is raised during parsing config file."""
