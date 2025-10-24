# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from AlgorithmImports import *

### <summary>
### Minimal Futures Test Algorithm - Quick compilation test
### </summary>
class MinimalFuturesTestAlgorithm(QCAlgorithm):
    '''Minimal futures algorithm for testing compilation'''

    def initialize(self):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.'''

        self.set_start_date(2023, 1, 1)
        self.set_end_date(2023, 1, 31)
        self.set_cash(100000)

        # Add ES futures (E-mini S&P 500)
        self._future = self.add_future(Futures.Indices.SP_500_E_MINI, Resolution.MINUTE)
        
        # Simple moving average for testing
        self._sma = self.sma(self._future.symbol, 10, Resolution.MINUTE)

    def on_data(self, data):
        '''OnData event is the primary entry point for your algorithm.'''
        
        # Simple logic: buy when price is above SMA, sell when below
        if not self._sma.is_ready:
            return
            
        if not self.portfolio.invested:
            if self.securities[self._future.symbol].price > self._sma.current.value:
                self.buy(self._future.symbol, 1)
        else:
            if self.securities[self._future.symbol].price < self._sma.current.value:
                self.liquidate()

    def on_order_event(self, order_event):
        self.debug(f"{self.time} - Order Event: {order_event}")