###
# Copyright (c) 2019-2021, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

"""A safe evaluator for math expressions using Python syntax.
Unlike eval(), it can be run on untrusted input.
"""

import ast
import math
import cmath
import operator

class InvalidNode(Exception):
    pass

def filter_module(module, safe_names):
    return dict([
        (name, getattr(module, name))
        for name in safe_names
        if hasattr(module, name)
    ])

UNARY_OPS = {
    ast.UAdd: lambda x: x,
    ast.USub: lambda x: -x,
}

BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.BitXor: operator.xor,
    ast.BitOr: operator.or_,
    ast.BitAnd: operator.and_,
}

MATH_CONSTANTS = 'e inf nan pi tau'.split()
SAFE_MATH_FUNCTIONS = (
    'acos acosh asin asinh atan atan2 atanh copysign cos cosh degrees erf '
    'erfc exp expm1 fabs fmod frexp fsum gamma hypot ldexp lgamma '
    'log1p log2 modf pow radians remainder sin sinh tan tanh'
).split()
SAFE_CMATH_FUNCTIONS = (
    'acos acosh asin asinh atan atanh cos cosh exp inf infj '
    'nanj phase polar rect sin sinh tan tanh tau'
).split()

SAFE_ENV = filter_module(math, MATH_CONSTANTS + SAFE_MATH_FUNCTIONS)
SAFE_ENV.update(filter_module(cmath, SAFE_CMATH_FUNCTIONS))

def _sqrt(x):
    if isinstance(x, complex) or x < 0:
        return cmath.sqrt(x)
    else:
        return math.sqrt(x)

def _log(x):
    if isinstance(x, complex) or x < 0:
        return cmath.log(x)
    else:
        return math.log(x)

def _log10(x):
    if isinstance(x, complex) or x < 0:
        return cmath.log10(x)
    else:
        return math.log10(x)

def _cbrt(x):
    return math.pow(x, 1.0/3)

def _factorial(x):
    if x<=10000:
        return float(math.factorial(x))
    else:
        raise Exception('factorial argument too large')

SAFE_ENV.update({
    'i': 1j,
    'abs': abs,
    'max': max,
    'min': min,
    'round': lambda x, y=0: round(x, int(y)),
    'factorial': _factorial,
    'sqrt': _sqrt,
    'cbrt': _cbrt,
    'log': _log,
    'log10': _log10,
    'ceil': lambda x: float(math.ceil(x)),
    'floor': lambda x: float(math.floor(x)),
})

UNSAFE_ENV = SAFE_ENV.copy()
# Add functions that return integers
UNSAFE_ENV.update(filter_module(math, 'ceil floor factorial gcd'.split()))


# It would be nice if ast.literal_eval used a visitor so we could subclass
# to extend it, but it doesn't, so let's reimplement it entirely.
class SafeEvalVisitor(ast.NodeVisitor):
    def __init__(self, allow_ints, variables=None):
        self._allow_ints = allow_ints
        self._env = UNSAFE_ENV if allow_ints else SAFE_ENV
        if variables:
            self._env = self._env.copy()
            self._env.update(variables)

    def _convert_num(self, x):
        """Converts numbers to complex if ints are not allowed."""
        if self._allow_ints:
            return x
        else:
            x = complex(x)
            if x.imag == 0:
                x = x.real
                # Need to use string-formatting here instead of str() because
                # use of str() on large numbers loses information:
                # str(float(33333333333333)) => '3.33333333333e+13'
                # float('3.33333333333e+13') => 33333333333300.0
                return float('%.16f' % x)
            else:
                return x

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Num(self, node):
        return self._convert_num(node.n)

    def visit_Name(self, node):
        id_ = node.id.lower()
        if id_ in self._env:
            return self._env[id_]
        else:
            raise NameError(node.id)

    def visit_Call(self, node):
        func = self.visit(node.func)
        args = map(self.visit, node.args)
        # TODO: keywords?
        return func(*args)

    def visit_UnaryOp(self, node):
        op = UNARY_OPS.get(node.op.__class__)
        if op:
            return op(self.visit(node.operand))
        else:
            raise InvalidNode('illegal operator %s' % node.op.__class__.__name__)

    def visit_BinOp(self, node):
        op = BIN_OPS.get(node.op.__class__)
        if op:
            return op(self.visit(node.left), self.visit(node.right))
        else:
            raise InvalidNode('illegal operator %s' % node.op.__class__.__name__)

    def generic_visit(self, node):
        raise InvalidNode('illegal construct %s' % node.__class__.__name__)

def safe_eval(text, allow_ints, variables=None):
    node = ast.parse(text, mode='eval')
    return SafeEvalVisitor(allow_ints, variables=variables).visit(node)
