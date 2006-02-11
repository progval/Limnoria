###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

"""
ansi.py

ANSI Terminal Interface

Color Usage:
  print RED + 'this is red' + RESET
  print BOLD + GREEN + WHITEBG + 'this is bold green on white' + RESET
  def move(new_x, new_y): 'Move cursor to new_x, new_y'
  def moveUp(lines): 'Move cursor up # of lines'
  def moveDown(lines): 'Move cursor down # of lines'
  def moveForward(chars): 'Move cursor forward # of chars'
  def moveBack(chars): 'Move cursor backward # of chars'
  def save(): 'Saves cursor position'
  def restore(): 'Restores cursor position'
  def clear(): 'Clears screen and homes cursor'
  def clrtoeol(): 'Clears screen to end of line'
"""



################################
# C O L O R  C O N S T A N T S #
################################
BLACK = '\033[30m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'

RESET = '\033[0;0m'
BOLD = '\033[1m'
REVERSE = '\033[2m'

BLACKBG = '\033[40m'
REDBG = '\033[41m'
GREENBG = '\033[42m'
YELLOWBG = '\033[43m'
BLUEBG = '\033[44m'
MAGENTABG = '\033[45m'
CYANBG = '\033[46m'
WHITEBG = '\033[47m'

#def move(new_x, new_y):
#  'Move cursor to new_x, new_y'
#  print '\033[' + str(new_x) + ';' + str(new_y) + 'H'
#
#def moveUp(lines):
#  'Move cursor up # of lines'
#  print '\033[' + str(lines) + 'A'
#
#def moveDown(lines):
#  'Move cursor down # of lines'
#  print '\033[' + str(lines) + 'B'
#
#def moveForward(chars):
#  'Move cursor forward # of chars'
#  print '\033[' + str(chars) + 'C'
#
#def moveBack(chars):
#  'Move cursor backward # of chars'
#  print '\033[' + str(chars) + 'D'
#
#def save():
#  'Saves cursor position'
#  print '\033[s'
#
#def restore():
#  'Restores cursor position'
#  print '\033[u'
#
#def clear():
#  'Clears screen and homes cursor'
#  print '\033[2J'
#
#def clrtoeol():
#  'Clears screen to end of line'
#  print '\033[K'
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
