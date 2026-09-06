"""Exceptions raised by the Radis la Toque client."""

class RadisLaToqueError(Exception):
    """Base client exception."""

class CannotConnect(RadisLaToqueError):
    """The public website could not be reached."""

class RestaurantNotFound(RadisLaToqueError):
    """A restaurant or its canonical identifier could not be found."""

class MenuNotAvailable(RadisLaToqueError):
    """No menu is currently published for the restaurant."""

class InvalidPdf(RadisLaToqueError):
    """The response advertised as a menu is not a readable PDF."""

class MenuParseError(RadisLaToqueError):
    """The PDF is readable but its menu structure is unsupported."""
