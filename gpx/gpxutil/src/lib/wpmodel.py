"""
Model for Waypoint and related objects
"""

from datetime import datetime
from typing import List, Optional, Any

import click
import yaml
import geopy
from gpxpy.gpx import GPXWaypoint
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


SKIP_TAGS_WPTX1 = '{http://www.garmin.com/xmlschemas/WaypointExtension/v1}'


class NameSpace:
    """Namespace helper class"""
    @staticmethod
    def remove(tag: str) -> str:
        """remove prefix {namespace} part from XML tag"""
        return tag.split('}')[-1] if '}' in tag else tag

    @staticmethod
    def add(namespace: str, key: str) -> str:
        """create namespace:tag for yaml output"""
        return f"{namespace}:{key}" if namespace else key


class MyLocation:
    """Simple geographical location """

    def __init__(self, latitude: float, longitude: float, elevation: Optional[float] = None) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation

    @staticmethod
    def read_ele(elevation: Optional[str]):
        if elevation:
            return float(elevation)


class MyWaypoint(MyLocation):
    """
    My internal waypoint representation.
    Top level fields should match GPXWaypoint attributes so code processing it
    are compatible with both.
    """
    def __init__(self, wpt: GPXWaypoint = None, wpt_yaml: dict = None) -> None:
        if wpt:
            # for GPXWaypoint the coordinates are already a 'float'
            MyLocation.__init__(self, wpt.latitude, wpt.longitude, wpt.elevation)
            self.name = wpt.name
            self.time = wpt.time
            self.comment = wpt.comment
            self.description = wpt.description
            self.symbol = wpt.symbol
            self.source: Optional[str] = wpt.source
            self.extensions: Optional[List[Any]] = MyWaypoint.read_extensions(wpt.extensions)
        elif wpt_yaml:
            # lat/lon must exist, ele is optional
            MyLocation.__init__(self, wpt_yaml.get('_lat'), wpt_yaml.get('_lon'),
                                wpt_yaml.get('ele'))
            self.name = wpt_yaml.get('name')
            self.time = wpt_yaml.get('time')
            self.comment = wpt_yaml.get('cmt')
            self.description = wpt_yaml.get('desc')
            self.symbol = wpt_yaml.get('sym')
            self.source: Optional[str] = wpt_yaml.get('src')
            self.extensions: Optional[List[Any]] = MyWaypoint.read_extensions_from_yaml(wpt_yaml.get('extensions'))

    @staticmethod
    def read_extensions(extensions: List[Any]) -> Optional[List[Any]]:
        if not extensions:
            return
        retval = []
        for extension in extensions:
            # process extension based on the type
            if WaypointExtension.match_tag(extension.tag):
                retval.append(WaypointExtension(extension))
            # future: additional supported extension type here
        return retval

    @staticmethod
    def read_extensions_from_yaml(extensions_data: Optional[List[dict]]) -> Optional[List[Any]]:
        """Read extensions from YAML data and instantiate appropriate extension objects"""
        if not extensions_data:
            return None

        retval = []
        for ext_dict in extensions_data:
            # Each extension is a dictionary with one key-value pair
            # where the key is the extension type and value is the extension data
            for ext_key, ext_value in ext_dict.items():
                # Remove namespace prefix if present (e.g., "gpxx:WaypointExtension" -> "WaypointExtension")
                clean_key = NameSpace.remove(ext_key)

                if WaypointExtension.match_tag(clean_key):
                    # Create WaypointExtension from YAML data
                    wp_ext = WaypointExtension.from_yaml(ext_value)
                    retval.append(wp_ext)
                # future: additional supported extension types here

        return retval if retval else None

    # while we support adding a namespace: prefix to yaml keys,
    # by default we don't use it for better readibility.
    # we can add them when we write the XMLs which are needed.
    def extensions_to_yaml(self, namespace: str = None):
        """
        Generate the extensions as a suitable array of yaml dictionaries.
        """
        if not self.extensions:
            return
        retval = []
        for ext in self.extensions:
            retval.append({
                # extension-name: extension as yaml representation
                NameSpace.add(namespace, ext.__class__.__name__): ext.to_yaml(namespace=namespace)
            })
        return retval

    @staticmethod
    def read_time(timestamp: Optional[str]):
        if timestamp:
            return datetime.fromisoformat(timestamp)

    def to_gpx(self) -> GPXWaypoint:
        """Convert to GPXWaypoint object"""
        wpt = GPXWaypoint(
            latitude=self.latitude,
            longitude=self.longitude,
            elevation=self.elevation,
            name=self.name,
            time=self.time,
            comment=self.comment,
            description=self.description,
            symbol=self.symbol,
        )
        wpt.source = self.source  # not in constructor
        # add extensions if any
        if self.extensions:
            for ext in self.extensions:
                wpt.extensions.append(ext.to_xml())
        return wpt

    def get_address(self) -> Optional['MyAddress']:
        """Get the address for this waypoint"""
        if self.extensions:
            for ext in self.extensions:
                if isinstance(ext, WaypointExtension):
                    return ext.address

    # we don't need a to_yaml() function for this class because it is
    # handled in the YAML representer function we register for this class.
    #
    # def to_yaml(self):
    #     # Return dictionary with fields in desired order
    #     val = {}
    #     val.update({
    #         'name': self.name,
    #         '_lat': self.latitude,
    #         '_lon': self.longitude,
    #         'ele': self.elevation,
    #         'time': self.time,
    #         'cmt': self.comment,
    #         'desc': self.description,
    #         'sym': self.symbol,
    #         'src': self.source,
    #         # Other fields in desired order
    #     })
    #     if self.extensions:
    #         val.update({'extensions': self.extensions_to_yaml()})


