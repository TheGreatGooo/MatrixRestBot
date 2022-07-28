from setuptools import setup

setup(
    name='webhook_matrix_bot',
    version='0.0.1',    
    description='Matrix Client Bot Proxy',
    url='http://strange.kudikala.lan:4000/BitOutput/MatrixBot',
    author='Srujith Kudikala',
    author_email='srujith@kudikala.com',
    license='MIT',
    packages=['webhook_matrix_bot'],
    install_requires=['matrix-nio[e2e]',
                      'Flask[async]'                
                      ],
    entry_points = {
        'console_scripts': [
            'webhook_matrix_bot = webhook_matrix_bot.main:main',                  
        ],              
    },
)