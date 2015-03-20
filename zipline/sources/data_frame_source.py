
#
# Copyright 2013 Quantopian, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tools to generate data sources.
"""
import pandas as pd

from zipline.gens.utils import hash_args

from zipline.sources.data_source import DataSource
from zipline.protocol import WideTradeEvent


class DataFrameSource(DataSource):
    """
    Yields all events in event_list that match the given sid_filter.
    If no event_list is specified, generates an internal stream of events
    to filter.  Returns all events if filter is None.

    Configuration options:

    sids   : list of values representing simulated internal sids
    start  : start date
    delta  : timedelta between internal events
    filter : filter to remove the sids
    """

    def __init__(self, data, **kwargs):
        assert isinstance(data.index, pd.tseries.index.DatetimeIndex)

        self.data = data
        # Unpack config dictionary with default values.
        self.sids = kwargs.get('sids', data.columns)
        self.start = kwargs.get('start', data.index[0])
        self.end = kwargs.get('end', data.index[-1])

        # Hash_value for downstream sorting.
        self.arg_string = hash_args(data, **kwargs)

        self._raw_data = None

    @property
    def mapping(self):
        return {
            'dt': (lambda x: x, 'dt'),
            'sid': (lambda x: x, 'sid'),
            'price': (float, 'price'),
            'volume': (int, 'volume'),
        }

    @property
    def instance_hash(self):
        return self.arg_string

    def raw_data_gen(self):
        for dt, series in self.data.iterrows():
            for sid, price in series.iteritems():
                if sid in self.sids:
                    event = {
                        'dt': dt,
                        'sid': sid,
                        'price': price,
                        # Just chose something large
                        # if no volume available.
                        'volume': 1e9,
                    }
                    yield event

    @property
    def raw_data(self):
        if not self._raw_data:
            self._raw_data = self.raw_data_gen()
        return self._raw_data


class DataPanelSource(DataSource):
    """
    Yields all events in event_list that match the given sid_filter.
    If no event_list is specified, generates an internal stream of events
    to filter.  Returns all events if filter is None.

    Configuration options:

    sids   : list of values representing simulated internal sids
    start  : start date
    delta  : timedelta between internal events
    filter : filter to remove the sids
    """

    def __init__(self, data, **kwargs):
        assert isinstance(data.major_axis, pd.tseries.index.DatetimeIndex)

        self.data = data
        # Unpack config dictionary with default values.
        self.sids = kwargs.get('sids', data.items)
        self.start = kwargs.get('start', data.major_axis[0])
        self.end = kwargs.get('end', data.major_axis[-1])

        # Hash_value for downstream sorting.
        self.arg_string = hash_args(data, **kwargs)

        self.it = self.mapped_data

    @property
    def instance_hash(self):
        return self.arg_string

    @property
    def raw_data(self):
        pass

    @property
    def mapped_data(self):
        # currently volume is same dtype as prices, float64
        values = self.data.values
        major_axis = self.data.major_axis
        minor_axis = self.data.minor_axis
        items = self.data.items
        source_id = self.get_hash()

        evt = WideTradeEvent()
        evt.sids = items
        evt.sids_set = set(items)
        evt.columns = minor_axis

        for i, dt in enumerate(major_axis):
            df = values[:, i, :]
            evt.vals = df
            evt.dt = dt
            evt.source_id = source_id
            yield evt

    def __iter__(self):
        return self.it

    def next(self):
        return self.it.next()

    def __next__(self):
        return next(self.it)