"""
py2app setup script for doiter
"""

from setuptools import setup

APP = ['doiter/main.py']
DATA_FILES = [
    ('Resources', ['doiter/resources/com.doiter.app.plist',
                   'doiter/resources/install_autostart.sh',
                   'doiter/resources/uninstall_autostart.sh'])
]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,
    'plist': {
        'CFBundleName': 'doiter',
        'CFBundleDisplayName': 'doiter',
        'CFBundleIdentifier': 'com.doiter.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,  # Run as background agent (no dock icon)
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
        'NSSupportsAutomaticGraphicsSwitching': True,
    },
    'packages': ['src', 'sqlite3', 'Cocoa', 'Quartz', 'Foundation', 'AppKit'],
    'includes': [
        'objc',
        'Foundation',
        'AppKit',
        'Cocoa',
        'Quartz',
        'CoreGraphics',
    ],
    'excludes': ['tkinter', 'matplotlib', 'numpy', 'pandas'],
    'resources': [],
    'frameworks': [],
    'semi_standalone': False,
    'site_packages': True,
}

setup(
    name='doiter',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'pyobjc-core>=10.0',
        'pyobjc-framework-Cocoa>=10.0',
        'pyobjc-framework-Quartz>=10.0',
    ],
)
