#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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
Commands specific to OSU;
(The Ohio State University, <http://www.ohio-state.edu/>)
"""

from baseplugin import *

import urllib2

import debug
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load OSU')

buildings = {
    'AA': 'Agricultural Administration Building, ' \
          '2120 Fyffe Road, Columbus, Ohio, 43210',
    'AC': 'ATI Student Activities Center, ' \
          'Agriculture Tech Inst, Wooster, Ohio, 44691',
    'AE': 'Agricultural Engineering, ' \
          '590 Woody Hayes Drive, Columbus, Ohio, 43210',
    'AF': 'Wagner, ATI Fairgrounds, Wooster, Ohio, 44691',
    'AG': 'ATI Greenhouse 3, Agriculture Tech Inst, Wooster, Ohio, 44691',
    'AK': 'Applecreek, Agriculture Tech Inst, Wooster, Ohio, 44691',
    'AM': 'Allied Medical Professions Building, ' \
          '1583 Perry Street, Columbus, Ohio, 43210',
    'AO': 'Airport Operations Building, ' \
          '2160 W Case Road, Columbus, Ohio, 43235',
    'AP': 'Arps Hall, 1945 N High Street, Columbus, Ohio, 43210',
    'AR': 'ATI Residence Hall, Agriculture Tech Inst, Wooster, Ohio, 44691',
    'AS': 'Animal Science Building, 2029 Fyffe Road, Columbus, Ohio, 43210',
    'AT': 'Halterman Hall (ATI), 1328 Dover Road, Wooster, Ohio, 44691',
    'AV': 'Aviation Building, 164 W 19th Avenue, Columbus, Ohio, 43210',
    'BA': 'Browning Amphitheatre, Mirror Lake, Columbus, Ohio, 43210',
    'BE': 'Baker Systems Engineering, 1971 Neil Avenue, Columbus, Ohio, 43210',
    'BF': 'Bromfield Hall, 1660 University Drive, Mansfield, Ohio, 44906',
    'BH': 'Bevis Hall, 1080 Carmack Road, Columbus, Ohio, 43210',
    'BI': 'Biological Sciences Building, ' \
          '484 W 12th Avenue, Columbus, Ohio, 43210',
    'BK': 'Bricker Hall, 190 N Oval Mall, Columbus, Ohio, 43210',
    'BL': 'Boyd Laboratory, 155 W Woodruff Avenue, Columbus, Ohio, 43210',
    'BO': 'Bolz Hall, 2036 Neil Avenue Mall, Columbus, Ohio, 43210',
    'BR': 'Brown Hall, 190 W 17th Avenue, Columbus, Ohio, 43210',
    'BZ': 'Botany & Zoology Building, 1735 Neil Avenue, Columbus, Ohio, 43210',
    'CC': 'Central Classroom Building, ' \
          '2009 Millikin Road, Columbus, Ohio, 43210',
    'CE': 'Celeste Laboratory Of Chemistry, ' \
          '120 W 18th Avenue, Columbus, Ohio, 43210',
    'CH': 'Cockins Hall, 1958 Neil Avenue, Columbus, Ohio, 43210',
    'CK': 'Cook Hall, 4240 Campus Drive, Lima, Ohio, 45804',
    'CL': 'Caldwell Laboratory, 2024 Neil Avenue, Columbus, Ohio, 43210',
    'CM': 'Campbell Hall, 1787 Neil Avenue, Columbus, Ohio, 43210',
    'CT': 'Fawcett Center For Tomorrow, ' \
          '2400 Olentangy River, Columbus, Ohio, 43210',
    'CV': 'Converse Hall, 2121 Tuttle Park Pl, Columbus, Ohio, 43210',
    'CX': 'Community Extension Center, ' \
          '905 Mt Vernon Avenue, Columbus, Ohio, 43203',
    'CZ': 'Cunz Hall, 1841 Millikin Road, Columbus, Ohio, 43210',
    'DB': 'Derby Hall, 154 N Oval Mall, Columbus, Ohio, 43210',
    'DE': 'Denney Hall, 164 W 17th Avenue, Columbus, Ohio, 43210',
    'DI': 'Drinko Hall, 55 W 12th Avenue, Columbus, Ohio, 43210',
    'DK': 'Dakan Hall, 674 W Lane Avenue, Columbus, Ohio, 43210',
    'DL': 'Dreese Laboratories, 2015 Neil Avenue, Columbus, Ohio, 43210',
    'DN': 'Doan Hall, 410 W 10th Avenue, Columbus, Ohio, 43210',
    'DO': 'Dodd Hall, 480 W 9th Avenue, Columbus, Ohio, 43210',
    'DR': 'Drake Union, 1849 Cannon Drive, Columbus, Ohio, 43210',
    'DU': 'Dulles Hall, 230 W 17th Avenue, Columbus, Ohio, 43210',
    'DV': 'Davis Medical Research Center, ' \
          '480 W 9th Avenue, Columbus, Ohio, 43210',
    'EA': '209 W Eighteenth Building, ' \
          '209 West 18th Avenue, Columbus, Ohio, 43210',
    'EC': 'Eisenhower Memorial Center, ' \
          '1640 University Drive, Mansfield, Ohio, 44906',
    'EL': 'Evans Laboratory, 88 W 18th Avenue, Columbus, Ohio, 43210',
    'EN': 'Enarson Hall, 154 W 12th Avenue, Columbus, Ohio, 43210',
    'FA': 'Fisher Auditorium, OARDC-Wooster, Wooster, Ohio, 44691',
    'FF': 'French Field House, 460 Woody Hayes Drive, Columbus, Ohio, 43210',
    'FH': 'Founders Hall, 1179 University Drive, Newark, Ohio, 43055',
    'FL': 'Fontana Laboratories, 116 W 19th Avenue, Columbus, Ohio, 43210',
    'FR': 'Fry Hall, 338 W 10th Avenue, Columbus, Ohio, 43210',
    'FT': 'Fallerius Technical Educ Center, ' \
          '2441 Kenwood Circle, Mansfield, Ohio, 44906',
    'GA': 'Galvin Hall, 4240 Campus Drive, Lima, Ohio, 45804',
    'GB': 'General Biology Annex, 1791 Neil Avenue, Columbus, Ohio, 43210',
    'GH': 'Golf Course Club House, 3605 Tremont Road, Columbus, Ohio, 43221',
    'GL': 'Goss Laboratory, 1925 Coffey Road, Columbus, Ohio, 43210',
    'GR': 'Graves Hall, 333 W 10th Avenue, Columbus, Ohio, 43210',
    'HA': 'Hayes Hall, 108 N Oval Mall, Columbus, Ohio, 43210',
    'HC': 'Hopkins Hall, 128 N Oval Mall, Columbus, Ohio, 43210',
    'HG': 'Howlett Greenhouses, 680 Tharp St, Columbus, Ohio, 43210',
    'HH': 'Hagerty Hall, 1775 College Road, Columbus, Ohio, 43210',
    'HI': 'Hitchcock Hall, 2070 Neil Avenue, Columbus, Ohio, 43210',
    'HK': 'Haskett Hall, 156 W 19th Avenue, Columbus, Ohio, 43210',
    'HL': 'Hale Hall, 153 W 12th Avenue, Columbus, Ohio, 43210',
    'HM': 'Hamilton Hall, 1645 Neil Avenue, Columbus, Ohio, 43210',
    'HN': 'Kuhn Honors House, 220 W 12th Avenue, Columbus, Ohio, 43210',
    'HP': 'Hopewell Hall (Newark), 1179 University Drive, Newark, Ohio, 43055',
    'HS': 'Health Science Library, 376 W 10th Avenue, Columbus, Ohio, 43210',
    'HT': 'Howlett Hall, 2001 Fyffe Court, Columbus, Ohio, 43210',
    'HU': 'Hughes Hall, 1899 College Road, Columbus, Ohio, 43210',
    'IH': 'Independence Hall, 1923 Neil Avenue Mall, Columbus, Ohio, 43210',
    'IR': 'Ice Rink, 390 Woody Hayes Drive, Columbus, Ohio, 43210',
    'IV': 'Ives Hall, 2073 Neil Avenue, Columbus, Ohio, 43210',
    'JA': 'James Cancer Hosp & Research Inst, ' \
          '300 W 10th Avenue, Columbus, Ohio, 43210',
    'JR': 'Journalism Building, 242 W 18th Avenue, Columbus, Ohio, 43210',
    'KH': 'Kottman Hall, 2021 Coffey Road, Columbus, Ohio, 43210',
    'KL': 'Koffolt Laboratories, 140 W 19th Avenue, Columbus, Ohio, 43210',
    'KR': '1224 Kinnear Road, 1224 Kinnear Road, Columbus, Ohio, 43212',
    'LC': 'Ohio Legal Center, 33 W 11th Avenue, Columbus, Ohio, 43201',
    'LI': 'Main Library, 1858 Neil Avenue Mall, Columbus, Ohio, 43210',
    'LK': 'Larkins Hall, 337 W 17th Avenue, Columbus, Ohio, 43210',
    'LO': 'Lord Hall, 124 W 17th Avenue, Columbus, Ohio, 43210',
    'LS': 'Reed Student Activities Building, ' \
          '4240 Campus Drive, Lima, Ohio, 45804',
    'LT': 'Lincoln Tower, 1800 Cannon Drive, Columbus, Ohio, 43210',
    'LZ': 'Lazenby Hall, 1827 Neil Avenue Mall, Columbus, Ohio, 43210',
    'MA': 'Mathematics Building, 231 W 18th Avenue, Columbus, Ohio, 43210',
    'MC': 'McCampbell Hall, 1581 Dodd Drive, Columbus, Ohio, 43210',
    'ME': 'Meiling Hall, 370 W 9th Avenue, Columbus, Ohio, 43210',
    'ML': 'Mendenhall Laboratory, 125 S Oval Mall, Columbus, Ohio, 43210',
    'MM': 'Mershon Auditorium, 1871 N High St, Columbus, Ohio, 43210',
    'MN': '1501 Neil Avenue, 1501 Neil Avenue, Columbus, Ohio, 43201',
    'MO': 'Mount Hall, 1050 Carmack Road, Columbus, Ohio, 43210',
    'MP': 'McPherson Chemical Laboratory, ' \
          '140 W 18th Avenue, Columbus, Ohio, 43210',
    'MQ': 'MacQuigg Laboratory, 105 W Woodruff Avenue, Columbus, Ohio, 43210',
    'MR': 'Morrill Hall (Marion), 1465 Mt Vernon Avenue, Marion, Ohio, 43302',
    'MS': 'Means Hall, 1654 Upham Drive, Columbus, Ohio, 43210',
    'MT': 'Morrill Tower, 1900 Cannon Drive, Columbus, Ohio, 43210',
    'NE': 'Neil-17th Building, 1949 Neil Avenue, Columbus, Ohio, 43210',
    'NH': 'Newton Hall, 1585 Neil Avenue, Columbus, Ohio, 43210',
    'NL': 'Neil Hall, 1634 Neil Avenue, Columbus, Ohio, 43210',
    'NR': 'Jesse Owens Recreation Center North, ' \
          '2151 Neil Avenue, Columbus, Ohio, 43210',
    'OR': 'Orton Hall, 155 S Oval Mall, Columbus, Ohio, 43210',
    'OU': 'Ohio Union, 1739 N High St, Columbus, Ohio, 43210',
    'OV': 'Ovalwood Hall (Mansfield), ' \
          '1680 University Drive, Mansfield, Ohio, 44906',
    'OX': 'Oxley Hall, 1712 Neil Avenue, Columbus, Ohio, 43210',
    'PA': 'Page Hall, 1810 College Road, Columbus, Ohio, 43210',
    'PH': 'Postle Hall, 305 W 12th Avenue, Columbus, Ohio, 43210',
    'PK': 'Parks Hall, 500 W 12th Avenue, Columbus, Ohio, 43210',
    'PL': 'Plumb Hall, 2027 Coffey Road, Columbus, Ohio, 43210',
    'PN': '1478 Pennsylvania Avenue, ' \
          '1478 Pennsylvania Avenue, Columbus, Ohio, 43201',
    'PO': 'Pomerene Hall, 1760 Neil Avenue, Columbus, Ohio, 43210',
    'PR': 'Pressey Hall, 1070 Carmack Road, Columbus, Ohio, 43210',
    'RA': 'Ramseyer Hall, 29 W Woodruff Avenue, Columbus, Ohio, 43210',
    'RC': 'Research Center, 1314 Kinnear Road, Columbus, Ohio, 43212',
    'RD': 'Rhodes Hall, 450 W 10th Avenue, Columbus, Ohio, 43210',
    'RF': 'Riffe Building, 496 W 12th Avenue, Columbus, Ohio, 43210',
    'RH': 'Rightmire Hall, 1060 Carmack Road, Columbus, Ohio, 43210',
    'RL': 'Robinson Laboratory, 206 W 18th Avenue, Columbus, Ohio, 43210',
    'RY': 'Royer Student Activities Center, ' \
          '85 Curl Drive, Columbus, Ohio, 43210',
    'SA': 'Foundry Metals & Glass Building, ' \
          '1055 Carmack Road, Columbus, Ohio, 43210',
    'SC': 'Scott Hall, 1090 Carmack Road, Columbus, Ohio, 43210',
    'SD': 'Alber Student Center, 1465 Mt Vernon Avenue, Marion, Ohio, 43302',
    'SE': 'Steeb Hall, Se 70 W 11th Avenue, Columbus, Ohio, 43210',
    'SH': 'Stillman Hall, 1947 College Road, Columbus, Ohio, 43210',
    'SI': 'Sisson Hall, 1900 Coffey Road, Columbus, Ohio, 43210',
    'SJ': 'St John Arena, 410 Woody Hayes Drive, Columbus, Ohio, 43210',
    'SK': 'Skou Hall, Agriculture Tech Inst, Wooster, Ohio, 44691',
    'SL': 'Starling Loving Hall A, 320 W 10th Avenue, Columbus, Ohio, 43210',
    'SM': 'Smith Laboratory, 174 W 18th Avenue, Columbus, Ohio, 43210',
    'SN': 'Gibraltar Stonlab, Gibraltar Island, Put-in-bay, Ohio, 43456',
    'SP': 'ATI Shop, Agriculture Tech Inst, Wooster, Ohio, 44691',
    'SR': 'Jesse Owens Recreation Center South, ' \
          '175 W 11th Avenue, 175 West 11th Avenue, Ohio, OH',
    'ST': 'Ohio Stadium, 411 Woody Hayes Drive, Columbus, Ohio, 43210',
    'SU': 'Sullivant Hall, 1813 N High St, Columbus, Ohio, 43210',
    'TE': 'Marion Technical Education Center, ' \
          '1467 Mt Vernon Avenue, Marion, Ohio, 43302',
    'TL': 'Technical Education Building (Lima), ' \
          '4240 Campus Drive, Lima, Ohio, 45804',
    'TO': 'Townshend Hall, 1885 Neil Avenue Mall, Columbus, Ohio, 43210',
    'TT': 'Taylor Tower, 50 Curl Drive, Columbus, Ohio, 43210',
    'UH': 'University Hall, 230 N Oval Mall, Columbus, Ohio, 43210',
    'UP': 'Upham Hall, 473 W 12th Avenue, Columbus, Ohio, 43210',
    'VE': 'Veterinary Hospital, 601 Vernon Tharp St, Columbus, Ohio, 43210',
    'VG': 'Van De Graaff Laboratory, 1302 Kinnear Road, Columbus, Ohio, 43212',
    'VH': 'Vivian Hall, 2121 Fyffe Road, Columbus, Ohio, 43210',
    'WA': 'Watts Hall, 2041 College Road, Columbus, Ohio, 43210',
    'WE': 'Welding Engineering Laboratory, ' \
          '190 W 19th Avenue, Columbus, Ohio, 43210',
    'WG': 'Weigel Hall, 1866 College Road, Columbus, Ohio, 43210',
    'WI': 'Wiseman Hall, 400 W 12th Avenue, Columbus, Ohio, 43210',
    'WL': 'Williams, OARDC-Wooster, Wooster, Ohio, 44691',
    'WO': 'Womens Field House, 1801 Neil Avenue, Columbus, Ohio, 43210',
    'WR': 'Jesse Owens Recreation Center West, ' \
          '1031 Carmack Road, Columbus, Ohio, 43210',
    'WS': 'Wilce Health Center, 1875 Millikin Road, Columbus, Ohio, 43210',
    'WX': 'Wexner Center, 1850 College Road, Columbus, Ohio, 43210'
}

class OSU(callbacks.Privmsg):
    threaded = True
    def osuemail(self, irc, msg, args):
        """<first name> <middle initial> <last name>"""
        s = '.'.join(args)
        url = 'http://www.ohio-state.edu/cgi-bin/inquiry2.cgi?keyword=%s' % s
        try:
            fd = urllib2.urlopen(url)
            data = fd.read()
            emails = []
            for line in data.splitlines():
                line.strip()
                if 'Published address' in line:
                    emails.append(line.split()[-1])
            if emails:
                irc.reply(msg, 'Possible matches: %s' % ', '.join(emails))
            else:
                irc.reply(msg, 'There seem to be no matches to that name.')
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

    def osubuilding(self, irc, msg, args):
        """<building abbreviation>"""
        building = privmsgs.getArgs(args)
        try:
            irc.reply(msg, buildings[building.upper()])
        except KeyError:
            irc.reply(msg, 'I don\'t know of any such OSU building.')


Class = OSU

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
