from setuptools import setup

setup(
    name='matrix_bot',
    version='0.0.1',    
    description='Matrix Client Bot Proxy',
    url='http://strange.kudikala.lan:4000/BitOutput/MatrixBot',
    author='Srujith Kudikala',
    author_email='srujith@kudikala.com',
    license='MIT',
    packages=['matrix_bot'],
    install_requires=['matrix-nio[e2e]'                    
                      ],
    entry_points = {
        'console_scripts': [
            'matrix-bot = matrix_bot.main:main',                  
        ],              
    },
)