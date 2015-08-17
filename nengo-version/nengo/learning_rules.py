from nengo.params import Parameter
from nengo.utils.compat import is_iterable


class LearningRule(object):
    """Base class for all learning rule objects.

    To use a learning rule, pass it as a ``learning_rule`` keyword argument to
    the Connection on which you want to do learning.
    """

    def __init__(self, learning_rate=1.0):
        self.learning_rate = learning_rate

    def __str__(self):
        return self.__class__.__name__


class PES(LearningRule):
    """Prescribed Error Sensitivity Learning Rule

    Modifies a connection's decoders to minimize an error signal.

    Parameters
    ----------
    error : NengoObject
        The Node, Ensemble, or Neurons providing the error signal. Must be
        connectable to the post-synaptic object that is being used for this
        learning rule.
    learning_rate : float, optional
        A scalar indicating the rate at which decoders will be adjusted.
        Defaults to 1e-5.

    Attributes
    ----------
    learning_rate : float
        The given learning rate.
    error_connection : Connection
        The modulatory connection created to project the error signal.
    """

    modifies = ['Ensemble', 'Neurons']

    def __init__(self, error_connection, learning_rate=1.0):
        self.error_connection = error_connection
        super(PES, self).__init__(learning_rate)


class BCM(LearningRule):
    """Bienenstock-Cooper-Munroe learning rule

    Modifies connection weights.

    Parameters
    ----------
    learning_rate : float, optional
        A scalar indicating the rate at which decoders will be adjusted.
        Defaults to 1e-5.
    theta_tau : float, optional
        A scalar indicating the time constant for theta integration.
    pre_tau : float, optional
        Filter constant on activities of neurons in pre population.
    post_tau : float, optional
        Filter constant on activities of neurons in post population.

    Attributes
    ----------
    TODO
    """

    modifies = ['Neurons']

    def __init__(self, pre_tau=0.005, post_tau=None, theta_tau=1.0,
                 learning_rate=1.0):
        self.theta_tau = theta_tau
        self.pre_tau = pre_tau
        self.post_tau = post_tau if post_tau is not None else pre_tau
        super(BCM, self).__init__(learning_rate)


class Oja(LearningRule):
    """Oja's learning rule

    Modifies connection weights.

    Parameters
    ----------
    learning_rate : float, optional
        A scalar indicating the rate at which decoders will be adjusted.
        Defaults to 1e-5.
    beta : float, optional
        A scalar governing the amount of forgetting. Larger => more forgetting.
    pre_tau : float, optional
        Filter constant on activities of neurons in pre population.
    post_tau : float, optional
        Filter constant on activities of neurons in post population.

    Attributes
    ----------
    TODO
    """

    modifies = ['Neurons']

    def __init__(self, pre_tau=0.005, post_tau=None, beta=1.0,
                 learning_rate=1.0):
        self.pre_tau = pre_tau
        self.post_tau = post_tau if post_tau is not None else pre_tau
        self.beta = beta
        super(Oja, self).__init__(learning_rate)


class LearningRuleParam(Parameter):
    def validate(self, instance, rule):
        if is_iterable(rule):
            for lr in rule:
                self.validate_rule(instance, lr)
        elif rule is not None:
            self.validate_rule(instance, rule)
        super(LearningRuleParam, self).validate(instance, rule)

    def validate_rule(self, instance, rule):
        if not isinstance(rule, LearningRule):
            raise ValueError("'%s' is not a learning rule" % rule)
