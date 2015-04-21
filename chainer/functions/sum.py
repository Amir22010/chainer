import numpy
from pycuda import gpuarray
from chainer import Function

class Sum(Function):
    """Summation over all elements."""

    def forward_cpu(self, x):
        return numpy.array(x[0].sum()),

    def forward_gpu(self, x):
        return gpuarray.sum(x[0]),

    def backward_cpu(self, x, gy):
        return numpy.full_like(x[0], gy[0]),

    def backward_gpu(self, x, gy):
        return gpuarray.empty_like(x[0]).fill(gy[0].get()),

def sum(x):
    return Sum()(x)
