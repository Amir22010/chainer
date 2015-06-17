import numpy
from chainer import cuda, cudnn, Function
from chainer.functions.sigmoid import Sigmoid

class SigmoidCrossEntropy(Function):
    """Sigmoid activation followed by a sigmoid cross entropy loss."""

    def __init__(self, use_cudnn=True):
        self.use_cudnn = use_cudnn

    def forward_cpu(self, inputs):
        x, t = inputs
        assert x.shape == t.shape
        self.y, = Sigmoid().forward_cpu((x,))
        # stable computation of the cross entropy.
        loss = -numpy.sum(
            x * (t - (x >= 0)) - numpy.log(1 + numpy.exp(-numpy.abs(x))))
        return numpy.array((loss / t.shape[0],), dtype=numpy.float32),

    def forward_gpu(self, inputs):
        x, t = inputs
        self.y, = Sigmoid(self.use_cudnn).forward_gpu((x,))
        loss = -cuda.reduce(
            'int* t, float* x',
            'x[i] * (t[i] - (x[i] >= 0)) - log(1 + exp(x[i] - 2 * x[i] * (x[i] >= 0)))',
            'a+b', '0', 'sigmoid_crossent_fwd', numpy.float32)(t, x)
        return loss / t.shape[0],

    def backward_cpu(self, inputs, grad_outputs):
        t, gloss = inputs[1], grad_outputs[0]
        gx = gloss * (self.y - t) / t.shape[0]
        return gx, None

    def backward_gpu(self, inputs, grad_outputs):
        t, gloss = inputs[1], grad_outputs[0]
        gx = cuda.empty_like(self.y)
        coeff = gloss / t.shape[0]
        cuda.elementwise(
            'float* gx, const float* y, const int* t, const float* coeff',
            'gx[i] = *coeff * (y[i] - t[i])',
            'sigmoid_crossent_bwd')(gx, self.y, t, coeff)
        return gx, None

def sigmoid_cross_entropy(x, t, use_cudnn=True):
    """Computes cross entropy loss on sigmoid of the prediction using
    the groundtruth label vector.

    Args:
        x (Variable): Variable holding a matrix whose (i, j)-th element indicates
            unnormalized log probability of the j-th unit at the i-th example.
        t (Variable): Variable holding an int32 vector of groundtruth binary labels.

    Returns:
        Variable: A variable holding a scalar array of the cross entropy loss.

    .. note::

       This function is differentiable only by ``x``.

    """
    return SigmoidCrossEntropy(use_cudnn)(x, t)
