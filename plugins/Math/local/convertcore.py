#****************************************************************************
# This file has been modified from its original version. It has been
# formatted to fit your irc bot.
#
# The original version is a nifty PyQt application written by Douglas Bell,
# available at  http://convertall.bellz.org/
#
# Below is the original copyright. Doug Bell rocks.
# The hijacker is Keith Jones, and he has no bomb in his shoe.
#
#****************************************************************************

import re
import copy

unitData = \
"""
#*****************************************************************************
#units.dat, the units data file, version 0.6.2
#
# ConvertAll, a units conversion program
# Copyright (C) 2016, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, Version 2.  This program is
# distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY.
#*****************************************************************************
#
# Units are defined by an optional quantity and an equivalent unit or unit
# combination.  A Python expression may be used for the quantity, but is
# restricted to using only the following operators: *, /, +, -.
# Beware of integer division truncation: be sure to use a float for at least
# one of the values.
#
# The unit type must be placed in square brackets before a set of units.  The
# first comment after the equivalent unit will be put in parenthesis after the
# unit name (usually used to give the full name of an abbreviated unit).  The
# next comment will be used in the program list's comment column; later
# comments and full line comments are ignored.
#
# Non-linear units are indicated with an equivalent unit in square brackets,
# followed by either equations or equivalency lists for the definition.  For
# equations, two are given, separated by a ';'.  Both are functions of "x", the
# first going from the unit to the equivalent unit and the second one in
# reverse.  Any valid Python expression returning a float (including the
# functions in the math module) should work.  The equivalency list is a Python
# list of tuples giving points for linear interpolation.
#
# All units must reduce to primitive units, which are indicated by an
# equivalent unit starting with '!'.  A special "unitless" primitve unit
# (usualty called "unit") has '!!' for an equivalent unit.  Circular references
# must also be avoided.
#
# Primitive units:  kg, m, s, K, A, mol, cd, rad, sr, bit, unit
#
##############################################################################

#
# mass units
#
[mass]
kg                  = !                  # kilogram
kilogram            = kg
key                 = kg                 # # drug slang
hectogram           = 100 gram
dekagram            = 10 gram
gram                = 0.001 kg
g                   = gram               # gram
decigram            = 0.1 gram
centigram           = 0.01 gram
milligram           = 0.001 gram
mg                  = milligram          # milligram
microgram           = 0.001 mg
tonne               = 1000 kg            # # metric
metric ton          = tonne
megagram            = tonne
kilotonne           = 1000 tonne         # # metric
gigagram            = 1e9 gram
teragram            = 1e12 gram
carat               = 0.2 gram
ct                  = carat              # carat
amu                 = 1.66053873e-27 kg  # atomic mass
atomic mass unit    = amu
pound               = 0.45359237 kg      #        # avoirdupois
lb                  = pound              # pound  # avoirdupois
lbm                 = pound              # pound  # avoirdupois
ounce               = 1/16.0 pound       #        # avoirdupois
oz                  = ounce              # ounce  # avoirdupois
lid                 = ounce              #        # drug slang
dram                = 1/16.0 ounce       #        # avoirdupois
pound troy          = 5760 grain
lb troy             = pound troy         # pound troy
ounce troy          = 1/12.0 lb troy
oz troy             = ounce troy         # ounce troy
ton                 = 2000 lb            # # non-metric
kiloton             = 1000 ton           # # non-metric
long ton            = 2240 lb            # # Imperial
ton imperial        = long ton
slug                = lbf*s^2/ft
stone               = 14 lb
grain               = 1/7000.0 lb
pennyweight         = 24 grain
hundredweight long  = 112 lb             # # Imperial
hundredweight short = 100 lb             # # US & Canada
solar mass          = 1.9891e30 kg


#
# length / distance units
#
[length]
m                        = !              # meter
meter                    = m
metre                    = m
dm                       = 0.1 m          # decimeter
decimeter                = dm
cm                       = 0.01 m         # centimeter
centimeter               = cm
mm                       = 0.001 m        # millimeter
millimeter               = mm
micrometer               = 1e-6 m
micron                   = micrometer
nanometer                = 1e-9 m
nm                       = nanometer      # nanometer
dekameter                = 10 m
hectometer               = 100 m
km                       = 1000 m         # kilometer
kilometer                = km
megameter                = 1000 km
angstrom                 = 1e-10 m
fermi                    = 1e-15 m        # # nuclear sizes
inch                     = 2.54 cm
in                       = inch           # inch
inches                   = inch
mil                      = 0.001 inch
microinch                = 1e-6 inch
microinches              = microinch
foot                     = 12 inch
ft                       = foot           # foot
feet                     = foot
foot US survey           = 1200/3937.0 m
Cape foot                = 1.033 foot
yard                     = 3 ft
yd                       = yard           # yard
mile                     = 5280 ft        # # statute mile
mi                       = mile           # mile # statute mile
nautical mile            = 1852 m
nmi                      = nautical mile  # nautical mile
mile US survey           = 5280 foot US survey
league                   = 3 mile
chain                    = 66 ft
chain US survey          = 66 foot US survey
link                     = 0.01 chain
fathom                   = 6 ft
cable                    = 0.1 nautical mile
rod                      = 5.5 yard
furlong                  = 40 rod
hand                     = 4 inch
cubit                    = 21.8 inch      # # biblical unit
point                    = 1/72.0 inch    # # desktop publishing point
pica                     = 12 point
caliber                  = 1.0 inch       # # bullet sizes
rack unit                = 1.75 in        # # computing
smoot                    = 67 inch
football field           = 100 yd
marathon                 = 46145 yd
mil Swedish              = 10 km
versta                   = 3500 ft        # # Russian unit
au                       = 1.49597870691e11 m   # astronomical unit
astronomical unit        = au
LD                       = 384400 km      # lunar distance # astronomical
lunar distance           = LD             # # astronomical distance
light year               = 365.25 light speed * day
light minute             = light speed * min
light second             = light speed * s
parsec                   = 3.0856775813e16 m
kiloparsec               = 1000 parsec
megaparsec               = 1000 kiloparsec
screw size               = [in] 0.013*x + 0.06 ; (x - 0.06) / 0.013 \
                           # # Unified diameters, non-linear
AWG Dia                  = [in] pow(92.0,(36-x)/39.0)/200.0 ; \
                           36 - 39.0*log(200.0*x)/log(92.0) \
                           # American Wire Gauge \
                           # use -1, -2 for 00, 000; non-linear
American Wire Gauge Dia  = [in] pow(92.0,(36-x)/39.0)/200.0 ; \
                           36 - 39.0*log(200.0*x)/log(92.0) \
                           #  # use -1, -2 for 00, 000; non-linear
British Std Wire Gauge   = [in] [(-6, .500), (-5, .464), (-3, .400), \
                           (-2, .372), (3, .252), (6, .192), (10, .128), \
                           (14, .080), (19, .040), (23, .024), (26, .018), \
                           (28, .0148), (30, .0124), (39, .0052), \
                           (49, .0012), (50, .001)] \
                           #  # use -1, -2 for 2/0, 3/0; non-linear
standard gauge           = [in] [(-5, .448350), (1, .269010), (14, .0747250), \
                           (16, .0597800), (17, .0538020), (20, .0358680), \
                           (26, .0179340), (31, .0104615), (36, .00672525), \
                           (38, .00597800)] # steel \
                           # Manufacturers Std. Gauge, non-linear
zinc gauge               = [in] [(1, .002), (10, .02), (15, .04), (19, .06), \
                           (23, .1), (24, .125), (27, .5), (28, 1)]  \
                           # # sheet metal thickness, non-linear
ring size                = [in] 0.1018*x + 1.4216 ; (x - 1.4216) / 0.1018  \
                           # # US size, circum., non-linear
shoe size mens           = [in] x/3.0 + 7 + 1/3.0 ; (x - 7 - 1/3.0) * 3 \
                           # # US sizes, non-linear
shoe size womens         = [in] x/3.0 + 6 + 5/6.0 ; (x - 6 - 5/6.0) * 3 \
                           # # US sizes, non-linear


#
# time units
#
[time]
s             = !                 # second
sec           = s                 # second
second        = s
ms            = 0.001 s           # millisecond
millisecond   = ms
microsecond   = 1e-6 s
ns            = 1e-9 s            # nanosecond
nanosecond    = ns
minute        = 60 s
min           = minute            # minute
hour          = 60 min
hr            = hour              # hour
bell          = 30 min            #  # naval definition
watch         = 4 hour
watches       = watch
day           = 24 hr
week          = 7 day
wk            = week              # week
fortnight     = 14 day
month         = 1/12.0 year
year          = 365.242198781 day
yr            = year              # year
calendar year = 365 day
decade        = 10 year
century       = 100 year
centuries     = century
millennium    = 1000 year
millennia     = millennium
[scheduling]
man hour      = 168/40.0 hour
man week      = 40 man hour
man month     = 1/12.0 man year
man year      = 52 man week


#
# temperature
#
[temperature]
K                 = !     # Kelvin
Kelvin            = K
deg K             = K     # Kelvin
degree Kelvin     = K

C                 = [K] x + 273.15 ; x - 273.15  # Celsius  # non-linear
Celsius           = [K] x + 273.15 ; x - 273.15  #          # non-linear
deg C             = [K] x + 273.15 ; x - 273.15  # Celsius  # non-linear
degree Celsius    = [K] x + 273.15 ; x - 273.15  #          # non-linear

R                 = 5/9.0 K     # Rankine
Rankine           = R
deg R             = R           # Rankine
F                 = [R] x + 459.67 ; x - 459.67  # Fahrenheit  # non-linear
Fahrenheit        = [R] x + 459.67 ; x - 459.67  #             # non-linear
deg F             = [R] x + 459.67 ; x - 459.67  # Fahrenheit  # non-linear
degree Fahrenheit = [R] x + 459.67 ; x - 459.67  #             # non-linear

[temp. diff.]
C deg             = K        # Celsius degree
Celsius degree    = C deg
F deg             = R        # Fahrenheit deg.
Fahrenheit degree = F deg


#
# electrical units
#
[current]
A              = !              # ampere
ampere         = A
amp            = A
milliampere    = 0.001 A
milliamp       = milliampere
mA             = milliampere    # milliampere
microampere    = 0.001 mA
kiloampere     = 1000 A
kA             = kiloampere     # kiloampere
[charge]
coulomb        = A*s
amp hour       = A*hr
mAh            = 0.001 amp hour # milliamp hour
milliamp hour  = mAh
[potential]
volt           = W/A
V              = volt           # volt
millivolt      = 0.001 volt
mV             = millivolt      # millivolt
kilovolt       = 1000 volt
kV             = kilovolt       # kilovolt
[resistance]
ohm            = V/A
milliohm       = 0.001 ohm
microhm        = 0.001 milliohm
kilohm         = 1000 ohm
[conductance]
siemens        = A/V
[capacitance]
farad          = coulomb/V
millifarad     = 0.001 farad
microfarad     = 0.001 millifarad
nanofarad      = 1e-9 farad
picofarad      = 1e-12 farad
[magn. flux]
weber          = V*s
Wb             = weber          # weber
maxwell        = 1e-8 Wb
[inductance]
henry          = Wb/A
H              = henry          # henry
millihenry     = 0.001 henry
mH             = millihenry     # millihenry
microhenry     = 0.001 mH
[flux density]
tesla          = Wb/m^2
T              = tesla          # tesla
gauss          = maxwell/cm^2


#
# molecular units
#
[molecular qty]
mol          = !           # mole       # gram mole
mole         = mol         #            # gram mole
gram mole    = mol
kilomole     = 1000 mol
kmol         = kilomole    # kilomole
pound mole   = mol*lbm/gram
lbmol        = pound mole  # pound mole
[size of a mol]
avogadro     = gram/(amu*mol)


#
# Illumination units
#
[lum. intens.]
cd          = !          # candela
candela     = cd

[luminous flux]
lumen        = cd * sr
lm           = lumen     # lumen

[illuminance]
lux          = lumen/m^2
footcandle   = lumen/ft^2
metercandle  = lumen/m^2

[luminance]
lambert      = cd/(pi*cm^2)
millilambert = 0.001 lambert
footlambert  = cd/(pi*ft^2)


#
# angular units
#
[angle]
radian      = !
rad         = radian         # radian
circle      = 2 pi*radian
turn        = circle
revolution  = circle
rev         = revolution     # revolution
degree      = 1/360.0 circle
deg         = degree         # degree
arc min     = 1/60.0 degree  # minute
arc minute  = arc min
min arc     = arc min        # minute
minute arc  = arc min
arc sec     = 1/60.0 arc min # second
arc second  = arc sec
sec arc     = arc sec        # second
second arc  = arc sec
quadrant    = 1/4.0 circle
right angle = quadrant
gradian     = 0.01 quadrant


#
# solid angle units
#
[solid angle]
sr         = !      # steradian
steradian  = sr
sphere     = 4 pi*sr
hemisphere = 1/2.0 sphere


#
# information units
#
[data]
bit              = !
kilobit          = 1000 bit          #                  # based on power of 10
megabit          = 1000 kilobit      #                  # based on power of 10
byte             = 8 bit
B                = byte              # byte
kilobyte         = 1024 byte         #                  # based on power of 2
kB               = kilobyte          # kilobyte         # based on power of 2
megabyte         = 1024 kB           #                  # based on power of 2
MB               = megabyte          # megabyte         # based on power of 2
gigabyte         = 1024 MB           #                  # based on power of 2
GB               = gigabyte          # gigabyte         # based on power of 2
terabyte         = 1024 GB           #                  # based on power of 2
TB               = terabyte          # terabyte         # based on power of 2
petabyte         = 1024 TB           #                  # based on power of 2
PB               = petabyte          # petabyte         # based on power of 2

kilobyte IEC std = 1000 byte         #                  # based on power of 10
kB IEC std       = kilobyte IEC std  # kilobyte         # based on power of 10
megabyte IEC std = 1000 kB IEC std   #                  # based on power of 10
MB IEC std       = megabyte IEC std  # megabyte         # based on power of 10
gigabyte IEC std = 1000 MB IEC std   #                  # based on power of 10
GB IEC std       = gigabyte IEC std  # gigabyte         # based on power of 10
terabyte IEC std = 1000 GB IEC std   #                  # based on power of 10
TB IEC std       = terabyte IEC std  # terabyte         # based on power of 10
petabyte IEC std = 1000 TB IEC std   #                  # based on power of 10
PB IEC std       = petabyte IEC std  # petabyte         # based on power of 10

kibibyte         = 1024 byte
KiB              = kibibyte          # kibibyte
mebibyte         = 1024 KiB
MiB              = mebibyte          # mebibyte
gibibyte         = 1024 MiB
GiB              = gibibyte          # gibibyte
tebibyte         = 1024 GiB
TiB              = tebibyte          # tebibyte
pebibyte         = 1024 TiB
PiB              = pebibyte          # pebibyte

[data transfer]
bps              = bit/sec           # bits / second
kbps             = 1000 bps          # kilobits / sec.  # based on power of 10


#
# Unitless numbers
#
[quantity]
unit               = !!
1                  = unit            # unit
pi                 = 3.14159265358979323846 unit
pair               = 2 unit
hat trick          = 3 unit          # # sports
dozen              = 12 unit
doz                = dozen           # dozen
bakers dozen       = 13 unit
score              = 20 unit
gross              = 144 unit
great gross        = 12 gross
ream               = 500 unit
percent            = 0.01 unit
%                  = percent
mill               = 0.001 unit
[interest rate]
APR                = [unit] log(1 + x/100) ;  (exp(x) - 1)*100 \
                     # annual % rate # based on continuous compounding
[concentration]
proof              = 1/200.0 unit    # # alcohol content
ppm                = 1e-6 unit       # parts per million
parts per million  = ppm
ppb                = 1e-9 unit       # parts per billion
parts per billion  = ppb
ppt                = 1e-12 unit      # parts per trillion
parts per trillion = ppt
karat              = 1/24.0 unit     # # gold purity
carat gold         = karat           # # gold purity


#
# force units
#
[force]
newton         = kg*m/s^2
N              = newton           # newton
dekanewton     = 10 newton
kilonewton     = 1000 N
kN             = kilonewton       # kilonewton
meganewton     = 1000 kN
millinewton    = 0.001 N
dyne           = cm*g/s^2
kg force       = kg * gravity     # kilogram f
kgf            = kg force         # kilogram force
kilogram force = kg force
kp             = kg force         # kilopond
kilopond       = kg force
gram force     = g * gravity
pound force    = lbm * gravity    #              # avoirdupois
lbf            = pound force      # pound force  # avoirdupois
ton force      = ton * gravity
ounce force    = ounce * gravity
ozf            = ounce force      # ounce force
tonne force    = tonne * gravity  # # metric
pdl            = lbm * ft / sec^2 # poundal # Imperial force
poundal        = pdl              # # Imperial force


#
# area units
#
[area]
barn                     = 1e-28 m^2       # # particle physics
are                      = 100 m^2
decare                   = 10 are
dekare                   = 10 are
hectare                  = 100 are
stremma                  = 1000 m^2
acre                     = 10 chain^2
section                  = mile^2
township                 = 36 section
homestead                = 160 acre
square perch             = 30.25 yd^2
rood                     = 0.25 acre
rai                      = 1600 m^2        # # Thai
ngaan                    = 400 m^2         # # Thai
circular inch            = 1/4.0 pi*in^2   # # area of 1 inch circle
circular mil             = 1/4.0 pi*mil^2  # # area of 1 mil circle
AWG Area                 = [in^2] pi/4*pow(pow(92.0,(36-x)/39.0)/200.0,2) ; \
                           36 - 39.0*log(200.0*sqrt(x*4.0/pi))/log(92.0) \
                           # American Wire Gauge \
                           # use -1, -2 for 00, 000; non-linear
American Wire Gauge Area = [in^2] pi/4*pow(pow(92.0,(36-x)/39.0)/200.0,2) ; \
                           36 - 39.0*log(200.0*sqrt(x*4.0/pi))/log(92.0) \
                           #  # use -1, -2 for 00, 000; non-linear


#
# volume units
#
[volume]
cc                   = cm^3                 # cubic centimeter
cubic centimeter     = cc
liter                = 1000 cc
l                    = liter                # liter
litre                = liter
deciliter            = 0.1 liter
centiliter           = 0.01 liter
milliliter           = cc
ml                   = milliliter           # milliliter
microliter           = 1e-6 liter
dekaliter            = 10 liter
hectoliter           = 100 liter
kiloliter            = 1000 liter
kl                   = kiloliter            # kiloliter
megaliter            = 1000 kiloliter
gallon               = 231 in^3             #             # US liquid
gal                  = gallon               # gallon      # US liquid
quart                = 1/4.0 gallon         #             # US liquid
qt                   = quart                # quart       # US liquid
pint                 = 1/2.0 quart          #             # US liquid
pt                   = pint                 # pint        # US liquid
fluid ounce          = 1/16.0 pint          #             # US
fl oz                = fluid ounce          # fluid ounce # US
ounce fluid          = fluid ounce          #             # US
fluid dram           = 1/8.0 fluid ounce    #             # US
minim                = 1/480.0 fluid ounce  #             # US
imperial gallon      = 4.54609 liter
imp gal              = imperial gallon      # imperial gallon
gallon imperial      = imperial gallon
imperial quart       = 1/4.0 imp gal
imp qt               = imperial quart       # imperial quart
quart imperial       = imperial quart
imperial pint        = 1/8.0 imp gal
imp pt               = imperial pint        # imperial pint
pint imperial        = imperial pint
imperial fluid ounce = 1/160.0 imp gal
imp fl oz            = imperial fluid ounce # imperial fluid ounce
imperial fluid dram  = 1/8.0 imp fl oz
imperial minim       = 1/480.0 imp fl oz
cup                  = 8 fl oz
tablespoon           = 1/16.0 cup
tbsp                 = tablespoon           # tablespoon
teaspoon             = 1/3.0 tbsp
tsp                  = teaspoon             # teaspoon
barrel               = 42 gallon
bbl                  = barrel               # barrel
shot                 = 1.5 fl oz
fifth                = 1/5.0 gallon         #             # alcohol
wine bottle          = 750 ml
magnum               = 1.5 liter            #             # alcohol
keg                  = 15.5 gallon          #             # beer
hogshead wine        = 63 gal
hogshead beer        = 54 gal
bushel               = 2150.42 in^3
peck                 = 1/4.0 bushel
cord                 = 128 ft^3
board foot           = ft^2*in
board feet           = board foot


#
# velocity units
#
[velocity]
knot        = nmi/hr
kt          = knot             # knot
light speed = 2.99792458e8 m/s
mph         = mi/hr            # miles/hour
kph         = km/hr            # kilometers/hour
mach        = 340.29 m/s       # # speed sound at STP
[rot. velocity]
rpm         = rev/min          # rev/min
rps         = rev/sec          # rev/sec


#
# flow rate units
#
[fluid flow]
gph         = gal/hr           # gallons/hour
gpm         = gal/min          # gallons/minute
cfs         = ft^3/sec         # cu ft/second
cfm         = ft^3/min         # cu ft/minute
lpm         = l/min            # liter/min
[gas flow]
sccm        = atm*cc/min       # std cc/min      # pressure * flow
sccs        = atm*cc/sec       # std cc/sec      # pressure * flow
slpm        = atm*l/min        # std liter/min   # pressure * flow
slph        = atm*l/hr         # std liter/hour  # pressure * flow
scfh        = atm*ft^3/hour    # std cu ft/hour  # pressure * flow
scfm        = atm*ft^3/min     # std cu ft/min   # pressure * flow


#
# pressure units
#
[pressure]
Pa                    = N/m^2                    # pascal
pascal                = Pa
hPa                   = 100 Pa                   # hectopascal
hectopascal           = hPa
kPa                   = 1000 Pa                  # kilopascal
kilopascal            = kPa
MPa                   = 1000 kPa                 # megapascal
megapascal            = MPa
GPa                   = 1000 MPa                 # gigapascal
gigapascal            = GPa
atm                   = 101325 Pa                # atmosphere
atmosphere            = atm
bar                   = 1e5 Pa
mbar                  = 0.001 bar                # millibar
millibar              = mbar
microbar              = 0.001 mbar
decibar               = 0.1 bar
kilobar               = 1000 bar
megabar               = 1000 kilobar
mm Hg                 = mm*density Hg*gravity
millimeter of Hg      = mm Hg
torr                  = mm Hg
micron of Hg          = micron*density Hg*gravity
in Hg                 = in*density Hg*gravity    # inch of Hg
inch of Hg            = in Hg
m water               = m*density water*gravity  # meter of H2O # fresh water
m H2O                 = m water                  # meter of H2O # fresh water
meter of water        = m water                  #              # fresh water
in water              = in*density water*gravity # inch of H2O  # fresh water
in H2O                = in water                 # inch of H2O  # fresh water
inch of water         = in water                 #              # fresh water
ft water              = ft*density water*gravity # feet of H2O  # fresh water
ft H2O                = ft water                 # feet of H20  # fresh water
feet of water         = ft water                 #              # fresh water
foot of head          = ft water                 #              # fresh water
ft hd                 = ft water                 # foot of head # fresh water
psi                   = lbf/in^2                 # pound / sq inch
pound per sq inch     = psi
ksi                   = 1000 psi                 # 1000 lb / sq inch


#
# density units
#
[density]
density water         = gram/cm^3
density sea water     = 1.025 gram/cm^3
density Hg            = 13.5950981 gram/cm^3
density air           = 1.293 kg/m^3          # # at STP
density steel         = 0.283 lb/in^3         # # carbon steel
density aluminum      = 0.098 lb/in^3
density zinc          = 0.230 lb/in^3
density brass         = 0.310 lb/in^3         # # 80Cu-20Zn
density copper        = 0.295 lb/in^3
density iron          = 0.260 lb/in^3         # # cast iron
density nickel        = 0.308 lb/in^3
density tin           = 0.275 lb/in^3
density titanium      = 0.170 lb/in^3
density silver        = 0.379 lb/in^3
density nylon         = 0.045 lb/in^3
density polycarbonate = 0.045 lb/in^3


#
# energy units
#
[energy]
joule                 = N*m
J                     = joule             # joule
kilojoule             = 1000 joule
kJ                    = kilojoule         # kilojoule
megajoule             = 1000 kilojoule
gigajoule             = 1000 megajoule
millijoule            = 0.001 joule
mJ                    = millijoule        # millijoule
calorie               = 4.1868 J
cal                   = calorie           # calorie
kilocalorie           = 1000 cal
kcal                  = kilocalorie       # kilocalorie
calorie food          = kilocalorie
thermie               = 1000 kcal
Btu                   = cal*lb*R/(g*K)    # British thermal unit
British thermal unit  = Btu
therm                 = 100000 Btu
erg                   = cm*dyne
electronvolt          = 1.602176462e-19 J
eV                    = electronvolt      # electronvolt
kWh                   = kW*hour           # kilowatt-hour
kilowatt hour         = kWh
ton TNT               = 4.184e9 J
tonne oil equivalent  = 41.868 gigajoule
tonne coal equivalent = 7000000 kcal


#
# power units
#
[power]
watt              = J/s
W                 = watt            # watt
kilowatt          = 1000 W
kW                = kilowatt        # kilowatt
megawatt          = 1000 kW
MW                = megawatt        # megawatt
gigawatt          = 1000 MW
GW                = gigawatt        # gigawatt
milliwatt         = 0.001 W
horsepower        = 550 ft*lbf/sec
hp                = horsepower      # horsepower
metric horsepower = 75 kgf*m/s
ton refrigeration = 12000 Btu/hr
MBH               = 1000 Btu/hr     # 1000 Btu/hr


#
# frequency
#
[frequency]
hertz       = unit/sec
Hz          = hertz      # hertz
millihertz  = 0.001 Hz
kilohertz   = 1000 Hz
kHz         = kilohertz  # kilohertz
megahertz   = 1000 kHz
MHz         = megahertz  # megahertz
gigahertz   = 1000 MHz
GHz         = gigahertz  # gigahertz


#
# radioactivity
#
[radioactivity]
becquerel       = unit/sec
Bq              = becquerel     # becquerel
curie           = 3.7e10 Bq
millicurie      = 0.001 curie
roentgen        = 2.58e-4 coulomb/kg
[radiation dose]
gray            = J/kg
Gy              = gray          # gray
centigray       = 0.01 Gy
rad. abs. dose  = 0.01 Gy       # # commonly rad
sievert         = J/kg          # # equiv. dose
millisievert    = 0.001 sievert # # equiv. dose
Sv              = sievert       # sievert # equiv. dose
rem             = 0.01 Sv       # # roentgen equiv mammal
millirem        = 0.001 rem     # # roentgen equiv mammal


#
# viscosity
#
[dyn viscosity]
poise        = g/(cm*s)
P            = poise       # poise
centipoise   = 0.01 poise
cP           = centipoise  # centipoise

[kin viscosity]
stokes       = cm^2/s
St           = stokes      # stokes
centistokes  = 0.01 stokes
cSt          = centistokes # centistokes


#
# misc. units
#
[acceleration]
gravity                = 9.80665 m/s^2
galileo                = cm/s^2
[constant]
gravity constant       = 6.673e-11 N*m^2/kg^2
gas constant           = 8.314472 J/(mol*K)   # R
[fuel consumpt.]
mpg                    = mi/gal               # miles/gallon
mpg imp                = mi/gallon imperial   # miles/gallon imp
liter per 100 km       = [mpg] 3.785411784 / (x * 0.01609344) ; \
                         3.785411784 / (x * 0.01609344) # # non-linear
[permeability]
darcy                  = 1 cm^2*centipoise/atm/s
millidarcy             = 0.001 darcy

"""


