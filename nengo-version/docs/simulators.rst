==========
Simulators
==========

The more Nengo simulators the better.
We provide the reference simulator,
but it is easy to use another simulator,
as long as it implements the same interface
as ``nengo.simulator.Simulator``.

TODO more?

Unit testing
============

We provide some helpers to make unit testing easier
for simulator developers.

.. autofunction:: nengo.tests.helpers.load_nengo_tests

.. autofunction:: nengo.tests.helpers.simulator_test_suite

.. autoclass:: nengo.tests.helpers.NengoTestLoader
   :members:
