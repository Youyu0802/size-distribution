# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['nano_measurer.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'tensorflow', 'keras', 'pandas', 'IPython', 'jupyter', 'notebook', 'jedi', 'pygments', 'zmq', 'lxml', 'h5py', 'grpc', 'google', 'googleapiclient', 'httplib2', 'openpyxl', 'fsspec', 'psutil', 'sympy', 'traitlets', 'tornado', 'setuptools', 'pkg_resources', 'certifi', 'urllib3', 'requests', 'charset_normalizer', 'pytz'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Measurement tool v1.6',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