class UnitGroup:
    "Stores, updates and converts a group of units"
    maxDecPlcs = 8
    def __init__(self, unitData, option):
        self.unitData = unitData
        self.option = option
        self.unitList = []
        self.currentNum = 0
        self.factor = 1.0
        self.reducedList = []
        self.linear = 1

    def update(self, text, cursorPos=None):
        "Decode user entered text into units"
        self.unitList = self.parseGroup(text)
        if cursorPos != None:
            self.updateCurrentUnit(text, cursorPos)
        else:
            self.currentNum = len(self.unitList) - 1

    def updateCurrentUnit(self, text, cursorPos):
        "Set current unit number"
        self.currentNum = len(re.findall('[\*/]', text[:cursorPos]))

    def currentUnit(self):
        "Return current unit if its a full match, o/w None"
        if self.unitList and self.unitList[self.currentNum].equiv:
            return self.unitList[self.currentNum]
        return None

    def currentPartialUnit(self):
        "Return unit with at least a partial match, o/w None"
        if not self.unitList:
            return None
        return self.unitData.findPartialMatch(self.unitList[self.currentNum]\
                                              .name)

    def currentSortPos(self):
        "Return unit near current unit for sorting"
        if not self.unitList:
            return self.unitData[self.unitData.sortedKeys[0]]
        return self.unitData.findSortPos(self.unitList[self.currentNum]\
                                         .name)

    def replaceCurrent(self, unit):
        "Replace the current unit with unit"
        if self.unitList:
            exp = self.unitList[self.currentNum].exp
            self.unitList[self.currentNum] = copy.copy(unit)
            self.unitList[self.currentNum].exp = exp
        else:
            self.unitList.append(copy.copy(unit))

    def completePartial(self):
        "Replace a partial unit with a full one"
        if self.unitList and not self.unitList[self.currentNum].equiv:
            text = self.unitList[self.currentNum].name
            unit = self.unitData.findPartialMatch(text)
            if unit:
                exp = self.unitList[self.currentNum].exp
                self.unitList[self.currentNum] = copy.copy(unit)
                self.unitList[self.currentNum].exp = exp

    def moveToNext(self, upward):
        "Replace unit with adjacent one based on match or sort position"
        unit = self.currentSortPos()
        num = self.unitData.sortedKeys.index(unit.name.\
                                             replace(' ', '')) \
                                             + (upward and -1 or 1)
        if 0 <= num < len(self.unitData.sortedKeys):
            self.replaceCurrent(self.unitData[self.unitData.sortedKeys[num]])

    def addOper(self, mult):
        "Add new operator & blank unit after current, * if mult is true"
        if self.unitList:
            self.completePartial()
            prevExp = self.unitList[self.currentNum].exp
            self.currentNum += 1
            self.unitList.insert(self.currentNum, Unit(''))
            if (not mult and prevExp > 0) or (mult and prevExp < 0):
                self.unitList[self.currentNum].exp = -1

    def changeExp(self, newExp):
        "Change the current unit's exponent"
        if self.unitList:
            self.completePartial()
            if self.unitList[self.currentNum].exp > 0:
                self.unitList[self.currentNum].exp = newExp
            else:
                self.unitList[self.currentNum].exp = -newExp

    def clearUnit(self):
        "Remove units"
        self.unitList = []

    def parseGroup(self, text):
        "Return list of units from text string"
        unitList = []
        parts = [part.strip() for part in re.split('([\*/])', text)]
        numerator = 1
        while parts:
            unit = self.parseUnit(parts.pop(0))
            if not numerator:
                unit.exp = -unit.exp
            if parts and parts.pop(0) == '/':
                numerator = not numerator
            unitList.append(unit)
        return unitList

    def parseUnit(self, text):
        "Return a valid or invalid unit with exponent from a text string"
        parts = text.split('^', 1)
        exp = 1
        if len(parts) > 1:   # has exponent
            try:
                exp = int(parts[1])
            except ValueError:
                if parts[1].lstrip().startswith('-'):
                    exp = -Unit.partialExp  # tmp invalid exp
                else:
                    exp = Unit.partialExp
        unitText = parts[0].strip().replace(' ', '')
        unit = copy.copy(self.unitData.get(unitText, None))
        if not unit and unitText and unitText[-1] == 's' and not \
           self.unitData.findPartialMatch(unitText):   # check for plural
            unit = copy.copy(self.unitData.get(unitText[:-1], None))
        if not unit:
            #unit = Unit(parts[0].strip())   # tmp invalid unit
            raise UnitDataError('%s is not a valid unit.' % (unitText))
        unit.exp = exp
        return unit

    def unitString(self, unitList=None):
        "Return the full string for this group or a given group"
        if unitList == None:
            unitList = self.unitList[:]
        fullText = ''
        if unitList:
            fullText = unitList[0].unitText(0)
            numerator = 1
            for unit in unitList[1:]:
                if (numerator and unit.exp > 0) \
                   or (not numerator and unit.exp < 0):
                    fullText = '%s * %s' % (fullText, unit.unitText(1))
                else:
                    fullText = '%s / %s' % (fullText, unit.unitText(1))
                    numerator = not numerator
        return fullText

    def groupValid(self):
        "Return 1 if all unitself.reducedLists are valid"
        if not self.unitList:
            return 0
        for unit in self.unitList:
            if not unit.unitValid():
                return 0
        return 1

    def reduceGroup(self):
        "Update reduced list of units and factor"
        self.linear = 1
        self.reducedList = []
        self.factor = 1.0
        if not self.groupValid():
            return
        count = 0
        tmpList = self.unitList[:]
        while tmpList:
            count += 1
            if count > 5000:
                raise UnitDataError('Circular unit definition')
            unit = tmpList.pop(0)
            if unit.equiv in ('!', '!!'):
                self.reducedList.append(copy.copy(unit))
            elif not unit.equiv:
                raise UnitDataError('Invalid conversion for "%s"' % unit.name)
            else:
                if unit.fromEqn:
                    self.linear = 0
                newList = self.parseGroup(unit.equiv)
                for newUnit in newList:
                    newUnit.exp *= unit.exp
                tmpList.extend(newList)
                self.factor *= unit.factor**unit.exp
        self.reducedList.sort()
        tmpList = self.reducedList[:]
        self.reducedList = []
        for unit in tmpList:
            if self.reducedList and unit == self.reducedList[-1]:
                self.reducedList[-1].exp += unit.exp
            else:
                self.reducedList.append(unit)
        self.reducedList = [unit for unit in self.reducedList if \
                            unit.name != 'unit' and unit.exp != 0]

    def categoryMatch(self, otherGroup):
        "Return 1 if unit types are equivalent"
        if not self.checkLinear() or not otherGroup.checkLinear():
            return 0
        return self.reducedList == otherGroup.reducedList and \
               [unit.exp for unit in self.reducedList] \
               == [unit.exp for unit in otherGroup.reducedList]

    def checkLinear(self):
        "Return 1 if linear or acceptable non-linear"
        if not self.linear:
            if len(self.unitList) > 1 or self.unitList[0].exp != 1:
                return 0
        return 1

    def compatStr(self):
        "Return string with reduced unit or linear compatability problem"
        if self.checkLinear():
            return self.unitString(self.reducedList)
        return 'Cannot combine non-linear units'

    def convert(self, num, toGroup):

        "Return num of this group converted to toGroup"
        if self.linear:
            num *= self.factor
        else:
            num = self.nonLinearCalc(num, 1) * self.factor


        n2 = -1
        if toGroup.linear:
            n2 =  num / toGroup.factor
        else:
            n2 = toGroup.nonLinearCalc(num / toGroup.factor, 0)
        return n2

    def nonLinearCalc(self, num, isFrom):
        "Return result of non-linear calculation"

        x = num
        try:
            if self.unitList[0].toEqn:      # regular equations
                if isFrom:
                    temp =  float(eval(self.unitList[0].fromEqn))
                    return temp
                temp = float(eval(self.unitList[0].toEqn))
                return temp
            data = list(eval(self.unitList[0].fromEqn))  # extrapolation list
            if isFrom:
                data = [(float(group[0]), float(group[1])) for group in data]
            else:
                data = [(float(group[1]), float(group[0])) for group in data]
            data.sort()
            pos = len(data) - 1
            for i in range(len(data)):
                if num <= data[i][0]:
                    pos = i
                    break
            if pos == 0:
                pos = 1
            y = (num-data[pos-1][0]) / float(data[pos][0]-data[pos-1][0]) \
                   * (data[pos][1]-data[pos-1][1]) + data[pos-1][1]
            return y
        except OverflowError:
            return 1e9999
        except:
            raise UnitDataError('Bad equation for %s' % self.unitList[0].name)

    def convertStr(self, num, toGroup):
        "Return formatted string of converted number"
        return self.formatNumStr(self.convert(num, toGroup))

    def formatNumStr(self, num):
        "Return num string formatted per options"
        decPlcs = self.option.intData('DecimalPlaces', 0, UnitGroup.maxDecPlcs)
        if self.option.boolData('SciNotation'):
            return ('%%0.%dE' % decPlcs) % num
        if self.option.boolData('FixedDecimals'):
            return ('%%0.%df' % decPlcs) % num
        return ('%%0.%dG' % decPlcs) % num