class MyAddress:
    """Encapsulating a gpxx::Address object"""

    def __init__(self, location: geopy.Location = None, element: ET.Element = None,
                 timezone: str = None) -> None:
        # if element is specified, initialize object from xml Element
        # by setting the corresponding tag field directly with its value
        if element:
            for child in element:
                tag = NameSpace.remove(child.tag)
                value = child.text.strip()
                if tag and value:
                    setattr(self, tag, value)
            return
        # otherwise set it from a geopy location response
        if location and location.raw:
            raw_addr = location.raw.get('address', {})  # the address dict
            # extract the relevant fields that are in the schema
            self.StreetAddress = raw_addr.get('road')
            self.City = raw_addr.get('city') or raw_addr.get('town') or raw_addr.get('municipality')
            self.State = raw_addr.get('state')
            self.Country = raw_addr.get('country')
            self.PostalCode = raw_addr.get('postcode')
            # my extra fields
            self.TimeZone = None
            self.CountryCode = raw_addr.get('country_code')
            self.LvL4 = raw_addr.get('ISO3166-2-lvl4')
            self.Address = location.address
        if timezone:
            self.TimeZone = timezone

    @classmethod
    def from_yaml(cls, yaml_data: dict):
        """Create MyAddress from YAML data"""
        instance = cls.__new__(cls)  # Create instance without calling __init__

        for key, value in yaml_data.items():
            clean_key = NameSpace.remove(key)
            if value:  # Only set non-empty values
                setattr(instance, clean_key, value)

        return instance

    def __str__(self) -> str:
        return (f"street_address={self.StreetAddress}, city={self.City}, state={self.State}, "
                f"postal_code={self.PostalCode}, country={self.Country}, country_code={self.CountryCode}, "
                f"lvl4={self.LvL4}")

    @staticmethod
    def match_tag(tag: str) -> bool:
        tag = NameSpace.remove(tag)
        return 'Address' == tag

    def to_xml(self):
        val = ET.Element(NameSpace.add('gpxx', 'Address'))

        for attr_name, attr_value in self.__dict__.items():
            if attr_value:
                element_tag = NameSpace.add('gpxx', attr_name)
                ET.SubElement(val, element_tag).text = str(attr_value)

        return val

    # value of Address Object
    def to_yaml(self, namespace: str = None):
        # Return dictionary with fields in desired order
        return {
            NameSpace.add(namespace, key): value
            for key, value in self.__dict__.items()
            if value
        }


