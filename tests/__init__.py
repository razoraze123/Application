import os
import sys

# Ajoute le répertoire parent pour que les modules soient importables
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)
