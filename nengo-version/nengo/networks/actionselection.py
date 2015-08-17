import warnings

import numpy as np

import nengo
from nengo.solvers import NnlsL2nz
from nengo.networks.ensemblearray import EnsembleArray
from nengo.utils.distributions import Uniform


class BasalGanglia(nengo.Network):
    """Winner takes all; outputs 0 at max dimension, negative elsewhere."""

    # connection weights from (Gurney, Prescott, & Redgrave, 2001)
    mm = 1
    mp = 1
    me = 1
    mg = 1
    ws = 1
    wt = 1
    wm = 1
    wg = 1
    wp = 0.9
    we = 0.3
    e = 0.2
    ep = -0.25
    ee = -0.2
    eg = -0.2
    le = 0.2
    lg = 0.2

    def __init__(self, dimensions, n_neurons_per_ensemble=100, radius=1.5,
                 tau_ampa=0.002, tau_gaba=0.008, output_weight=-3,
                 input_bias=0.0, solver=None):
        if solver is None:
            try:
                # Best, if we have SciPy
                solver = NnlsL2nz()
            except ImportError:
                # If not, use default
                warnings.warn("SciPy is not installed, so BasalGanglia will "
                              "use default decoder solver. Installing SciPy "
                              "may improve BasalGanglia performance.")
                solver = nengo.Default
        encoders = np.ones((n_neurons_per_ensemble, 1))
        ea_params = {
            'n_neurons': n_neurons_per_ensemble,
            'n_ensembles': dimensions,
            'radius': radius,
            'encoders': encoders,
        }

        self.strD1 = EnsembleArray(label="Striatal D1 neurons",
                                   intercepts=Uniform(self.e, 1), **ea_params)

        self.strD2 = EnsembleArray(label="Striatal D2 neurons",
                                   intercepts=Uniform(self.e, 1), **ea_params)

        self.stn = EnsembleArray(label="Subthalamic nucleus",
                                 intercepts=Uniform(self.ep, 1), **ea_params)

        self.gpi = EnsembleArray(label="Globus pallidus internus",
                                 intercepts=Uniform(self.eg, 1), **ea_params)

        self.gpe = EnsembleArray(label="Globus pallidus externus",
                                 intercepts=Uniform(self.ee, 1), **ea_params)

        self.input = nengo.Node(label="input", size_in=dimensions)
        self.output = nengo.Node(label="output", size_in=dimensions)

        # add bias input (BG performs best in the range 0.5--1.5)
        if abs(input_bias) > 0.0:
            self.bias_input = nengo.Node([input_bias] * dimensions)
            nengo.Connection(self.bias_input, self.input)

        # spread the input to StrD1, StrD2, and STN
        nengo.Connection(self.input, self.strD1.input, synapse=None,
                         transform=self.ws * (1 + self.lg))
        nengo.Connection(self.input, self.strD2.input, synapse=None,
                         transform=self.ws * (1 - self.le))
        nengo.Connection(self.input, self.stn.input, synapse=None,
                         transform=self.wt)

        # connect the striatum to the GPi and GPe (inhibitory)
        strD1_output = self.strD1.add_output(
            'func_str', self.str_func, solver=solver)
        nengo.Connection(strD1_output,
                         self.gpi.input, synapse=tau_gaba,
                         transform=-np.eye(dimensions) * self.wm)
        strD2_output = self.strD2.add_output(
            'func_str', self.str_func, solver=solver)
        nengo.Connection(strD2_output,
                         self.gpe.input, synapse=tau_gaba,
                         transform=-np.eye(dimensions) * self.wm)

        # connect the STN to GPi and GPe (broad and excitatory)
        tr = self.wp * np.ones((dimensions, dimensions))
        stn_output = self.stn.add_output(
            'func_stn', self.stn_func, solver=solver)
        nengo.Connection(stn_output, self.gpi.input,
                         transform=tr, synapse=tau_ampa)
        nengo.Connection(stn_output, self.gpe.input,
                         transform=tr, synapse=tau_ampa)

        # connect the GPe to GPi and STN (inhibitory)
        gpe_output = self.gpe.add_output(
            'func_gpe', self.gpe_func, solver=solver)
        nengo.Connection(gpe_output, self.gpi.input, synapse=tau_gaba,
                         transform=-self.we)
        nengo.Connection(gpe_output, self.stn.input, synapse=tau_gaba,
                         transform=-self.wg)

        # connect GPi to output (inhibitory)
        gpi_output = self.gpi.add_output(
            'func_gpi', self.gpi_func, solver=solver)
        nengo.Connection(gpi_output, self.output, synapse=None,
                         transform=output_weight)

    @classmethod
    def str_func(cls, x):
        if x < cls.e:
            return 0
        return cls.mm * (x - cls.e)

    @classmethod
    def stn_func(cls, x):
        if x < cls.ep:
            return 0
        return cls.mp * (x - cls.ep)

    @classmethod
    def gpe_func(cls, x):
        if x < cls.ee:
            return 0
        return cls.me * (x - cls.ee)

    @classmethod
    def gpi_func(cls, x):
        if x < cls.eg:
            return 0
        return cls.mg * (x - cls.eg)


class Thalamus(nengo.Network):
    """Converts basal ganglia output into a signal with
    (approximately) 1 for the selected action and 0 elsewhere."""

    def __init__(self, dimensions, n_neurons_per_ensemble=50, mutual_inhib=1,
                 threshold=0):
        self.actions = EnsembleArray(n_neurons_per_ensemble, dimensions,
                                     intercepts=Uniform(threshold, 1),
                                     encoders=[[1]] * n_neurons_per_ensemble,
                                     label="actions")

        self.input = self.actions.input
        self.output = self.actions.output

        nengo.Connection(self.actions.output, self.actions.input,
                         transform=(np.eye(dimensions) - 1) * mutual_inhib)

        self.bias = nengo.Node([1])
        nengo.Connection(self.bias, self.actions.input,
                         transform=[[1]] * dimensions)