class WaypointExtension:
    address: MyAddress

    def __init__(self, extension: ET.Element = None, address: MyAddress = None) -> None:
        """
        :param extension: xml element where we can read data from
        :param address: already constructed MyAddress value
        """
        if address:
            self.address = address
        elif extension:
            for child in extension:
                tag = NameSpace.remove(child.tag)
                # process the list of supported childs, Address only for now
                if MyAddress.match_tag(tag):
                    self.address = MyAddress(element=child)

    @classmethod
    def from_yaml(cls, yaml_data: dict):
        """Create WaypointExtension from YAML data"""
        instance = cls.__new__(cls)  # Create instance without calling __init__

        for key, value in yaml_data.items():
            clean_key = NameSpace.remove(key)
            if MyAddress.match_tag(clean_key):
                instance.address = MyAddress.from_yaml(value)
            # future: additional supported nested objects here

        return instance

    @staticmethod
    def match_tag(tag: str) -> bool:
        # we skip wptx1: since it's a duplicate of gpxx: which we use
        if tag.startswith(SKIP_TAGS_WPTX1):
            return False
        tag = NameSpace.remove(tag)
        return 'WaypointExtension' == tag

    # { WaypointExtension: ... }
    def to_yaml(self, namespace: str = None):
        return {
            NameSpace.add(namespace, 'Address'): self.address.to_yaml(namespace=namespace)
        }

    def to_xml(self):
        val = ET.Element('gpxx:WaypointExtension')
        if hasattr(self, 'address') and self.address:
            val.append(self.address.to_xml())
        return val


class MyWidthTracker:
    """Tracks max width of each field so we can align when printing"""

    def __init__(self):
        self._counter = 0  # internal counter
        self.count = 0
        self.name = 0
        self.latitude = 0
        self.longitude = 0
        self.elevation = 0
        self.description = 0
        self.time = 0
        self.timezone = 0

    def update(self, waypoint: GPXWaypoint):
        """update the max values based on this new waypoint"""
        self._counter += 1
        self.count = max(self.count, len(str(self._counter)))
        self.name = max(self.name, len(waypoint.name))
        self.latitude = max(self.latitude, len(str(waypoint.latitude)))
        self.longitude = max(self.longitude, len(str(waypoint.longitude)))
        self.elevation = max(self.elevation, len(str(waypoint.elevation)))
        self.description = max(self.description, MyWidthTracker.field_len(waypoint.description))
        self.time = max(self.time, len(str(waypoint.time)))
        # self.timezone = max(self.timezone, len(waypoint.))

    @staticmethod
    def field_len(field):
        if field:
            return len(field)
        else:
            return 0

    def print_wp(self, i: int, waypoint: GPXWaypoint, timezone: bool):
        """print the waypoint justified with max width appropriately"""
        pass


def my_waypoint_representer(dumper: yaml.Dumper, data: MyWaypoint) -> yaml.Node:
    """
    Custom YAML representer for MyWaypoint objects.
    Only includes non-null fields in the output.
    """
    # Create a dictionary with all possible fields in the order we want
    waypoint_dict = {
        'name': data.name,
        '_lat': data.latitude,
        '_lon': data.longitude,
        'ele': data.elevation,
        'time': data.time,
#        'timezone': getattr(data, 'timezone', None),
        'cmt': data.comment,
        'desc': data.description,
        'sym': data.symbol,
        'src': data.source,
        'extensions': data.extensions_to_yaml(namespace=None)
    }

    # Remove None values and empty strings for cleaner output
    waypoint_dict = {k: v for k, v in waypoint_dict.items()
                     if v is not None and v != ''}

    return dumper.represent_dict(waypoint_dict)


yaml.add_representer(MyWaypoint, my_waypoint_representer)