class UnitDataError(Exception):
    pass


class UnitData(dict):
    def __init__(self):
        dict.__init__(self)
        self.sortedKeys = []

    def readData(self):
        "Read all unit data from file"
        types = []
        typeUnits = {}
        lines = unitData.splitlines()
        for i in range(len(lines)):     # join continuation lines
            delta = 1
            while lines[i].rstrip().endswith('\\'):
                lines[i] = ''.join([lines[i].rstrip()[:-1], lines[i+delta]])
                lines[i+delta] = ''
                delta += 1
        units = [Unit(line) for line in lines if \
                 line.split('#', 1)[0].strip()]   # remove comment lines
        typeText = ''
        for unit in units:               # find & set headings
            if unit.name.startswith('['):
                typeText = unit.name[1:-1].strip()
                types.append(typeText)
                typeUnits[typeText] = []
            unit.typeName = typeText
        units = [unit for unit in units if unit.equiv]  # keep valid units
        for unit in units:
            self[unit.name.replace(' ', '')] = unit
            typeUnits[unit.typeName].append(unit.name)
        self.sortedKeys = list(self.keys())
        self.sortedKeys.sort()

        if len(self.sortedKeys) < len(units):
            raise UnitDataError('Duplicate unit names found')

        return (types, typeUnits)

    def findPartialMatch(self, text):
        "Return first partially matching unit or None"
        text = text.replace(' ', '')
        if not text:
            return None
        for name in self.sortedKeys:
            if name.startswith(text):
                return self[name]
        return None

    def findSortPos(self, text):
        "Return unit whose abbrev comes immediately after text"
        text = text.replace(' ', '')
        for name in self.sortedKeys:
            if text <= name:
                return self[name]
        return self[self.sortedKeys[-1]]


