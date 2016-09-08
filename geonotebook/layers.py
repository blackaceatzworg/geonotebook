from config import Config
from collections import namedtuple
import rasterio
import numpy as np

BBox = namedtuple('BBox', ['ulx', 'uly', 'lrx', 'lry'])

# Note:  GeonotebookLayers must support instances where data is
#        None. This allows us to use a consistent interface for things
#        like the OSM base layer,  or more generally for tile server URLs
#        that don't have any (accessible) data associated with them.
class GeonotebookLayer(object):
    def __init__(self, name, vis_url=None, band_collection=None, **kwargs):
        self.config = Config()
        self.name = name
        self.vis_url = vis_url
        self.band_collection = band_collection
        self._region = None

        assert vis_url is not None or band_collection is not None, \
            "Must pass in vis_url or band_collection to {}".format(
                self.__class__.__name__)

        if band_collection is not None and vis_url is None:
            self.vis_url = self.config.vis_server.ingest(
                self.band_collection.data, name=self.name)

        self.params = self.config.vis_server.get_params(
            self.name, band_collection, **kwargs)

    @property
    def region(self):
        if self.data is None:
            return None

        (ulx, uly), (lrx, lry) = self.data.index(self._region.ulx, self._region.uly), \
            self.data.index(self._region.lrx, self._region.lry)

        if self.data.count == 1:
            return self.data.read(1, window=((ulx, lrx), (uly, lry)))
        else:
            return np.stack(self.data.read(
                window=((ulx, lrx), (uly, lry))), axis=2)


    @region.setter
    def region(self, value):
        assert isinstance(value, BBox), \
            "Region must be set to a value of type BBox"

        self._region = value

    def __repr__(self):
        return "<{}('{}')>".format(
            self.__class__.__name__, self.name)

# GeonotebookStack supports dict-like indexing on a list
# of Geonotebook Layers. We could implement this with an
# OrderedDict,  but i think we are eventually going to want
# to support re-ordering,  potentially serializing etc so it
# Seems like putting it in its own class is best for now.

# TODO: support slices other list functionality etc
class GeonotebookStack(object):
    def __init__(self, layers=None):
        if layers is not None:
            for l in layers:
                assert isinstance(l, GeonotebookLayer), \
                    "{} is not a GeonotebookLayer".format(l)
            self._layers = layers
        else:
            self._layers = []

    def __repr__(self):
        return "GeonotebookStack({})".format(self._layers.__repr__())

    def find(self, predicate):
        """Find first GeonotebookLayer that matches predicate. If predicate
        is not callable it will check predicate against each layer name."""

        if not hasattr(predicate, '__call__'):
            name = predicate
            predicate = lambda l: l.name == name

        try:
            return next(l for l in self._layers if predicate(l))
        except StopIteration:
            return None

    def indexOf(self, predicate):
        if not hasattr(predicate, '__call__'):
            name = predicate
            predicate = lambda l: l.name == name
        try:
            return next(i for i,l in enumerate(self._layers) if predicate(l))
        except StopIteration:
            return None


    def remove(self, value):
        if isinstance(value, basestring):
            idx = self.indexOf(value)
            if idx is not None:
                return self.remove(idx)
            else:
                raise KeyError('{}'.format(value))
        else:
            del self._layers[value]

    def append(self, value):
        if isinstance(value, GeonotebookLayer):
            if self.find(value.name) is None:
                self._layers.append(value)
            else:
                raise Exception("There is already a layer named {}".format(value.name))

        else:
            raise Exception("Can only append GeonotebookLayer to Stack")

    def __getitem__(self, value):
        if isinstance(value, basestring):
            idx = self.indexOf(value)
            if idx is not None:
                return self.__getitem__(idx)
            else:
                raise KeyError('{}'.format(value))
        else:
            return self._layers.__getitem__(value)

    def __setitem__(self, index, value):
        if isinstance(value, GeonotebookLayer):
            if isinstance(index, basestring):
                idx = self.indexOf(index)
                if idx is not None:
                    self.__setitem__(idx, value)
                else:
                    raise KeyError('{}'.format(value.name))
            else:
                self._layers.__setitem__(index, value)
        else:
            raise Exception("Can only append GeonotebookLayer to Stack")