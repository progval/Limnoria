cp locale/ py3k/ -R
cp plugins/ py3k/ -R # copy plugins data
python 2to3/run.py src/ plugins/ test/ scripts/* setup.py -wWno py3k -f all -f def_iteritems -f def_itervalues -f def_iterkeys -f reload "$@"