class Unit:
    "Reads and stores a single unit conversion"
    partialExp = 1000
    def __init__(self, dataStr):
        dataList = dataStr.split('#')
        unitList = dataList.pop(0).split('=', 1)
        self.name = unitList.pop(0).strip()
        self.equiv = ''
        self.factor = 1.0
        self.fromEqn = ''   # used only for non-linear units
        self.toEqn = ''     # used only for non-linear units
        if unitList:
            self.equiv = unitList[0].strip()
            if self.equiv[0] == '[':   # used only for non-linear units
                try:
                    self.equiv, self.fromEqn = re.match('\[(.*?)\](.*)', \
                                                        self.equiv).groups()
                    if ';' in self.fromEqn:
                        self.fromEqn, self.toEqn = self.fromEqn.split(';', 1)
                        self.toEqn = self.toEqn.strip()
                    self.fromEqn = self.fromEqn.strip()
                except AttributeError:
                    raise UnitDataError('Bad equation for "%s"' % self.name)
            else:                # split factor and equiv unit for linear
                parts = self.equiv.split(None, 1)
                if len(parts) > 1 and re.search('[^\d\.eE\+\-\*/]', parts[0]) \
                   == None:       # only allowed digits and operators
                    try:
                        self.factor = float(eval(parts[0]))
                        self.equiv = parts[1]
                    except:
                        pass
        self.comments = [comm.strip() for comm in dataList]
        self.comments.extend([''] * (2 - len(self.comments)))
        self.exp = 1
        self.viewLink = [None, None]
        self.typeName = ''

    def description(self):
        "Return name and 1st comment (usu. full name) if applicable"
        if self.comments[0]:
            return '%s  (%s)' % (self.name, self.comments[0])
        return self.name

    def unitValid(self):
        "Return 1 if unit and exponent are valid"
        if self.equiv and -Unit.partialExp < self.exp < Unit.partialExp:
            return 1
        return 0

    def unitText(self, absExp=0):
        "Return text for unit name with exponent or absolute value of exp"
        exp = self.exp
        if absExp:
            exp = abs(self.exp)
        if exp == 1:
            return self.name
        if -Unit.partialExp < exp < Unit.partialExp:
            return '%s^%d' % (self.name, exp)
        if exp > 1:
            return '%s^' % self.name
        else:
            return '%s^-' % self.name

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    def __lt__(self, other):
        return self.name < other.name

    def __eq__(self, other):
        return self.name == other.name

############################################################################
# Wrapper functionality
#
############################################################################


# Parse the data file, and set everything up for conversion
data = UnitData()
(types, unitsByType) = data.readData()

# At the moment, we're not handling options
option = None

# set up the objects for unit conversion
fromUnit = UnitGroup(data, option)
toUnit = UnitGroup(data, option)

def convert(num, unit1, unit2):
    """ Convert from one unit to another

    num is the factor for the first unit. Raises UnitDataError for
    various errors.
    """
    fromUnit.update(unit1)
    toUnit.update(unit2)

    fromUnit.reduceGroup()
    toUnit.reduceGroup()

    # Match up unit categories
    if not fromUnit.categoryMatch(toUnit):
        raise UnitDataError('unit categories did not match')

    return fromUnit.convert(num, toUnit)



def units(type):
    """ Return comma separated string list of units of given type, or
        a list of types if the argument is not valid.
    """
    if type in types:
        return '%s units: %s' % (type, ', '.join(unitsByType[type]))
    else:
        return 'valid types: ' + ', '.join(types)
