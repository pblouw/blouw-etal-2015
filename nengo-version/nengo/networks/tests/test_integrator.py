import logging

import pytest

import nengo
from nengo.utils.functions import piecewise
from nengo.utils.numpy import rmse
from nengo.utils.testing import Plotter

logger = logging.getLogger(__name__)


def test_integrator(Simulator, nl):
    model = nengo.Network(label='Integrator', seed=892)
    with model:
        model.config[nengo.Ensemble].neuron_type = nl()
        inputs = {0: 0, 0.2: 1, 1: 0, 2: -2, 3: 0, 4: 1, 5: 0}
        input = nengo.Node(piecewise(inputs))

        tau = 0.1
        T = nengo.networks.Integrator(tau, n_neurons=100, dimensions=1)
        nengo.Connection(input, T.input, synapse=tau)

        A = nengo.Ensemble(100, dimensions=1)
        nengo.Connection(A, A, synapse=tau)
        nengo.Connection(input, A, transform=tau, synapse=tau)

        input_p = nengo.Probe(input)
        A_p = nengo.Probe(A, synapse=0.01)
        T_p = nengo.Probe(T.ensemble, synapse=0.01)

    sim = Simulator(model, dt=0.001)
    sim.run(6.0)

    with Plotter(Simulator, nl) as plt:
        t = sim.trange()
        plt.plot(t, sim.data[A_p], label='Manual')
        plt.plot(t, sim.data[T_p], label='Template')
        plt.plot(t, sim.data[input_p], 'k', label='Input')
        plt.legend(loc=0)
        plt.savefig('test_integrator.test_integrator.pdf')
        plt.close()

    assert rmse(sim.data[A_p], sim.data[T_p]) < 0.2


if __name__ == "__main__":
    nengo.log(debug=True)
    pytest.main([__file__, '-v'])
