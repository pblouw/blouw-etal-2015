import logging

import numpy as np
import pytest

import nengo
import nengo.simulator
from nengo.builder import (
    Model, ProdUpdate, Copy, Reset, DotInc, Signal, build_pyfunc)
from nengo.solvers import LstsqL2nz
from nengo.utils.compat import range
from nengo.utils.functions import whitenoise


logger = logging.getLogger(__name__)


def test_steps(RefSimulator):
    m = nengo.Network(label="test_steps")
    sim = RefSimulator(m)
    assert sim.n_steps == 0
    sim.step()
    assert sim.n_steps == 1
    sim.step()
    assert sim.n_steps == 2


def test_time_steps(RefSimulator):
    m = nengo.Network(label="test_time_steps")
    sim = RefSimulator(m)
    assert np.allclose(sim.signals["__time__"], 0.00)
    sim.step()
    assert np.allclose(sim.signals["__time__"], 0.001)
    sim.step()
    assert np.allclose(sim.signals["__time__"], 0.002)


def test_time_absolute(Simulator):
    m = nengo.Network(label="test_time_absolute", seed=123)
    sim = Simulator(m)
    sim.run(0.003)
    assert np.allclose(sim.trange(), [0.00, .001, .002])


def test_trange_with_probes(Simulator):
    dt = 1e-3
    m = nengo.Network()
    periods = dt * np.arange(1, 21)
    with m:
        u = nengo.Node(output=np.sin)
        probes = [nengo.Probe(u, sample_every=p, synapse=5*p) for p in periods]

    sim = Simulator(m, dt=dt)
    sim.run(0.333)
    for i, p in enumerate(periods):
        assert len(sim.trange(p)) == len(sim.data[probes[i]])


def test_signal_indexing_1(RefSimulator):
    one = Signal(np.zeros(1), name="a")
    two = Signal(np.zeros(2), name="b")
    three = Signal(np.zeros(3), name="c")
    tmp = Signal(np.zeros(3), name="tmp")

    m = Model(dt=0.001)
    m.operators += [
        ProdUpdate(
            Signal(1, name="A1"), three[:1], Signal(0, name="Z0"), one),
        ProdUpdate(
            Signal(2.0, name="A2"), three[1:], Signal(0, name="Z1"), two),
        Reset(tmp),
        DotInc(
            Signal([[0, 0, 1], [0, 1, 0], [1, 0, 0]], name="A3"), three, tmp),
        Copy(src=tmp, dst=three, as_update=True),
    ]

    sim = RefSimulator(None, model=m)
    sim.signals[three] = np.asarray([1, 2, 3])
    sim.step()
    assert np.all(sim.signals[one] == 1)
    assert np.all(sim.signals[two] == [4, 6])
    assert np.all(sim.signals[three] == [3, 2, 1])
    sim.step()
    assert np.all(sim.signals[one] == 3)
    assert np.all(sim.signals[two] == [4, 2])
    assert np.all(sim.signals[three] == [1, 2, 3])


def test_simple_pyfunc(RefSimulator):
    dt = 0.001
    time = Signal(np.zeros(1), name="time")
    sig = Signal(np.zeros(1), name="sig")
    m = Model(dt=dt)
    sig_in, sig_out = build_pyfunc(lambda t, x: np.sin(x), True, 1, 1, None, m)
    m.operators += [
        ProdUpdate(Signal(dt), Signal(1), Signal(1), time),
        DotInc(Signal([[1.0]]), time, sig_in),
        ProdUpdate(Signal([[1.0]]), sig_out, Signal(0), sig),
    ]

    sim = RefSimulator(None, model=m)
    sim.step()
    for i in range(5):
        sim.step()
        t = (i + 2) * dt
        assert np.allclose(sim.signals[time], t)
        assert np.allclose(sim.signals[sig], np.sin(t - dt*2))


