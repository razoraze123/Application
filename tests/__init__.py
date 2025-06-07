import os
import sys

# Ajoute le répertoire parent pour que les modules soient importables
tests_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(tests_dir, '..'))
sys.path.insert(0, parent_dir)
