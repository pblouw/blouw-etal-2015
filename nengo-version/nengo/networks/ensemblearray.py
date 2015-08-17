import warnings

import numpy as np

import nengo
from nengo.utils.compat import range
from nengo.utils.network import with_self


class EnsembleArray(nengo.Network):

    def __init__(self, n_neurons, n_ensembles, ens_dimensions=1,
                 neuron_nodes=False, label=None, **ens_kwargs):
        if "dimensions" in ens_kwargs:
            raise TypeError(
                "'dimensions' is not a valid argument to EnsembleArray. "
                "To set the number of ensembles, use 'n_ensembles'. To set "
                "the number of dimensions per ensemble, use 'ens_dimensions'.")

        self.config[nengo.Ensemble].update(ens_kwargs)

        label_prefix = "" if label is None else label + "_"

        self.n_neurons = n_neurons
        self.n_ensembles = n_ensembles
        self.dimensions_per_ensemble = ens_dimensions

        self.input = nengo.Node(size_in=self.dimensions, label="input")

        if neuron_nodes:
            self.neuron_input = nengo.Node(size_in=n_neurons * n_ensembles,
                                           label="neuron_input")
            self.neuron_output = nengo.Node(size_in=n_neurons * n_ensembles,
                                            label="neuron_output")

        self.ea_ensembles = []
        for i in range(n_ensembles):
            e = nengo.Ensemble(
                n_neurons, self.dimensions_per_ensemble,
                label=label_prefix + str(i))

            nengo.Connection(self.input[i * ens_dimensions:
                                        (i + 1) * ens_dimensions],
                             e, synapse=None)

            if neuron_nodes and not isinstance(e.neuron_type, nengo.Direct):
                nengo.Connection(self.neuron_input[i * n_neurons:
                                                   (i + 1) * n_neurons],
                                 e.neurons, synapse=None)
                nengo.Connection(e.neurons,
                                 self.neuron_output[i * n_neurons:
                                                    (i + 1) * n_neurons],
                                 synapse=None)

            self.ea_ensembles.append(e)

        if neuron_nodes and isinstance(e.neuron_type, nengo.Direct):
            warnings.warn("Creating neuron nodes in an EnsembleArray"
                          " with Direct neurons")

        self.add_output('output', function=None)

    @with_self
    def add_output(self, name, function, synapse=None, **conn_kwargs):
        if function is None:
            function_d = self.dimensions_per_ensemble
        else:
            func_output = function(np.zeros(self.dimensions_per_ensemble))
            function_d = np.asarray(func_output).size

        dim = self.n_ensembles * function_d
        output = nengo.Node(output=None, size_in=dim, label=name)
        setattr(self, name, output)

        for i, e in enumerate(self.ea_ensembles):
            nengo.Connection(
                e, output[i * function_d:(i + 1) * function_d],
                function=function, synapse=synapse, **conn_kwargs)
        return output

    @property
    def dimensions(self):
        return self.n_ensembles * self.dimensions_per_ensemble
