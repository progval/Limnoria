  #
  # Copyright (c) 2004, Mike Taylor
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
  #

__author__    = "Mike Taylor <bear@code-bear.com>"
__copyright__ = "Copyright (c) 2004 Mike Taylor"
__license__   = "BSD"
__revision__  = "$Id$"

import os, string, re, time

RE_SPECIAL  = r'(?P<special>^[in|last|next]+)\s+'
RE_UNITS    = r'\s+(?P<units>[hour|minute|second|day|week|month|year]+)'
RE_QUNITS   = r'(?P<qunits>[0-9]+[hmsdwmy])'
RE_MODIFIER = r'(?P<modifier>[from|before|after|ago|prior]+)\s+'

CRE_SPECIAL  = re.compile(RE_SPECIAL, re.IGNORECASE)
CRE_UNITS    = re.compile(RE_UNITS, re.IGNORECASE)
CRE_QUNITS   = re.compile(RE_QUNITS, re.IGNORECASE)
CRE_MODIFIER = re.compile(RE_MODIFIER, re.IGNORECASE)

  # Used to adjust the returned date before/after the source

_Modifiers = {'from':    1,
              'before': -1,
              'after':   1,
              'ago':     1,
              'prior':  -1}

_Minute =  60
_Hour   =  60 * _Minute
_Day    =  24 * _Hour
_Week   =   7 * _Day
_Month  =  30 * _Day
_Year   = 365 * _Day

  # This looks hokey - but it is a nice simple way to get
  # the proper unit value and it has the advantage that 
  # later I can morph it into something localized.
  # Any trailing s will be removed before lookup.
  
_Units = {'second': 1,
          'sec':    1,
          's':      1,
          'minute': _Minute,
          'min':    _Minute,
          'm':      _Minute,
          'hour':   _Hour,
          'hr':     _Hour,
          'h':      _Hour,
          'day':    _Day,
          'dy':     _Day,
          'd':      _Day,
          'week':   _Week,
          'wk':     _Week,
          'w':      _Week,
          'month':  _Month,
          'mth':    _Month,
          'm':      _Month,
          'year':   _Year,
          'yr':     _Year,
          'y':      _Year} 

def _buildTime(sourceTime, quantity, modifier, units):
  """Take quantity, modifier and units strings and convert them
     into values, calcuate the time and return the adjusted
     sourceTime
  """
  # print '[%s][%s][%s]' % (quantity, modifier, units)
  
  q = int(quantity)
  
  if _Modifiers.has_key(modifier):
    q = q * _Modifiers[modifier]

  if units[-1] == 's':
    units = units[:-1]
    
  if _Units.has_key(units):   
    u = _Units[units]
  else:
    u = 1
  
  # print 'sourceTime [%d]' % sourceTime
  # print 'quantity   [%d]' % q
  # print 'units      [%d]' % u
    
  return sourceTime + (q * u)
  
  
def parse(timeString, sourceTime=None):
  """Parse timeString and return the number of seconds from sourceTime
     that the timeString expression represents.

     This version of parse understands only the more basic of expressions
     in this form: 
     
       <quantity> <units> <modifier> <target>
       
     Example:
     
       5 minutes from now
       last week
       2 hours before noon
      
      Valid units     - hour, minute, second, month, week, day and year
                        (including their plural forms)
      Valid modifiers - from, before, after, ago, prior
  """
  
  if sourceTime == None:
    sourceTime = int(time.time())
  else:
    sourceTime = int(sourceTime)
  
  quantity = ''
  units    = ''
  modifier = ''
  target   = ''
  
  s = string.strip(string.lower(timeString))

  m = CRE_SPECIAL.search(s)
  
  if m <> None:
    target = 'now'
    
    if m.group('special') == 'last':
      modifier = 'before'
    else:
      modifier = 'from'

    s = s[m.end('special'):]

    m = CRE_UNITS.search(s)
    
    if m <> None:
      units    = m.group('units')
      quantity = s[:m.start('units')]
      s        = s[m.end('units'):]

  else:
    m = CRE_MODIFIER.search(s)
    
    if m <> None:
      modifier = m.group('modifier')
      target   = s[m.end('modifier'):]
      s        = s[:m.start('modifier'):]
  
    m = CRE_UNITS.search(s)
    
    if m <> None:
      units    = m.group('units')
      quantity = s[:m.start('units')]
      target   = s[m.end('units'):]
  
  return _buildTime(sourceTime, quantity, modifier, units)

def _test(text, value):
  print text

  v = parse(text)
  
  print '\t%s\t%d\t%d' % ((v == value), value, v)

  #
  # TODO
  # 
  #  - make month unit adjustment aware of the actual number of days in each 
  #    month between source and target
  #  - handle edge case where quantity and unit are merged: 5s for 5 sec
  #  - handle compound/nested quantites and modifiers
  #  - bring unit test over from prototype into this file
  #  - convert 'five' to 5 and also 'twenty five' to 25



if __name__ == '__main__':
  start = int(time.time())
  tests = { '5 minutes from now':  start + 5 * _Minute,
            '5 min from now':      start + 5 * _Minute,
            'in 5 minutes':        start + 5 * _Minute,
            '5 days from today':   start + 5 * _Day,
            '5 days before today': start - 5 * _Day,
            '5 minutes':           start + 5 * _Minute,
            '5 min':               start + 5 * _Minute,
            '30 seconds from now': start + 30,
            '30 sec from now':     start + 30,
            '30 seconds':          start + 30,
            '30 sec':              start + 30,
            '1 week':              start + _Week,
            '1 wk':                start + _Week,
            '1 week':              start + _Week,
            '5 days':              start + 5 * _Day,
            '1 year':              start + _Year,
            '2 years':             start + 2 * _Year}
            
  for test in tests.keys():
    _test(test, tests[test])

            



