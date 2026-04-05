# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, copy_metadata

# Streamlit calls importlib.metadata.version("streamlit") — bundle dist-info + assets.
_streamlit_datas, _streamlit_binaries, _streamlit_hidden = collect_all("streamlit")
_fastapi_datas, _fastapi_binaries, _fastapi_hidden = collect_all("fastapi")
_yfinance_datas, _yfinance_binaries, _yfinance_hidden = collect_all("yfinance")
_redis_datas, _redis_binaries, _redis_hidden = collect_all("redis")
_pydantic_settings_datas, _pydantic_settings_binaries, _pydantic_settings_hidden = collect_all(
    "pydantic_settings"
)
_aiofiles_datas, _aiofiles_binaries, _aiofiles_hidden = collect_all("aiofiles")

_binaries = (
    _streamlit_binaries
    + _fastapi_binaries
    + _yfinance_binaries
    + _redis_binaries
    + _pydantic_settings_binaries
    + _aiofiles_binaries
)
_hidden = list(
    dict.fromkeys(
        [
            *_streamlit_hidden,
            *_fastapi_hidden,
            *_yfinance_hidden,
            *_redis_hidden,
            *_pydantic_settings_hidden,
            *_aiofiles_hidden,
        ]
    )
)

a = Analysis(
    ['scripts\\desktop_launcher.py'],
    pathex=[],
    binaries=_binaries,
    datas=[
        ('src', 'src'),
        ('.env', '.'),
        ('.streamlit/config.toml', '.streamlit'),
        *_streamlit_datas,
        *_fastapi_datas,
        *_yfinance_datas,
        *_redis_datas,
        *_pydantic_settings_datas,
        *_aiofiles_datas,
        *copy_metadata('streamlit'),
        *copy_metadata('fastapi'),
        *copy_metadata('yfinance'),
        *copy_metadata('redis'),
        *copy_metadata('pydantic-settings'),
        *copy_metadata('aiofiles'),
    ],
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='learningSharesDesktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
