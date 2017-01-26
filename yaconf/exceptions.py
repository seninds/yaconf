# coding: utf-8


class Error(Exception):
    """Common yaconf error."""


class ParsingError(Error):
    """Error while parse config file."""
