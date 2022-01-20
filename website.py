from quart import Quart, redirect, render_template
from pathlib import Path
import os
import importlib

app = Quart(__name__)
app.config['SERVER_NAME'] = 'squiddy.me'

filedir = os.path.dirname(os.path.realpath(__file__))

for files in Path(filedir + '/modules').glob('*'):
    file = files.resolve()
    relpath = file.relative_to(Path(filedir + '/modules'))
    if (relpath.suffix == '.py'):
        importlib.import_module(f"modules.{relpath.with_suffix('')}").init(app)