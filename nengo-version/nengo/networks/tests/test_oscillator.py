import logging

import pytest

import nengo
from nengo.utils.functions import piecewise
from nengo.utils.numpy import rmse
from nengo.utils.testing import Plotter


logger = logging.getLogger(__name__)


def test_oscillator(Simulator, nl):
    model = nengo.Network(label='Oscillator', seed=789)
    with model:
        model.config[nengo.Ensemble].neuron_type = nl()
        inputs = {0: [1, 0], 0.5: [0, 0]}
        input = nengo.Node(piecewise(inputs), label='Input')

        tau = 0.1
        freq = 5
        T = nengo.networks.Oscillator(
            tau, freq, label="Oscillator", n_neurons=100)
        nengo.Connection(input, T.input)

        A = nengo.Ensemble(100, dimensions=2)
        nengo.Connection(A, A, synapse=tau,
                         transform=[[1, -freq*tau], [freq*tau, 1]])
        nengo.Connection(input, A)

        in_probe = nengo.Probe(input)
        A_probe = nengo.Probe(A, synapse=0.01)
        T_probe = nengo.Probe(T.ensemble, synapse=0.01)

    sim = Simulator(model)
    sim.run(3.0)

    with Plotter(Simulator, nl) as plt:
        t = sim.trange()
        plt.plot(t, sim.data[A_probe], label='Manual')
        plt.plot(t, sim.data[T_probe], label='Template')
        plt.plot(t, sim.data[in_probe], 'k', label='Input')
        plt.legend(loc=0)
        plt.savefig('test_oscillator.test_oscillator.pdf')
        plt.close()

    assert rmse(sim.data[A_probe], sim.data[T_probe]) < 0.3


if __name__ == "__main__":
    nengo.log(debug=True)
    pytest.main([__file__, '-v'])