def test_encoder_decoder_pathway(RefSimulator):
    """Verifies (like by hand) that the simulator does the right
    things in the right order."""
    foo = Signal([1.0], name="foo")
    decoders = np.asarray([.2, .1])
    decs = Signal(decoders * 0.5)
    m = Model(dt=0.001)
    sig_in, sig_out = build_pyfunc(lambda t, x: x + 1, True, 2, 2, None, m)
    m.operators += [
        DotInc(Signal([[1.0], [2.0]]), foo, sig_in),
        ProdUpdate(decs, sig_out, Signal(0.2), foo)
    ]

    def check(sig, target):
        assert np.allclose(sim.signals[sig], target)

    sim = RefSimulator(None, model=m)

    check(foo, 1.0)
    check(sig_in, 0)
    check(sig_out, 0)

    sim.step()
    # DotInc to pop.input_signal (input=[1.0,2.0])
    # produpdate updates foo (foo=[0.2])
    # pop updates pop.output_signal (output=[2,3])

    check(sig_in, [1, 2])
    check(sig_out, [2, 3])
    check(foo, .2)
    check(decs, [.1, .05])

    sim.step()
    # DotInc to pop.input_signal (input=[0.2,0.4])
    #  (note that pop resets its own input signal each timestep)
    # produpdate updates foo (foo=[0.39]) 0.2*0.5*2+0.1*0.5*3 + 0.2*0.2
    # pop updates pop.output_signal (output=[1.2,1.4])

    check(decs, [.1, .05])
    check(sig_in, [0.2, 0.4])
    check(sig_out, [1.2, 1.4])
    # -- foo is computed as a prodUpdate of the *previous* output signal
    #    foo <- .2 * foo + dot(decoders * .5, output_signal)
    #           .2 * .2  + dot([.2, .1] * .5, [2, 3])
    #           .04      + (.2 + .15)
    #        <- .39
    check(foo, .39)


def test_encoder_decoder_with_views(RefSimulator):
    foo = Signal([1.0], name="foo")
    decoders = np.asarray([.2, .1])
    m = Model(dt=0.001)
    sig_in, sig_out = build_pyfunc(lambda t, x: x + 1, True, 2, 2, None, m)
    m.operators += [
        DotInc(Signal([[1.0], [2.0]]), foo[:], sig_in),
        ProdUpdate(Signal(decoders * 0.5), sig_out, Signal(0.2), foo[:])
    ]

    def check(sig, target):
        assert np.allclose(sim.signals[sig], target)

    sim = RefSimulator(None, model=m)

    sim.step()
    # DotInc to pop.input_signal (input=[1.0,2.0])
    # produpdate updates foo (foo=[0.2])
    # pop updates pop.output_signal (output=[2,3])

    check(foo, .2)
    check(sig_in, [1, 2])
    check(sig_out, [2, 3])

    sim.step()
    # DotInc to pop.input_signal (input=[0.2,0.4])
    #  (note that pop resets its own input signal each timestep)
    # produpdate updates foo (foo=[0.39]) 0.2*0.5*2+0.1*0.5*3 + 0.2*0.2
    # pop updates pop.output_signal (output=[1.2,1.4])

    check(foo, .39)
    check(sig_in, [0.2, 0.4])
    check(sig_out, [1.2, 1.4])


def test_probedict():
    """Tests simulator.ProbeDict's implementation."""
    raw = {"scalar": 5,
           "list": [2, 4, 6]}
    probedict = nengo.simulator.ProbeDict(raw)
    assert np.all(probedict["scalar"] == np.asarray(raw["scalar"]))
    assert np.all(probedict.get("list") == np.asarray(raw.get("list")))


def test_reset(Simulator, nl_nodirect):
    """Make sure resetting actually resets.

    A learning network on weights is used as the example network as the
    ultimate stress test; lots of weird stuff happens during learning, but
    if we're able to reset back to initial connection weights and everything
    then we're probably doing resetting right.
    """
    noise = whitenoise(0.1, 5, dimensions=2, seed=328)
    m = nengo.Network(seed=3902)
    with m:
        m.config[nengo.Ensemble].neuron_type = nl_nodirect()
        u = nengo.Node(output=noise)
        ens = nengo.Ensemble(200, dimensions=2)
        error = nengo.Ensemble(200, dimensions=2)
        square = nengo.Ensemble(200, dimensions=2)

        nengo.Connection(u, ens)
        nengo.Connection(u, error)
        nengo.Connection(square, error, transform=-1)
        err_conn = nengo.Connection(error, square, modulatory=True)
        nengo.Connection(ens, square,
                         learning_rule=[nengo.PES(err_conn), nengo.BCM()],
                         solver=LstsqL2nz(weights=True))

        square_p = nengo.Probe(square, synapse=0.1)
        err_p = nengo.Probe(error, synapse=0.1)

    sim = Simulator(m)
    sim.run(0.2)
    sim.run(0.6)

    first_t = sim.trange()
    first_square_p = np.array(sim.data[square_p], copy=True)
    first_err_p = np.array(sim.data[err_p], copy=True)

    sim.reset()
    sim.run(0.8)

    assert np.all(sim.trange() == first_t)
    assert np.all(sim.data[square_p] == first_square_p)
    assert np.all(sim.data[err_p] == first_err_p)


if __name__ == "__main__":
    nengo.log(debug=True)
    pytest.main([__file__, "-v"])
