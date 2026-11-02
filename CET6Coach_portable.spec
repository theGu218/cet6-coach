# -*- mode: python ; coding: utf-8 -*-
# 便携版（onedir）：不解压到临时目录，启动更快，杀毒软件误报概率更低。
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('CET6Coach.ico', '.'),
        ('content/vocabulary.json', 'content'),
        ('content/reading.json', 'content'),
        ('content/exams_scraped.json', 'content'),
        ('content/writing.json', 'content'),
        ('content/translation.json', 'content'),
        ('content/accumulation_seed.json', 'content'),
        ('content/analyses', 'content/analyses'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'numpy', 'pandas', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CET6Coach',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['CET6Coach.ico'],
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='CET6Coach-portable',
)
