import numpy as np

import nengo
from nengo.networks.ensemblearray import EnsembleArray


class Product(nengo.Network):
    """Computes the element-wise product of two equally sized vectors."""

    def __init__(self, n_neurons, dimensions,
                 radius=1, encoders=nengo.Default, **ens_kwargs):
        self.config[nengo.Ensemble].update(ens_kwargs)
        self.A = nengo.Node(size_in=dimensions, label="A")
        self.B = nengo.Node(size_in=dimensions, label="B")
        self.output = nengo.Node(size_in=dimensions, label="output")
        self.dimensions = dimensions

        if encoders is nengo.Default:
            encoders = np.tile(
                [[1, 1], [1, -1], [-1, 1], [-1, -1]],
                ((n_neurons // 4) + 1, 1))[:n_neurons]

        self.product = EnsembleArray(
            n_neurons, n_ensembles=dimensions, ens_dimensions=2,
            encoders=encoders, radius=np.sqrt(2) * radius)

        nengo.Connection(
            self.A, self.product.input[::2], synapse=None)
        nengo.Connection(
            self.B, self.product.input[1::2], synapse=None)

        nengo.Connection(
            self.product.add_output('product', lambda x: x[0] * x[1]),
            self.output, synapse=None)

    def dot_product_transform(self, scale=1.0):
        """Returns a transform for output to compute the scaled dot product."""
        return scale*np.ones((1, self.dimensions))
