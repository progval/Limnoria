rm -f src/version.py # Prevent 2to3 from copying it, since py3k/src/version.py was probably written by root.
rm -rf py3k
mkdir py3k
cp locale/ py3k/ -R
cp plugins/ py3k/ -R # copy plugins data
python 2to3/run.py src/ plugins/ test/ scripts/* setup.py -wWno py3k -f all -f def_iteritems -f def_itervalues -f def_iterkeys -f reload "$@"
